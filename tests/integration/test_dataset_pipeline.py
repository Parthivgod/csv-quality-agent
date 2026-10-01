"""Actual LangChain graph with both dataset handles and a local scripted model.

These checks establish wiring and evidence enforcement, not live model quality.
"""

import json
from io import BytesIO
from pathlib import Path
from threading import Event

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from src.config import Settings
from src.data.loader import load_dataset
from src.services.triage_service import TriageError, run_triage


SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples"


class DatasetScriptedModel(BaseChatModel):
    plan: list[str]
    omit_report_issues: bool = False
    fabricate_report_issue: bool = False

    @property
    def _llm_type(self):
        return "dataset-pipeline-scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if "Create a concise CSV data-quality report" in str(messages[0].content):
            observations = json.loads(str(messages[-1].content).split("Tool observations: ", 1)[1])
            issues = [{**finding, "source_tool": item["tool"]}
                      for item in observations for finding in item.get("findings", [])]
            if self.omit_report_issues:
                issues = []
            if self.fabricate_report_issue:
                issues = [{"issue": "Invented failure", "severity": "high", "column": "x",
                           "evidence": "made-up count", "impact": "made-up impact",
                           "recommendation": "made-up action", "source_tool": "outlier_check"}]
            response = {"summary": "The selected diagnostics returned evidence for contextual review.", "issues": issues,
                        "tools_used": ["made-up tool"], "limitations": ["Invented complete scan"],
                        "interpretation": [{"text": "This observation applies to the selected check and its stated coverage.",
                                            "source_tools": [item["tool"]]} for item in observations[:6]],
                        "next_steps": ["Review the supplied evidence and limitations before changing the dataset."]}
            message = AIMessage(content=json.dumps(response))
        else:
            completed = sum(isinstance(m, ToolMessage) for m in messages)
            if completed < len(self.plan):
                message = AIMessage(content="", tool_calls=[{
                    "name": self.plan[completed], "args": {}, "id": f"dataset_{completed}", "type": "tool_call"
                }])
            else:
                message = AIMessage(content="Investigation finished.")
        return ChatResult(generations=[ChatGeneration(message=message)])


@pytest.fixture(params=["pandas", "duckdb"])
def backend(request):
    return request.param


def assert_report_exactly_grounded(result):
    supplied = {
        (event["tool"], json.dumps(finding, sort_keys=True))
        for event in result.trace if event["status"] == "ok"
        for finding in event["result"]["findings"]
    }
    emitted = set()
    for issue in result.report.issues:
        payload = issue.model_dump()
        tool = payload.pop("source_tool")
        emitted.add((tool, json.dumps(payload, sort_keys=True)))
    assert emitted == supplied
    assert "100%" not in result.report.summary
    assert "Invented complete scan" not in result.report.limitations


def test_handle_numeric_fullgraph_preserves_findings_and_provenance(backend):
    handle = load_dataset(BytesIO((SAMPLES / "corrupted_outliers_corr.csv").read_bytes()), "numeric.csv", backend=backend)
    try:
        result = run_triage(handle, "Numerical outliers and relationships?",
                            model=DatasetScriptedModel(plan=["outlier_check", "correlation_check"], omit_report_issues=True))
        assert [e["tool"] for e in result.trace] == ["outlier_check", "correlation_check"]
        assert {i.issue for i in result.report.issues} == {"IQR outliers", "Strong feature correlation"}
        assert_report_exactly_grounded(result)
        assert result.report.limitations == []
        assert result.metadata["dataset_hash"] == handle.fingerprint
        for event in result.trace:
            execution = event["result"]["execution"]
            assert execution["backend"] == backend
            assert execution["dataset_hash"] == handle.fingerprint
            assert execution["exact"] is True
    finally:
        handle.close()


def test_handle_target_fullgraph_and_missing_target_limitation(backend):
    handle = load_dataset(BytesIO((SAMPLES / "corrupted_class_imbalance.csv").read_bytes()), "classes.csv", backend=backend)
    try:
        plan = ["class_imbalance_check"]
        result = run_triage(handle, "Is my target imbalanced?", target="label", model=DatasetScriptedModel(plan=plan))
        assert len(result.report.issues) == 1
        assert "ratio 9.0:1" in result.report.issues[0].evidence
        assert_report_exactly_grounded(result)
        no_target = run_triage(handle, "Is my target imbalanced?", model=DatasetScriptedModel(plan=plan))
        assert no_target.trace[0]["status"] == "skipped"
        assert no_target.report.issues == []
        assert any("target column" in limitation for limitation in no_target.report.limitations)
    finally:
        handle.close()


