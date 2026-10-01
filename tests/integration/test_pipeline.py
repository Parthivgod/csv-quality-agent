import json

import pandas as pd
import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda

from src.agent.report_chain import ReportParseError, create_report
from src.agent.tools import build_tools
from src.config import Settings
from src.data.context_builder import build_context
from src.services.trace import TraceCollector
from src.services.triage_service import run_triage
import src.agent.tools as tool_module


class ScriptedChatModel(BaseChatModel):
    """Local scripted model for agent wiring tests; no claim of live LLM quality."""

    @property
    def _llm_type(self) -> str:
        return "scripted-fixture-model"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        system = str(messages[0].content)
        if "Create a concise CSV data-quality report" in system:
            human = str(messages[-1].content)
            observations = json.loads(human.split("Tool observations: ", 1)[1])
            issues = [{**finding, "source_tool": observation["tool"]}
                      for observation in observations for finding in observation.get("findings", [])]
            limitations = [o["summary"] for o in observations if o["status"] in {"skipped", "error"}]
            if not observations and "target" in human.lower():
                limitations.append("Select a target column to assess class imbalance.")
            content = json.dumps({"summary": "Diagnosis based on selected diagnostics.", "issues": issues,
                                  "tools_used": [o["tool"] for o in observations], "limitations": limitations,
                                  "interpretation": [{"text": "This observation applies to the selected check and its stated coverage.",
                                                      "source_tools": [o["tool"]]} for o in observations[:6]],
                                  "next_steps": ["Review supplied evidence and limitations before deciding on data changes."]})
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

        question = next((str(m.content).lower() for m in messages if isinstance(m, HumanMessage)), "")
        if "missing" in question:
            plan = ["missing_values_check"]
        elif "target" in question or "imbalanced" in question:
            plan = ["class_imbalance_check"] if "Selected target: none" not in system else []
        elif "numerical" in question or "relationships" in question:
            plan = ["outlier_check", "correlation_check"]
        else:
            plan = ["dataset_profile", "missing_values_check", "duplicate_rows_check", "constant_columns_check"]
        completed = sum(isinstance(m, ToolMessage) for m in messages)
        if completed < len(plan):
            name = plan[completed]
            message = AIMessage(content="", tool_calls=[{"name": name, "args": {},
                                                          "id": f"call_{completed}", "type": "tool_call"}])
        else:
            message = AIMessage(content="Investigation finished.")
        return ChatResult(generations=[ChatGeneration(message=message)])


def test_tool_wrapper_calls_pure_diagnostic() -> None:
    frame = pd.read_csv("data/samples/corrupted_missing_duplicates.csv")
    trace = TraceCollector(6)
    tools = {tool.name: tool for tool in build_tools(frame, None, Settings(), trace)}
    assert all(set(tool.args) == {"reason"} for tool in tools.values())
    assert all(tool.args_schema.model_fields["reason"].default == ""
               and not tool.args_schema.model_fields["reason"].is_required()
               for tool in tools.values())
    observation = json.loads(tools["duplicate_rows_check"].invoke({}))
    assert observation["data"]["duplicate_count"] == 2
    assert trace.events[0]["tool"] == "duplicate_rows_check"
    assert trace.events[0]["status"] == "ok"


def test_tool_failure_and_budget_are_observable(monkeypatch) -> None:
    frame = pd.DataFrame({"x": [1, 2, 3]})
    def broken(_frame):
        raise RuntimeError("fixture failure")
    monkeypatch.setattr(tool_module, "duplicate_rows_check", broken)
    trace = TraceCollector(1)
    tools = {tool.name: tool for tool in build_tools(frame, None, Settings(max_tool_calls=1), trace)}
    assert json.loads(tools["duplicate_rows_check"].invoke({}))["status"] == "error"
    assert json.loads(tools["missing_values_check"].invoke({}))["summary"] == "Diagnostic call budget reached."
    assert [e["status"] for e in trace.events] == ["error", "skipped"]


def test_context_contains_schema_but_not_raw_values() -> None:
    context = build_context(pd.DataFrame({"secret": ["private-value"], "age": [20]}))
    assert context["rows"] == 1
    assert "private-value" not in str(context)


def test_two_agent_scenarios_select_different_tools() -> None:
    model = ScriptedChatModel()
    broad = run_triage(pd.read_csv("data/samples/corrupted_missing_duplicates.csv"),
                       "Why could this dataset cause problems during model training?", model=model)
    assert [e["tool"] for e in broad.trace] == ["dataset_profile", "missing_values_check",
                                                   "duplicate_rows_check", "constant_columns_check"]
    assert {i.issue for i in broad.report.issues} >= {"Missing values", "Duplicate rows", "Constant column"}
    target = run_triage(pd.read_csv("data/samples/corrupted_class_imbalance.csv"),
                        "Is my target distribution a problem?", "label", model=model)
    assert [e["tool"] for e in target.trace] == ["class_imbalance_check"]
    assert target.report.issues[0].evidence.startswith("Majority/minority ratio 9.0:1")


def test_numeric_and_missing_target_scenarios() -> None:
    model = ScriptedChatModel()
    numeric = run_triage(pd.read_csv("data/samples/corrupted_outliers_corr.csv"),
                         "Do the numerical features contain suspicious values or relationships?", model=model)
    assert [e["tool"] for e in numeric.trace] == ["outlier_check", "correlation_check"]
    no_target = run_triage(pd.read_csv("data/samples/corrupted_class_imbalance.csv"),
                           "Is my target imbalanced?", model=model)
    assert no_target.trace == []
    assert "Select a target column to assess class imbalance." in no_target.report.limitations


def test_report_rejects_unsupported_evidence_and_retries_once() -> None:
    responses = iter([json.dumps({"summary": "wrong", "issues": [{"issue": "Fake", "severity": "high",
        "column": None, "evidence": "invented", "impact": "x", "recommendation": "x",
        "source_tool": "missing_values_check"}], "tools_used": [], "limitations": []}),
        json.dumps({"summary": "No supported issue", "issues": [], "tools_used": [], "limitations": [],
                    "next_steps": ["Ask a focused quality question and inspect the relevant local checks."]})])
    report = create_report(RunnableLambda(lambda _: next(responses)), "Any issue?", None, [])
    assert report.issues == []
    with pytest.raises(ReportParseError) as exc_info:
        create_report(RunnableLambda(lambda _: "not-json"), "Any issue?", None, [])
    assert exc_info.value.raw_response == "not-json"
