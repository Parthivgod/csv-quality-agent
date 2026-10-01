import json
from threading import Event

import pandas as pd
import pytest
from langchain_core.runnables import RunnableLambda

from src.agent.report_chain import ReportParseError, create_report
from src.agent.tools import bound_observation
from src.config import Settings
from src.data.context_builder import build_context
from src.services.jobs import BackgroundJob


def test_observation_byte_cap_and_complete_findings():
    settings = Settings(max_observation_bytes=2048, max_findings_per_tool=2)
    result = {"tool": "missing_values_check", "status": "ok", "summary": "many columns", "data": {"large": "x"*10000},
              "findings": [{"evidence": "y"*900, "column": str(i)} for i in range(10)]}
    bounded = bound_observation(result, settings)
    assert len(json.dumps(bounded, ensure_ascii=False).encode()) <= 2048
    assert len(result["findings"]) == 10
    assert bounded["execution"]["output_limited"]
    assert bounded["execution"]["findings_omitted"] >= 8


def test_report_summary_and_limits_cannot_invent_evidence():
    response = json.dumps({"summary": "Every column has 100% missing values.", "issues": [],
                           "tools_used": [], "limitations": ["Invented model statistic"],
                           "interpretation": [{"text": "Only the selected check and available coverage were assessed.", "source_tools": ["missing_values_check"]}],
                           "next_steps": ["Review the check's actual coverage before deciding what to inspect next."]})
    observation = {"tool": "missing_values_check", "status": "ok", "summary": "No missing values",
                   "result": {"findings": [], "execution": {"output_limitation": "Partial output"}}}
    calls = []
    def unsupported(_):
        calls.append(True)
        return response
    with pytest.raises(ReportParseError, match="numeric value absent"):
        create_report(RunnableLambda(unsupported), "Any missing?", None, [observation])
    assert len(calls) == 2


def test_nonfinite_statistics_use_strict_json_and_disclose_replacement():
    result = {"tool": "outlier_check", "status": "ok", "summary": "numeric range",
              "data": {"bounds": [float("nan"), float("inf"), 12]}, "findings": []}
    bounded = bound_observation(result, Settings())
    encoded = json.dumps(bounded, allow_nan=False)
    assert bounded["data"]["bounds"] == [None, None, 12]
    assert "Non-finite" in bounded["execution"]["coverage_limitation"]
    assert "Infinity" not in encoded


def test_target_beyond_schema_cap_remains_visible_without_values():
    frame = pd.DataFrame({f"column_{i}": ["private-cell"] for i in range(60)})
    context = build_context(frame, "column_59", max_columns=50)
    assert len(context["schema"]) == 50
    assert context["schema"][-1]["name"] == "column_59"
    assert "private-cell" not in str(context)


def test_background_busy_and_cancel_waits_for_owned_work():
    entered, done = Event(), Event()
    def work(job):
        entered.set()
        assert job.cancel_event.wait(3)
        done.set()
        return "stopped"
    job = BackgroundJob.start("test", work)
    assert entered.wait(3)
    with pytest.raises(RuntimeError, match="Another analysis"):
        BackgroundJob.start("second", lambda _: None)
    job.cancel()
    assert job.wait(3) == "stopped"
    assert done.is_set()
    followup = BackgroundJob.start("followup", lambda _: "usable")
    assert followup.wait(3) == "usable"
