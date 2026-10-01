"""Save actual scripted or live-Groq end-to-end scenario evidence.

Default mode is API-free scripted execution. --live uses the configured real model.
The controlled failure is scoped to one harness run, never production configuration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from src.config import Settings, provider_ready
from src.data.loader import CSVLoadError, load_dataset
from src.services.triage_service import run_triage


@dataclass(frozen=True)
class Scenario:
    identifier: str
    label: str
    filename: str
    question: str
    target: str | None = None
    tools: tuple[str, ...] = ()
    controlled_failure: bool = False


SCENARIOS = (
    Scenario("T01", "missing", "corrupted_missing_duplicates.csv", "Does this CSV contain missing data?", tools=("missing_values_check",)),
    Scenario("T02", "broad", "corrupted_missing_duplicates.csv", "Why could this dataset cause problems during model training?",
             tools=("dataset_profile", "missing_values_check", "duplicate_rows_check", "constant_columns_check")),
    Scenario("T03", "target", "corrupted_class_imbalance.csv", "Is my target distribution a problem?", "label", ("class_imbalance_check",)),
    Scenario("T04", "numeric", "corrupted_outliers_corr.csv", "Do the numerical features contain suspicious values or relationships?",
             tools=("outlier_check", "correlation_check")),
    Scenario("T05", "unexpected_target", "corrupted_class_imbalance.csv", "Check class imbalance in my selected target using the class imbalance tool.",
             "record_id", ("class_imbalance_check",)),
    Scenario("T06", "controlled_failure", "corrupted_missing_duplicates.csv", "Check this dataset for duplicate rows using the duplicate rows tool.",
             tools=("duplicate_rows_check",), controlled_failure=True),
    Scenario("T07", "missing_target", "corrupted_class_imbalance.csv", "Is my target distribution a problem?"),
    Scenario("T08", "clean", "clean_small.csv", "Does this CSV contain missing data?", tools=("missing_values_check",)),
    Scenario("T09", "invalid_input", "invalid_header_only.csv", "Upload only; triage must not run."),
)


class ScenarioModel(BaseChatModel):
    """Deterministically exercises actual LangChain graph; no live-quality claim."""

    planned_tools: list[str]

    @property
    def _llm_type(self) -> str:
        return "phase3-scripted-fixture"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if "Create a concise CSV data-quality report" in str(messages[0].content):
            human = str(messages[-1].content)
            observations = json.loads(human.split("Tool observations: ", 1)[1])
            issues = [{**finding, "source_tool": observation["tool"]}
                      for observation in observations for finding in observation.get("findings", [])]
            limitations = [o["summary"] for o in observations if o["status"] in {"skipped", "error"}]
            content = json.dumps({"summary": "Selected diagnostics completed.", "issues": issues,
                                  "tools_used": [o["tool"] for o in observations], "limitations": limitations})
            message = AIMessage(content=content)
        else:
            completed = sum(isinstance(m, ToolMessage) for m in messages)
            if completed < len(self.planned_tools):
                message = AIMessage(content="", tool_calls=[{"name": self.planned_tools[completed], "args": {},
                                                             "id": f"fixture_{completed}", "type": "tool_call"}])
            else:
                message = AIMessage(content="Investigation completed.")
        return ChatResult(generations=[ChatGeneration(message=message)])


def verify_scenario(scenario: Scenario, trace: list[dict], report: dict) -> tuple[str, list[str]]:
    """Check semantic evidence and tool coverage, independently of narrative wording."""
    actual = {}
    for event in trace:
        # Prefer original successful observations over an agent's repeated-call skip.
        if event["tool"] not in actual or (actual[event["tool"]]["status"] != "ok" and event["status"] == "ok"):
            actual[event["tool"]] = event
    required = set(scenario.tools) - ({"dataset_profile"} if scenario.identifier == "T02" else set())
    missing = sorted(required - actual.keys())
    failures = [f"Required diagnostic never called: {name}" for name in missing]
    issues = report.get("issues", [])
    if missing:
        return "partial", failures
    if scenario.identifier in {"T01", "T02"}:
        data = actual["missing_values_check"]["result"]["data"]
        counts = {item["column"]: item["missing_count"] for item in data.get("affected_columns", [])}
        if counts != {"age": 6, "income": 3}:
            failures.append(f"Unexpected null counts: {counts}")
    if scenario.identifier == "T02":
        if actual["duplicate_rows_check"]["result"]["data"].get("duplicate_count") != 2:
            failures.append("Expected two duplicate rows.")
        constants = actual["constant_columns_check"]["result"]["data"].get("constant_columns", [])
        if "constant_feature" not in {item["column"] for item in constants}:
            failures.append("Expected constant_feature to be constant.")
    if scenario.identifier == "T03":
        data = actual["class_imbalance_check"]["result"]["data"]
        if {c["class"]: c["count"] for c in data.get("classes", [])} != {"negative": 90, "positive": 10}:
            failures.append("Expected 90 negative and 10 positive labels.")
        if data.get("majority_minority_ratio") != 9:
            failures.append("Expected class ratio nine.")
    if scenario.identifier == "T04":
        outliers = actual["outlier_check"]["result"]["data"].get("columns", [])
        if {c["column"]: c["outlier_count"] for c in outliers if c["outlier_count"]} != {"feature_x": 1, "feature_y": 1}:
            failures.append("Expected one outlier in each of feature_x and feature_y.")
        pairs = actual["correlation_check"]["result"]["data"].get("pairs", [])
        if not pairs or not any(abs(abs(p.get("correlation", 0)) - 1) < 1e-9 for p in pairs):
            failures.append("Expected perfectly correlated numeric pair.")
    if scenario.identifier in {"T05", "T06"}:
        tool = scenario.tools[0]
        wanted = "error" if scenario.controlled_failure else "skipped"
        if not any(event["tool"] == tool and event["status"] == wanted for event in trace):
            failures.append(f"Expected {wanted} status for {tool}.")
        if not report.get("limitations"):
            failures.append("Failed/skipped check must appear as a report limitation.")
        if any(issue.get("source_tool") == tool for issue in issues):
            failures.append("Unsupported issue emitted for failed/skipped diagnostic.")
    if scenario.identifier == "T07":
        if any(issue.get("source_tool") == "class_imbalance_check" for issue in issues):
            failures.append("Class imbalance must not be invented without a selected target.")
        if not report.get("limitations"):
            failures.append("Missing target must be disclosed.")
    if scenario.identifier == "T08":
        if actual["missing_values_check"]["result"]["data"].get("affected_columns"):
            failures.append("Expected no missing values in clean control.")
        if any(issue.get("issue") == "Missing values" for issue in issues):
            failures.append("Clean missing-value control produced an unsupported finding.")
    return ("fail" if failures else "pass"), failures


def sanitize_error(value: str, limit: int = 3000) -> str:
    """Retain useful provider/parser diagnostics without credentials or local paths."""
    for name in ("GROQ_API_KEY", "OPENAI_API_KEY", "MISTRAL_API_KEY", "LANGSMITH_API_KEY"):
        secret = os.getenv(name)
        if secret:
            value = value.replace(secret, "[redacted credential]")
    value = re.sub(r"\b(?:gsk_|sk-)[A-Za-z0-9_-]{8,}", "[redacted credential]", value)
    value = re.sub(r"(?i)Bearer\s+[A-Za-z0-9_.-]+", "Bearer [redacted]", value)
    value = value.replace(str(ROOT), "[repository]").replace(ROOT.as_posix(), "[repository]")
    value = re.sub(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\r\n\"']+", "[local path]", value)
    value = re.sub(r"\borg_[A-Za-z0-9]+", "[provider organization]", value)
    return value[:limit]


def evaluate_scenario(scenario: Scenario, output: Path, live: bool = False, settings: Settings | None = None) -> dict:
    settings = settings or Settings()
    path = ROOT / "data/samples" / scenario.filename
    payload = path.read_bytes()  # Small tracked fixtures only; large benchmarks use stream ingestion.
    attempt = f"{scenario.identifier}_{scenario.label}_{'live' if live else 'scripted'}_{time.time_ns()}"
    record = {"id": scenario.identifier, "attempt": attempt, "utc_time": datetime.now(timezone.utc).isoformat(),
              "mode": "live Groq" if live else "scripted LangChain integration", "provider": settings.provider if live else "local scripted",
              "model": settings.model if live else "phase3-scripted-fixture", "file": scenario.filename,
              "sha256": hashlib.sha256(payload).hexdigest(), "target": scenario.target, "question": scenario.question,
              "controlled_failure_injection": scenario.controlled_failure, "status": "error"}
    trace, report, dataset = [], None, None
    started = time.perf_counter()
    try:
        with path.open("rb") as upload:
            dataset = load_dataset(upload, path.name, settings=settings)
        if scenario.identifier == "T09":
            record.update(status="fail", reasons=["Header-only CSV was accepted."])
        else:
            model = None if live else ScenarioModel(planned_tools=list(scenario.tools))
            original = type(dataset).run_check
            def injected(self, name, *args, **kwargs):
                if name == "duplicate_rows_check":
                    raise RuntimeError("controlled diagnostic failure")
                return original(self, name, *args, **kwargs)
            context = patch.object(type(dataset), "run_check", injected) if scenario.controlled_failure else nullcontext()
            with context:
                result = run_triage(dataset, scenario.question, scenario.target, settings=settings, model=model)
            trace, report = result.trace, result.report.model_dump()
            status, reasons = verify_scenario(scenario, trace, report)
            record.update(status=status, reasons=reasons, actual_calls=[e["tool"] for e in trace])
            record["run_metadata"] = getattr(result, "metadata", {})
    except Exception as exc:
        trace = getattr(exc, "trace", [])
        record["error_message"] = sanitize_error(str(exc))
        record["cause_type"] = type(exc.__cause__).__name__ if exc.__cause__ else None
        raw = getattr(exc, "raw_response", None)
        if raw is not None:
            record["raw_report_response_excerpt"] = sanitize_error(str(raw), 2000)
        if scenario.identifier == "T09" and dataset is None and isinstance(exc, CSVLoadError):
            record.update(status="pass", reasons=["Invalid input rejected before agent execution."], error_type=type(exc).__name__)
        else:
            record.update(status="error", reasons=[type(exc).__name__], actual_calls=[e["tool"] for e in trace])
    finally:
        if dataset is not None:
            dataset.close()
        record["latency_seconds"] = round(time.perf_counter() - started, 6)
        output.mkdir(parents=True, exist_ok=True)
        for suffix, value in (("trace", trace), ("report", report), ("result", record)):
            filename = f"{attempt}_{suffix}.json"
            (output / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            record[f"{suffix}_file"] = filename
        # Save final record including all evidence filenames.
        (output / f"{attempt}_result.json").write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Call the configured provider; default is API-free scripted")
    parser.add_argument("--scenarios", nargs="+", choices=[s.identifier for s in SCENARIOS], default=[s.identifier for s in SCENARIOS])
    parser.add_argument("--output-dir", type=Path, default=Path("docs/evaluation/phase3/scenarios"))
    args = parser.parse_args()
    settings = Settings()
    if args.live and (settings.provider != "groq" or not provider_ready(settings)):
        parser.error("Live Phase 3 evaluation requires configured Groq credentials; set GROQ_API_KEY in the ignored .env.")
    records = []
    for scenario in SCENARIOS:
        if scenario.identifier in args.scenarios:
            record = evaluate_scenario(scenario, args.output_dir, args.live, settings)
            records.append(record)
            print(f"{scenario.identifier}: {record['status']} ({record['latency_seconds']}s), {record['attempt']}", flush=True)
    header = "# Phase 3 scenario results\n\nOriginal attempts are retained; scripted runs are wiring tests, live runs measure actual provider tool selection.\n\n"
    lines = ["| ID | Mode | Result | Actual calls | Seconds | Evidence |", "| --- | --- | --- | --- | --- | --- |"]
    for file in sorted(args.output_dir.glob("*_result.json")):
        record = json.loads(file.read_text(encoding="utf-8"))
        lines.append(f"| {record['id']} | {record['mode']} | {record['status']} | {', '.join(record.get('actual_calls', []))} | {record['latency_seconds']} | [{record['attempt']}]({file.name}) |")
    (args.output_dir / "scenario_results.md").write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    return 1 if any(r["status"] != "pass" for r in records) else 0


if __name__ == "__main__":
    raise SystemExit(main())
