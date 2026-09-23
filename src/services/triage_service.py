"""One request's end-to-end investigation and reporting workflow."""

from dataclasses import dataclass

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


class TriageError(RuntimeError):
    def __init__(self, message: str, trace: list[dict] | None = None,
                 raw_response: str | None = None):
        super().__init__(message)
        self.trace = trace or []
        self.raw_response = raw_response


def run_triage(frame: pd.DataFrame, question: str, target: str | None = None,
               settings: Settings | None = None, model=None) -> TriageResult:
    """Run an isolated LangChain agent; real model is replaceable in tests."""
    settings = settings or Settings()
    if not question.strip():
        raise TriageError("Enter a data-quality question.")
    if target and target not in frame.columns:
        raise TriageError("Selected target column was not found in the uploaded CSV.")
    trace = TraceCollector(settings.max_tool_calls)
    tools = build_tools(frame, target, settings, trace)
    model = model or create_chat_model(settings)
    agent = create_investigation_agent(model, tools, build_context(frame, target), target, settings)
    try:
        agent.invoke({"messages": [{"role": "user", "content": question}]},
                     config={"recursion_limit": 2 * settings.max_tool_calls + 5})
        report = create_report(model, question, target, trace.events)
        return TriageResult(report, trace.events)
    except Exception as exc:
        raise TriageError(f"Triage could not complete: {exc}", trace.events,
                          getattr(exc, "raw_response", None)) from exc
