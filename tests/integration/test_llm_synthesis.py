"""LLM narrative survives validation alongside independently verified scope.

These tests use the real LCEL/agent/schema and Streamlit renderer with scripted
model responses. They establish wiring and rejection rules, not live LLM quality.
"""

from copy import deepcopy
import json

import pandas as pd
import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from streamlit.testing.v1 import AppTest

from src.agent.report_chain import ReportParseError, create_report
from src.data.backends.pandas_backend import PandasDataset
from src.diagnostics.imbalance import class_imbalance_check
from src.services.evidence import evidence_json
from src.services.triage_service import run_triage


SUMMARY = "The selected target has a majority/minority ratio of 1.5:1. The tool returned no imbalance finding; this does not establish model fairness."
INTERPRETATION = "There is a target-frequency difference below this check's finding trigger. Review per-class behavior rather than automatically changing the distribution."
NEXT_STEP = "Use a stratified split and examine minority-class precision and recall before choosing sampling or weights."


def narrative_payload():
    return {"summary": SUMMARY, "issues": [], "tools_used": ["class_imbalance_check"], "limitations": [],
            "interpretation": [{"text": INTERPRETATION, "source_tools": ["class_imbalance_check"]}],
            "next_steps": [NEXT_STEP], "assessment_summary": "Model assessment text should not become verified scope."}


def target_frame():
    return pd.DataFrame({"label": ["negative"] * 60 + ["positive"] * 40})


def target_observation():
    result = class_imbalance_check(target_frame(), "label")
    assert result["data"]["majority_minority_ratio"] == 1.5 and not result["findings"]
    return {"tool": "class_imbalance_check", "status": "ok", "summary": result["summary"], "result": result}


class SynthesisModel(BaseChatModel):
    @property
    def _llm_type(self):
        return "synthesis-scripted-integration"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if "Create a concise CSV data-quality report" in str(messages[0].content):
            message = AIMessage(content=json.dumps(narrative_payload()))
        elif any(isinstance(item, ToolMessage) for item in messages):
            message = AIMessage(content="Investigation finished.")
        else:
            message = AIMessage(content="", tool_calls=[{
                "name": "class_imbalance_check", "args": {"reason": "The user asked about the selected target distribution."},
                "id": "synthesis_target", "type": "tool_call"}])
        return ChatResult(generations=[ChatGeneration(message=message)])


def test_full_agent_explains_nonfinding_ratio_without_overwriting_llm_narrative():
    result = run_triage(target_frame(), "Is the selected target distribution worth reviewing?", "label", model=SynthesisModel())
    assert result.trace[0]["result"]["data"]["majority_minority_ratio"] == 1.5
    assert result.report.issues == []
    assert result.report.summary == SUMMARY
    assert result.report.interpretation[0].text == INTERPRETATION
    assert result.report.interpretation[0].source_tools == ["class_imbalance_check"]
    assert result.report.next_steps == [NEXT_STEP]
    assert result.report.assessment_summary.startswith("0 verified finding(s) from 1 completed diagnostic(s)")
    assert "Model assessment text" not in result.report.assessment_summary
    assert result.trace[0]["selection_reason"] == "The user asked about the selected target distribution."


@pytest.mark.parametrize("mutation,error", [
    ("summary_number", "numeric value absent"),
    ("summary_integer_period", "numeric value absent"),
    ("summary_leading_decimal", "numeric value absent"),
    ("interpretation_number", "numeric value absent"),
    ("unknown_source", "tool that did not run"),
    ("broad_assurance", "unsupported assurance"),
    ("unrelated_negation", "unsupported assurance"),
])
def test_unsupported_narrative_rejected_after_one_repair(mutation, error):
    payload = narrative_payload()
    if mutation == "summary_number":
        payload["summary"] = "The selected target ratio is 7.25:1."
    elif mutation == "summary_integer_period":
        payload["summary"] = "The supplied dataset has 77 records."
    elif mutation == "summary_leading_decimal":
        payload["summary"] = "The observed minority recall is .77."
    elif mutation == "interpretation_number":
        payload["interpretation"][0]["text"] = "The observed minority recall is 0.77."
    elif mutation == "unknown_source":
        payload["interpretation"][0]["source_tools"] = ["correlation_check"]
    elif mutation == "unrelated_negation":
        payload["summary"] = "Correlation was not assessed. The dataset is completely clean."
    else:
        payload["summary"] = "The dataset is completely clean."
    calls = []
    def model(prompt):
        calls.append(prompt)
        return json.dumps(payload)
    with pytest.raises(ReportParseError, match=error) as failure:
        create_report(RunnableLambda(model), "Explain the target distribution.", "label", [target_observation()])
    assert len(calls) == 2
    assert json.loads(failure.value.raw_response) == payload


def test_invalid_narrative_can_be_repaired_to_supported_model_synthesis():
    bad = narrative_payload()
    bad["interpretation"][0]["source_tools"] = ["duplicate_rows_check"]
    responses = iter([bad, narrative_payload()])
    calls = []
    def model(prompt):
        calls.append(prompt)
        return json.dumps(next(responses))
    report = create_report(RunnableLambda(model), "Explain the target distribution.", "label", [target_observation()])
    assert len(calls) == 2
    assert report.summary == SUMMARY
    assert report.interpretation[0].source_tools == ["class_imbalance_check"]
    assert report.next_steps == [NEXT_STEP]


