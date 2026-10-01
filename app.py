"""Streamlit CSV triage with session-owned datasets and cancellable background work."""
from pathlib import Path
import time

import pandas as pd
import streamlit as st

from src.config import Settings, provider_key_name, provider_ready
from src.data.loader import load_dataset
from src.services.evidence import evidence_json
from src.services.jobs import BackgroundJob
from src.services.triage_service import TriageError, run_triage
from src.ui.components import show_report, show_trace

EXAMPLES = ["Why might this dataset cause problems during training?",
    "Does this dataset contain missing values?", "Are there duplicate rows?",
    "Are any columns likely to be IDs?", "Are there extreme numeric outliers?",
    "Is my target class imbalanced?", "Are any numerical features suspiciously correlated?"]
SAMPLE_ROOT = Path(__file__).parent / "data" / "samples"

def clear_report():
    for key in ("triage_result", "triage_error", "result_question", "result_target"):
        st.session_state.pop(key, None)

def release_dataset():
    dataset = st.session_state.pop("dataset", None)
    if dataset is not None:
        dataset.close()
    clear_report()
    st.session_state.pop("import_error", None)
    st.session_state.pop("numeric_subset_widget", None)
    st.session_state.pop("selected_coverage", None)

def upload_changed():
    release_dataset()
    st.session_state.pending_upload = True

def reset():
    release_dataset()
    st.session_state.pop("csv_upload", None)
    st.session_state.pending_upload = False
    st.session_state.pop("selected_target", None)
    st.session_state.pop("question_widget", None)
    st.session_state.pop("current_question", None)

def watch_job_body():
    job = st.session_state.get("job")
    if job is None:
        return
    if not job.future.done():
        st.info(f"{job.stage} · {time.monotonic() - job.started:.1f} seconds")
        if st.button("Cancel current operation", disabled=job.cancel_event.is_set()):
            job.cancel()
        st.caption("Cancellation waits for active work to stop; files are retained until then.")
        return
    st.session_state.pop("job", None)
    st.session_state.restore_question = True
    try:
        value = job.future.result()
        if job.cancel_event.is_set():
            if job.kind == "import":
                value.close()
            st.session_state.import_error = "Operation cancelled. You can load a dataset or run again."
        elif job.kind == "import":
            value.import_seconds = round((job.finished or time.monotonic()) - job.started, 3)
            st.session_state.dataset = value
            st.session_state.pop("import_error", None)
        else:
            st.session_state.triage_result = value
    except Exception as exc:
        if job.cancel_event.is_set():
            st.session_state.import_error = "Operation cancelled. You can load a dataset or run again."
        elif isinstance(exc, TriageError):
            st.session_state.triage_error = exc
        else:
            st.session_state.import_error = str(exc)
    st.rerun()

watch_job = st.fragment(run_every=0.5)(watch_job_body)

