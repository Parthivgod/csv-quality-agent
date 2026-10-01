"""Observable, bounded tool explanations with unchanged deterministic results."""

import json

import pandas as pd
import pytest
from pydantic import ValidationError

from src.agent.tools import build_tools
from src.config import Settings
from src.services.trace import TraceCollector
import src.agent.tools as tool_module


def tools_and_trace(progress=None):
    trace = TraceCollector(6)
    tools = {tool.name: tool for tool in build_tools(
        pd.DataFrame({"age": [1.0, None, 3.0]}), None, Settings(), trace, progress=progress)}
    return tools, trace


def test_reason_is_cleaned_recorded_and_visible_before_diagnostic(monkeypatch):
    progress = []
    actual_check = tool_module.missing_values_check
    explanation = "Check missing values because the question asks about incomplete data."

    def assert_explanation_precedes_execution(*args, **kwargs):
        assert progress == ["Running missing_values_check — " + explanation]
        return actual_check(*args, **kwargs)

    monkeypatch.setattr(tool_module, "missing_values_check", assert_explanation_precedes_execution)
    tools, trace = tools_and_trace(progress.append)
    observation = json.loads(tools["missing_values_check"].invoke({
        "reason": "  Check\nmissing\x00 values\u202e because the question asks about incomplete data.  "}))
    assert trace.events[0]["selection_reason"] == explanation
    assert trace.events[0]["arguments"] == {"reason": explanation}
    assert progress == ["Running missing_values_check — " + explanation]
    assert observation["data"]["affected_columns"][0]["missing_count"] == 1
    assert "selection_reason" not in observation


def test_missing_reason_remains_compatible_without_fabricated_explanation():
    progress = []
    tools, trace = tools_and_trace(progress.append)
    observation = json.loads(tools["missing_values_check"].invoke({}))
    assert observation["status"] == "ok"
    assert trace.events[0]["selection_reason"] is None
    assert trace.events[0]["arguments"] == {}
    assert progress == ["Running missing_values_check"]
    assert all(set(tool.args) == {"reason"} for tool in tools.values())
    assert all(not tool.args_schema.model_fields["reason"].is_required() for tool in tools.values())


@pytest.mark.parametrize("arguments", [
    {"reason": "x" * 301}, {"reason": 42}, {"reason": True}, {"reason": None},
    {"reason": []}, {"reason": "Relevant check", "target": "other"},
    {"reason": "Relevant check", "dataset": "other.csv"},
])
def test_invalid_or_extra_arguments_cannot_execute_diagnostics(arguments):
    tools, trace = tools_and_trace()
    with pytest.raises(ValidationError):
        tools["missing_values_check"].invoke(arguments)
    assert trace.events == []
    assert trace.executed_calls == 0


def test_reason_does_not_change_diagnostic_evidence():
    first, _ = tools_and_trace()
    second, _ = tools_and_trace()
    plain = json.loads(first["missing_values_check"].invoke({}))
    explained = json.loads(second["missing_values_check"].invoke({"reason": "Check the completeness requested by the user."}))
    for key in ("status", "tool", "summary", "data", "findings"):
        assert plain[key] == explained[key]


def test_reason_is_preserved_for_skipped_repeated_tool():
    tools, trace = tools_and_trace()
    tools["missing_values_check"].invoke({"reason": "Check completeness."})
    repeat = json.loads(tools["missing_values_check"].invoke({"reason": "Recheck completeness."}))
    assert repeat["status"] == "skipped"
    assert trace.events[1]["selection_reason"] == "Recheck completeness."
    assert trace.executed_calls == 1