def test_handle_controlled_failure_is_visible_without_invented_issue(backend, monkeypatch):
    handle = load_dataset(BytesIO((SAMPLES / "corrupted_missing_duplicates.csv").read_bytes()), "issues.csv", backend=backend)
    actual = handle.run_check

    def failure(name, **kwargs):
        if name == "duplicate_rows_check":
            raise RuntimeError("injected test failure; sensitive path must not escape")
        return actual(name, **kwargs)

    monkeypatch.setattr(handle, "run_check", failure)
    try:
        result = run_triage(handle, "Missing and duplicated?", model=DatasetScriptedModel(plan=["missing_values_check", "duplicate_rows_check"]))
        assert [e["status"] for e in result.trace] == ["ok", "error"]
        assert_report_exactly_grounded(result)
        assert {i.issue for i in result.report.issues} == {"Missing values"}
        assert "Diagnostic failed: RuntimeError" in result.report.limitations
        assert "sensitive path" not in json.dumps(result.trace)
    finally:
        handle.close()


def test_handle_scope_is_reported_as_partial_and_too_wide_scan_skips(backend):
    header = ",".join(f"x{i}" for i in range(21))
    rows = "\n".join(",".join(str(i+j) for i in range(21)) for j in range(5))
    handle = load_dataset(BytesIO((header + "\n" + rows + "\n").encode()), "wide.csv", backend=backend)
    try:
        full = run_triage(handle, "Numeric relationships?", model=DatasetScriptedModel(plan=["correlation_check"]))
        assert full.trace[0]["status"] == "skipped"
        assert full.report.issues == []
        assert any("at most 20" in item for item in full.report.limitations)
        bounded = run_triage(handle, "Numeric relationships?", columns=["x0", "x1"],
                             model=DatasetScriptedModel(plan=["correlation_check"]))
        assert len(bounded.report.issues) == 1
        assert any("19 columns" in item for item in bounded.report.limitations)
        assert_report_exactly_grounded(bounded)
    finally:
        handle.close()


def test_bounded_fullgraph_validation_uses_only_transmitted_findings(backend):
    handle = load_dataset(BytesIO((SAMPLES / "corrupted_missing_duplicates.csv").read_bytes()), "missing.csv", backend=backend)
    try:
        settings = Settings(max_findings_per_tool=1, max_observation_bytes=2048)
        result = run_triage(handle, "Missing values?", settings=settings,
                            model=DatasetScriptedModel(plan=["missing_values_check"], omit_report_issues=True))
        assert_report_exactly_grounded(result)
        assert len(result.report.issues) == 1
        assert len(result.full_results[0]["findings"]) == 2
        assert result.trace[0]["result"]["execution"]["findings_omitted"] == 1
        assert len(json.dumps(result.trace[0]["result"], ensure_ascii=False).encode("utf-8")) <= 2048
        assert any("bounded" in item for item in result.report.limitations)
    finally:
        handle.close()


def test_fullgraph_rejects_fabricated_evidence_after_retry(backend):
    handle = load_dataset(BytesIO((SAMPLES / "corrupted_outliers_corr.csv").read_bytes()), "numeric.csv", backend=backend)
    try:
        with pytest.raises(TriageError) as failure:
            run_triage(handle, "Numerical features?", model=DatasetScriptedModel(plan=["outlier_check"], fabricate_report_issue=True))
        assert "matching tool finding" in str(failure.value)
        assert failure.value.trace[0]["tool"] == "outlier_check"
        assert "made-up count" in failure.value.raw_response
        # A failed report never makes the underlying handle unusable.
        fresh = run_triage(handle, "Numerical features?", model=DatasetScriptedModel(plan=["outlier_check"]))
        assert fresh.trace[0]["result"]["execution"]["cache_hit"] is True
        assert_report_exactly_grounded(fresh)
    finally:
        handle.close()


def test_cancelled_fullgraph_can_be_followed_by_new_handle_run(backend):
    handle = load_dataset(BytesIO((SAMPLES / "corrupted_outliers_corr.csv").read_bytes()), "numeric.csv", backend=backend)
    try:
        cancellation = Event()
        cancellation.set()
        with pytest.raises(TriageError):
            run_triage(handle, "Numerical features?", cancel_event=cancellation,
                       model=DatasetScriptedModel(plan=["outlier_check"]))
        fresh = run_triage(handle, "Numerical features?", model=DatasetScriptedModel(plan=["outlier_check"]))
        assert fresh.trace[0]["status"] == "ok"
        assert_report_exactly_grounded(fresh)
    finally:
        handle.close()
