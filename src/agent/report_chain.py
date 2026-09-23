"""LCEL report generation, Pydantic parsing and bounded repair."""

import json

from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.runnables import Runnable

from src.agent.prompt import REPORT_PROMPT
from src.models.schemas import DataQualityReport


class ReportParseError(ValueError):
    def __init__(self, message: str, raw_response: str):
        super().__init__(message)
        self.raw_response = raw_response


def _validate_evidence(report: DataQualityReport, observations: list[dict]) -> DataQualityReport:
    allowed = {(event["tool"], finding["issue"], finding["severity"], finding.get("column"),
                finding["evidence"], finding["impact"], finding["recommendation"])
               for event in observations for finding in event["result"].get("findings", [])}
    for issue in report.issues:
        if (issue.source_tool, issue.issue, issue.severity, issue.column,
                issue.evidence, issue.impact, issue.recommendation) not in allowed:
            raise ValueError(f"Report issue has no matching tool finding: {issue.issue}")
    report.tools_used = list(dict.fromkeys(e["tool"] for e in observations))
    for event in observations:
        if event["status"] in {"skipped", "error"} and event["summary"] not in report.limitations:
            report.limitations.append(event["summary"])
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
    for attempt in range(2):
        try:
            if attempt:
                payload["question"] = question + "\nYour previous JSON was invalid or unsupported. Repair it by using only exact supplied findings."
            raw = chain.invoke(payload)
            return _validate_evidence(parser.parse(raw), observations)
        except Exception as exc:
            if attempt:
                raise ReportParseError(f"Structured report validation failed after one retry: {exc}", raw) from exc
    raise AssertionError("unreachable")
