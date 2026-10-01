"""Actual Streamlit flows using local fixtures and real background imports."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.data import upload_store
from src.models.schemas import DataQualityReport
from src.services.triage_service import TriageResult
import src.services.triage_service as triage_module
from tests.integration.test_pipeline import ScriptedChatModel


APP = Path(__file__).resolve().parents[2] / "app.py"


def widget(elements, label):
    return next(item for item in elements if item.label == label)


def state_value(app, key, default=None):
    try:
        return app.session_state[key]
    except KeyError:
        return default


def settle(app):
    """Wait on the owned future, then execute the fragment's completion path."""
    for _ in range(4):
        job = state_value(app, "job")
        if job is None:
            break
        try:
            job.wait(timeout=10)
        except Exception:
            pass  # The app must render import failures itself.
        app.run(timeout=10)
    assert state_value(app, "job") is None
    assert not app.exception
    return app


def load_sample(app, filename, backend="pandas"):
    widget(app.selectbox, "Backend for next import").select(backend)
    widget(app.selectbox, "Sample CSV").select(filename)
    widget(app.button, "Load sample CSV").click()
    app.run(timeout=10)
    return settle(app)


@pytest.mark.parametrize("backend", ["pandas", "duckdb"])
def test_real_sample_import_and_reset_close_storage(tmp_path, monkeypatch, backend):
    monkeypatch.setattr(upload_store, "TEMP_ROOT", tmp_path / "owned")
    app = AppTest.from_file(APP).run(timeout=10)
    load_sample(app, "corrupted_outliers_corr.csv", backend)
    dataset = app.session_state["dataset"]
    try:
        assert dataset.backend == backend
        assert dataset.row_count == 30
        assert widget(app.selectbox, "Target column (optional)").options == ["None selected", "feature_x", "feature_y", "feature_z"]
        assert len(app.dataframe) == 2
        owned = dataset.storage.path
        widget(app.button, "Reset dataset and report").click().run(timeout=10)
        assert state_value(app, "dataset") is None
        assert not owned.exists()
        assert not app.exception
    finally:
        dataset.close()


def test_target_change_clears_old_report_and_invalid_replacement_cleans_dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(upload_store, "TEMP_ROOT", tmp_path / "owned")
    app = AppTest.from_file(APP).run(timeout=10)
    load_sample(app, "corrupted_class_imbalance.csv")
    first = app.session_state["dataset"]
    try:
        app.session_state["triage_result"] = TriageResult(DataQualityReport(summary="Old dataset result"), [])
        app.run(timeout=10)
        assert any(item.value == "Structured diagnosis" for item in app.subheader)
        widget(app.selectbox, "Target column (optional)").select("label").run(timeout=10)
        assert state_value(app, "triage_result") is None
        app.session_state["triage_result"] = TriageResult(DataQualityReport(summary="Old target result"), [])
        app.run(timeout=10)
        original_path = first.storage.path
        load_sample(app, "invalid_header_only.csv")
        assert state_value(app, "dataset") is None
        assert state_value(app, "triage_result") is None
        assert not original_path.exists()
        assert any("no data rows" in item.value for item in app.error)
        assert not list((tmp_path / "owned").glob("session-*"))
    finally:
        first.close()


def test_completed_background_run_retains_question_and_selected_target(tmp_path, monkeypatch):
    monkeypatch.setattr(upload_store, "TEMP_ROOT", tmp_path / "owned")
    original = triage_module.run_triage
    monkeypatch.setattr(triage_module, "run_triage", lambda *args, **kwargs:
                        original(*args, **kwargs, model=ScriptedChatModel()))
    app = AppTest.from_file(APP).run(timeout=10)
    load_sample(app, "corrupted_class_imbalance.csv", "duckdb")
    dataset = app.session_state["dataset"]
    try:
        widget(app.selectbox, "Target column (optional)").select("label").run(timeout=10)
        question = "Is my target distribution a problem?"
        widget(app.text_area, "Data-quality question").input(question)
        widget(app.button, "Run Triage").click().run(timeout=10)
        settle(app)
        assert widget(app.text_area, "Data-quality question").value == question
        assert widget(app.selectbox, "Target column (optional)").value == "label"
        assert app.session_state["triage_result"].report.issues[0].issue == "Class imbalance"
        assert app.session_state["result_question"] == question
    finally:
        dataset.close()
