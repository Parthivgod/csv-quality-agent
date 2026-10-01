"""One request's end-to-end investigation and reporting workflow."""

from dataclasses import dataclass
import time

import pandas as pd

from src.agent.factory import create_chat_model, create_investigation_agent
from src.agent.report_chain import create_report
from src.agent.tools import build_tools
from src.config import Settings
from src.data.context_builder import build_context
from src.models.schemas import DataQualityReport
from src.services.trace import TraceCollector


@dataclass
class TriageResult:
    report: DataQualityReport
    trace: list[dict]
    metadata: dict | None = None
    full_results: list[dict] | None = None


class TriageError(RuntimeError):
    def __init__(self, message: str, trace: list[dict] | None = None,
                 raw_response: str | None = None):
        super().__init__(message)
        self.trace = trace or []
        self.raw_response = raw_response


def run_triage(frame: pd.DataFrame, question: str, target: str | None = None,
               settings: Settings | None = None, model=None, columns: list[str] | None = None,
               cancel_event=None, progress=None) -> TriageResult:
    """Run an isolated LangChain agent; real model is replaceable in tests."""
    settings = settings or Settings()
    if not question.strip():
        raise TriageError("Enter a data-quality question.")
    if target and target not in frame.columns:
        raise TriageError("Selected target column was not found in the uploaded CSV.")
    if columns is not None:
        if len(columns) > settings.max_numeric_columns or len(set(columns)) != len(columns):
            raise TriageError("Choose a unique numeric column subset within the configured limit.")
        if any(column not in frame.columns for column in columns):
            raise TriageError("Selected numeric columns were not found in the uploaded CSV.")
    started = time.perf_counter()
    trace = TraceCollector(settings.max_tool_calls)
    tools = build_tools(frame, target, settings, trace, columns, cancel_event, progress)
    model = model or create_chat_model(settings)
    agent = create_investigation_agent(model, tools, build_context(frame, target, settings.max_schema_columns, columns), target, settings)
    try:
        agent.invoke({"messages": [{"role": "user", "content": question}]},
                     config={"recursion_limit": 2 * settings.max_tool_calls + 5})
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError("Analysis cancelled.")
        if progress:
            progress("Formatting and validating report")
        report = create_report(model, question, target, trace.events)
        metadata = {"backend": "pandas" if isinstance(frame, pd.DataFrame) else frame.backend,
                    "rows": len(frame) if isinstance(frame, pd.DataFrame) else frame.row_count,
                    "dataset_hash": None if isinstance(frame, pd.DataFrame) else frame.fingerprint,
                    "target": target, "selected_numeric_columns": columns,
                    "local_compute_seconds": round(trace.local_compute_seconds, 4),
                    "total_seconds": round(time.perf_counter() - started, 4),
                    "provider": settings.provider, "model": settings.model}
        return TriageResult(report, trace.events, metadata, trace.full_results)
    except Exception as exc:
        raise TriageError(f"Triage could not complete: {exc}", trace.events,
                          getattr(exc, "raw_response", None)) from exc