def test_repeated_skipped_call_does_not_hide_earlier_cited_numeric_evidence():
    payload = narrative_payload()
    payload["interpretation"][0]["text"] = "A majority/minority ratio of 1.5:1 does not by itself determine classification performance."
    skipped = {"tool": "class_imbalance_check", "status": "skipped",
               "summary": "This diagnostic already ran; use its previous observation.", "data": {}, "findings": []}
    repeated = {"tool": "class_imbalance_check", "status": "skipped", "summary": skipped["summary"], "result": skipped}
    report = create_report(RunnableLambda(lambda _: json.dumps(payload)), "Explain the target distribution.", "label", [target_observation(), repeated])
    assert report.interpretation[0].text == payload["interpretation"][0]["text"]
    assert report.tools_used == ["class_imbalance_check"]
    assert skipped["summary"] in report.limitations


def test_negated_caution_is_retained_instead_of_mistaken_for_clean_assurance():
    payload = narrative_payload()
    payload["summary"] = "The selected target cannot be described as fully balanced from this check alone."
    report = create_report(RunnableLambda(lambda _: json.dumps(payload)), "Explain the target distribution.", "label", [target_observation()])
    assert report.summary == payload["summary"]
    assert report.interpretation[0].text == INTERPRETATION


@pytest.mark.parametrize("missing_field,message", [
    ("interpretation", "Explain the tool observations"),
    ("next_steps", "at least one suggested next step"),
])
def test_fresh_report_cannot_silently_drop_interpretation_or_followup(missing_field, message):
    payload = narrative_payload()
    payload[missing_field] = []
    calls = []
    def model(prompt):
        calls.append(prompt)
        return json.dumps(payload)
    with pytest.raises(ReportParseError, match=message):
        create_report(RunnableLambda(model), "Explain the target distribution.", "label", [target_observation()])
    assert len(calls) == 2


def test_no_tool_target_guidance_has_narrative_without_invented_statistics():
    payload = {"summary": "The target distribution cannot be assessed without a selected target.", "issues": [],
               "interpretation": [], "next_steps": ["Choose a categorical target and ask about its class frequencies."],
               "tools_used": [], "limitations": []}
    report = create_report(RunnableLambda(lambda _: json.dumps(payload)), "Is my target imbalanced?", None, [])
    assert report.summary == payload["summary"]
    assert report.next_steps == payload["next_steps"]
    assert report.issues == [] and report.tools_used == [] and report.interpretation == []
    assert "Select a target column to assess class imbalance." in report.limitations
    fabricated = deepcopy(payload)
    fabricated["summary"] = "The unselected target has a class ratio of 9:1."
    with pytest.raises(ReportParseError, match="numeric value absent"):
        create_report(RunnableLambda(lambda _: json.dumps(fabricated)), "Is my target imbalanced?", None, [])


def test_coverage_and_failed_tool_limits_survive_model_explanation():
    observation = target_observation()
    observation["result"]["execution"] = {"columns_omitted": 2, "coverage_limitation": "Only the selected target distribution was assessed."}
    failed_result = {"tool": "duplicate_rows_check", "status": "error", "summary": "Diagnostic failed: RuntimeError", "data": {}, "findings": []}
    failed = {"tool": "duplicate_rows_check", "status": "error", "summary": failed_result["summary"], "result": failed_result}
    payload = narrative_payload()
    payload["limitations"] = ["Model claims all checks completed."]
    report = create_report(RunnableLambda(lambda _: json.dumps(payload)), "Explain the distribution and check duplicates.", "label", [observation, failed])
    assert report.summary == SUMMARY and report.next_steps == [NEXT_STEP]
    assert "Diagnostic failed: RuntimeError" in report.limitations
    assert "Only the selected target distribution was assessed." in report.limitations
    assert any("did not assess 2 columns" in item for item in report.limitations)
    assert "Model claims all checks completed." not in report.limitations
    assert report.issues == []


def test_synthesis_survives_original_evidence_export_and_actual_streamlit_render():
    handle = PandasDataset.from_frame(target_frame(), "moderate_classes.csv")
    try:
        result = run_triage(handle, "Explain the selected target distribution.", "label", model=SynthesisModel())
        exported = json.loads(evidence_json(result, "Explain the selected target distribution.", handle, "label"))
        assert exported["report"]["summary"] == SUMMARY
        assert exported["report"]["interpretation"][0]["text"] == INTERPRETATION
        assert exported["report"]["next_steps"] == [NEXT_STEP]
        assert exported["trace"][0]["selection_reason"]
        assert exported["trace"][0]["result"]["data"]["majority_minority_ratio"] == 1.5
        source = ("import json\nfrom src.models.schemas import DataQualityReport\n"
                  "from src.ui.components import show_report, show_trace\n"
                  f"bundle = json.loads({json.dumps(exported)!r})\n"
                  "show_trace(bundle['trace'])\nshow_report(DataQualityReport.model_validate(bundle['report']))\n")
        app = AppTest.from_string(source).run()
        assert not app.exception
        markdown = "\n".join(str(item.value) for item in app.markdown)
        captions = "\n".join(str(item.value) for item in app.caption)
        assert "LLM summary" in markdown and SUMMARY in markdown
        assert "LLM interpretation" in markdown and INTERPRETATION in markdown
        assert "Suggested next steps" in markdown and NEXT_STEP in markdown
        assert "Based on: class_imbalance_check" in captions
        assert "Verified scope: 0 verified finding(s)" in captions
        assert any("No verified issue findings" in item.value for item in app.info)
    finally:
        handle.close()
