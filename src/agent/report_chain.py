"""LCEL report generation, Pydantic parsing and bounded repair."""

import json
import re
from decimal import Decimal

from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.runnables import Runnable

from src.agent.prompt import REPORT_PROMPT
from src.models.schemas import DataQualityReport, Issue


class ReportParseError(ValueError):
    def __init__(self, message: str, raw_response: str):
        super().__init__(message)
        self.raw_response = raw_response


_NUMBER = re.compile(r"(?<![\w.])[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?(?!\w|\.\d)")
_UNSUPPORTED_CERTAINTY = re.compile(
    r"\b(?:100(?:\.0+)?\s*%|fully|completely|perfectly|entirely)\s+(?:clean|balanced|safe|valid)\b"
    r"|\b(?:no|without any)\s+(?:data[- ]quality (?:issues|problems)|leakage)\b", re.IGNORECASE)
_NEGATED = re.compile(r"\b(?:not|cannot|can't|doesn't|does not|no guarantee|does not establish|does not prove)\b", re.IGNORECASE)
_CLAUSE_BREAK = re.compile(r"[!?;\n]|\.(?!\d)|\b(?:but|however|yet)\b|,\s*and\b", re.IGNORECASE)


def _numbers(value) -> set[Decimal]:
    """Recognize supplied numeric literals; this is not semantic fact verification."""
    if isinstance(value, dict):
        return set().union(*(_numbers(v) for k, v in value.items() if k != "dataset_hash")) if value else set()
    if isinstance(value, (list, tuple)):
        return set().union(*(_numbers(v) for v in value)) if value else set()
    if isinstance(value, bool) or value is None:
        return set()
    return {Decimal(m.group().replace(",", "")) for m in _NUMBER.finditer(str(value))}


def _validate_narrative(report: DataQualityReport, observations: list[dict]) -> None:
    """Preserve model prose while rejecting unknown sources/numbers and broad assurances."""
    supplied = {}
    for event in observations:
        if event["tool"] not in supplied or event["status"] == "ok":
            supplied[event["tool"]] = event["result"]
    allowed_numbers = _numbers([e["result"] for e in observations])
    if observations and not report.interpretation:
        raise ValueError("Explain the tool observations in interpretation with their source_tools.")
    if not report.next_steps:
        raise ValueError("Provide at least one suggested next step.")
    texts = [(report.summary, allowed_numbers)]
    for item in report.interpretation:
        unknown = set(item.source_tools) - supplied.keys()
        if unknown:
            raise ValueError("Interpretation cites a tool that did not run: " + ", ".join(sorted(unknown)))
        item.source_tools = list(dict.fromkeys(item.source_tools))
        texts.append((item.text, _numbers([supplied[name] for name in item.source_tools])))
    texts.extend((step, allowed_numbers) for step in report.next_steps)
    for text, numbers in texts:
        if not text.strip() or len(text) > 2400:
            raise ValueError("Narrative must be concise and nonempty.")
        if _numbers(text) - numbers:
            raise ValueError("Narrative contains a numeric value absent from its supplied tool observations.")
        if any(not _NEGATED.search(_CLAUSE_BREAK.split(text[max(0, match.start()-100):match.start()])[-1])
               for match in _UNSUPPORTED_CERTAINTY.finditer(text)):
            raise ValueError("Narrative makes an unsupported assurance beyond the selected diagnostics.")


def _validate_evidence(report: DataQualityReport, observations: list[dict],
                       question: str, target: str | None) -> DataQualityReport:
    allowed = {(event["tool"], finding["issue"], finding["severity"], finding.get("column"),
                finding["evidence"], finding["impact"], finding["recommendation"])
               for event in observations if event["status"] == "ok"
               for finding in event["result"].get("findings", [])}
    for issue in report.issues:
        if (issue.source_tool, issue.issue, issue.severity, issue.column,
                issue.evidence, issue.impact, issue.recommendation) not in allowed:
            raise ValueError(f"Report issue has no matching tool finding: {issue.issue}")
    report.tools_used = list(dict.fromkeys(e["tool"] for e in observations))
    unique_issues = {}
    for issue in report.issues:
        unique_issues.setdefault((issue.source_tool, issue.issue, issue.severity, issue.column,
                                 issue.evidence, issue.impact, issue.recommendation), issue)
    report.issues = list(unique_issues.values())
    # Preserve every supplied finding and derive coverage independently of model prose.
    present = {(i.source_tool, i.issue, i.column, i.evidence) for i in report.issues}
    for event in observations:
        if event["status"] == "ok":
            for finding in event["result"].get("findings", []):
                key = (event["tool"], finding["issue"], finding.get("column"), finding["evidence"])
                if key not in present:
                    report.issues.append(Issue(**finding, source_tool=event["tool"]))
                    present.add(key)
    report.limitations = []
    for event in observations:
        if event["status"] in {"skipped", "error"} and event["summary"] not in report.limitations:
            report.limitations.append(event["summary"])
        execution = event["result"].get("execution", {})
        for key in ("output_limitation", "coverage_limitation"):
            if execution.get(key) and execution[key] not in report.limitations:
                report.limitations.append(execution[key])
        if execution.get("columns_omitted"):
            limitation = f"{event['tool']} did not assess {execution['columns_omitted']} columns; inspect its coverage."
            if limitation not in report.limitations:
                report.limitations.append(limitation)
    if target is None and any(term in question.lower() for term in ("target", "imbalan", "class distribution")):
        limitation = "Select a target column to assess class imbalance."
        if limitation not in report.limitations:
            report.limitations.append(limitation)
    completed = len({e["tool"] for e in observations if e["status"] == "ok"})
    report.assessment_summary = (f"{len(report.issues)} verified finding(s) from {completed} completed diagnostic(s). "
                                "Results apply to the selected checks and their stated coverage.")
    _validate_narrative(report, observations)
    return report


def create_report(model: Runnable, question: str, target: str | None,
                  observations: list[dict]) -> DataQualityReport:
    """Format observations using LCEL and parse once, with one repair attempt."""
    parser = PydanticOutputParser(pydantic_object=DataQualityReport)
    chain = REPORT_PROMPT | model | StrOutputParser()
    payload = {"question": question, "target": target or "none",
               "observations": json.dumps([e["result"] for e in observations], ensure_ascii=False),
               "format_instructions": parser.get_format_instructions()}
    raw = ""
    validation_error = ""
    for attempt in range(2):
        try:
            if attempt:
                payload["question"] = (question + "\nYour previous report failed validation: " + validation_error +
                    "\nRegenerate valid JSON. Keep exact findings; use only observed numbers and source_tools in narrative, "
                    "and provide interpretation and suggested next_steps.")
            raw = chain.invoke(payload)
            return _validate_evidence(parser.parse(raw), observations, question, target)
        except Exception as exc:
            validation_error = str(exc)[:300]
            if attempt:
                raise ReportParseError(f"Structured report validation failed after one retry: {exc}", raw) from exc
    raise AssertionError("unreachable")