def main():
    st.set_page_config(page_title="CSV Data Quality Triage Agent", layout="wide")
    st.title("CSV Data Quality Triage Agent")
    st.caption("The agent chooses relevant checks. Local tools calculate the evidence.")
    try:
        settings = Settings()
    except ValueError as exc:
        st.error(f"Configuration error: {exc}")
        return
    busy = st.session_state.get("job") is not None
    with st.sidebar:
        st.header("Dataset")
        st.caption(f"Upload limit: {settings.max_upload_mb} MB ({settings.max_upload_mb * 1024**2:,} bytes)")
        backend = st.selectbox("Backend for next import", ["auto", "duckdb", "pandas"], disabled=busy,
            help="Auto uses Pandas for small files and DuckDB for larger files. Applies to the next import.")
        upload = st.file_uploader("Upload CSV", type=["csv"], key="csv_upload", disabled=busy,
                                  max_upload_size=settings.max_upload_mb, on_change=upload_changed)
        if st.button("Reset dataset and report", disabled=busy, on_click=reset):
            st.rerun()
        with st.expander("Try a sample"):
            sample = st.selectbox("Sample CSV", sorted(p.name for p in SAMPLE_ROOT.glob("*.csv")), disabled=busy)
            sample_clicked = st.button("Load sample CSV", disabled=busy)
        if sample_clicked:
            release_dataset()
            def import_sample(job):
                with (SAMPLE_ROOT / sample).open("rb") as stream:
                    return load_dataset(stream, sample, settings, backend, job.progress, job.cancel_event)
            try:
                st.session_state.job = BackgroundJob.start("import", import_sample)
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))
        if st.session_state.pop("pending_upload", False) and upload is not None:
            try:
                st.session_state.job = BackgroundJob.start("import", lambda job:
                    load_dataset(upload, upload.name, settings, backend, job.progress, job.cancel_event))
                st.rerun()
            except RuntimeError as exc:
                st.session_state.import_error = str(exc)
        dataset = st.session_state.get("dataset")
        st.write("Loaded" if dataset else "No valid CSV loaded")
        target = st.selectbox("Target column (optional)", [None] + list(dataset.columns) if dataset else [None],
            key="target_widget", disabled=busy, format_func=lambda value: "None selected" if value is None else str(value))
        if target != st.session_state.get("selected_target"):
            st.session_state.selected_target = target
            clear_report()
        st.caption(f"Model: {settings.provider} / {settings.model}")
        st.write("API key configured" if provider_ready(settings) else f"{provider_key_name(settings) or 'Provider key'} not configured")
    if st.session_state.get("import_error"):
        st.error(st.session_state.import_error)
    if dataset is None:
        if busy:
            watch_job()
        else:
            st.info("Upload a CSV or load a sample to see its profile and ask a question.")
        return
    for warning in dataset.warnings:
        st.warning(warning)
    st.subheader("Dataset overview")
    st.write(f"**{dataset.filename}** · {dataset.row_count:,} rows · {len(dataset.columns)} columns · {dataset.encoding}")
    st.caption(f"Backend: {dataset.backend} · File size: {dataset.file_bytes:,} bytes · SHA-256: {dataset.fingerprint[:16]}…")
    if hasattr(dataset, "import_seconds"):
        st.caption(f"Import wall time: {dataset.import_seconds:.3f}s (local copying, validation and backend import; upload transfer excluded)")
    visible = dataset.columns[:settings.max_schema_columns]
    if target and target not in visible:
        visible = visible[:-1] + [target]
    st.dataframe([{"column": c, "dtype": dataset.dtypes[c], "nulls": dataset.null_counts[c]} for c in visible], hide_index=True)
    if len(visible) < len(dataset.columns):
        st.caption(f"Overview shows {len(visible)} of {len(dataset.columns)} columns. Selected target is always included.")
    with st.expander("Preview (first 10 rows)"):
        st.dataframe(dataset.preview().loc[:, visible], hide_index=True)
    numeric = [c for c in dataset.columns if pd.api.types.is_numeric_dtype(dataset.dtypes[c]) and c != target]
    with st.expander("Numerical check coverage"):
        columns = st.multiselect("Numeric columns to assess (optional)", numeric, max_selections=settings.max_numeric_columns,
            key="numeric_subset_widget", disabled=busy, help="An empty selection uses eligible columns. Wide correlation checks require an explicit subset.")
        st.caption(f"Correlation limit: {settings.max_numeric_columns} numeric columns. Checks disclose any omitted columns.")
    coverage = tuple(columns)
    if coverage != st.session_state.get("selected_coverage", ()):
        st.session_state.selected_coverage = coverage
        clear_report()
    st.subheader("Ask a question")
    st.caption("Examples: " + " · ".join(EXAMPLES))
    if st.session_state.pop("restore_question", False) or "question_widget" not in st.session_state:
        st.session_state.question_widget = st.session_state.get("current_question", EXAMPLES[0])
    with st.form("triage_form"):
        question = st.text_area("Data-quality question", key="question_widget", disabled=busy)
        submitted = st.form_submit_button("Run Triage", disabled=busy or not provider_ready(settings))
    if not provider_ready(settings):
        st.info(f"Set {provider_key_name(settings)} in the root .env and restart Streamlit to enable triage.")
    if submitted:
        clear_report()
        st.session_state.result_question = question
        st.session_state.current_question = question
        st.session_state.restore_question = True
        st.session_state.result_target = target
        try:
            def investigate(job):
                job.progress("Agent selecting and running diagnostics")
                return run_triage(dataset, question, target, settings, columns=columns or None,
                                  cancel_event=job.cancel_event, progress=job.progress)
            st.session_state.job = BackgroundJob.start("triage", investigate, dataset.interrupt)
            st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))
    error = st.session_state.get("triage_error")
    if error:
        st.error(str(error))
        show_trace(error.trace)
    result = st.session_state.get("triage_result")
    if result:
        st.caption("Question for this report: " + st.session_state.get("result_question", question))
        show_trace(result.trace)
        show_report(result.report)
        metadata = result.metadata or {}
        st.caption(f"Local diagnostics: {metadata.get('local_compute_seconds', 0):.3f}s · Total run: {metadata.get('total_seconds', 0):.3f}s")
        st.download_button("Download run evidence (JSON)", evidence_json(result,
            st.session_state.get("result_question", question), dataset,
            st.session_state.get("result_target", target)), file_name="csv_triage_evidence.json", mime="application/json")
    st.caption("Raw rows stay local; schema and aggregate observations are sent to the selected provider. The upload buffer still uses memory.")
    if busy:
        watch_job()

if __name__ == "__main__":
    main()
