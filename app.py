"""Streamlit entry point for the CSV Data Quality Triage Agent."""

import hashlib

import streamlit as st

from src.config import Settings, provider_ready
from src.data.loader import CSVLoadError, load_csv
from src.diagnostics.profile import dataset_profile
from src.services.triage_service import TriageError, run_triage
from src.ui.components import show_report, show_trace


EXAMPLES = [
    "Why might this dataset cause problems during training?",
    "Does this dataset contain missing values?",
    "Are there duplicate rows?",
    "Are any columns likely to be IDs?",
    "Are there extreme numeric outliers?",
    "Is my target class imbalanced?",
    "Are any numerical features suspiciously correlated?",
]


def main() -> None:
    st.set_page_config(page_title="CSV Data Quality Triage Agent", layout="wide")
    st.title("CSV Data Quality Triage Agent")
    st.caption("The agent chooses relevant checks. Python tools calculate the evidence.")
    try:
        settings = Settings()
    except ValueError as exc:
        st.error(f"Configuration error: {exc}")
        return

    with st.sidebar:
        st.header("Dataset")
        upload = st.file_uploader("Upload CSV", type=["csv"], key="csv_upload")
        if st.button("Reset dataset and report"):
            for key in ("loaded_csv", "file_identity", "selected_target", "triage_result", "triage_error", "csv_upload"):
                st.session_state.pop(key, None)
            st.rerun()
        if upload is not None:
            content = upload.getvalue()
            identity = (upload.name, hashlib.sha256(content).hexdigest())
            if identity != st.session_state.get("file_identity"):
                st.session_state.pop("triage_result", None)
                st.session_state.pop("triage_error", None)
                try:
                    st.session_state.loaded_csv = load_csv(content, upload.name, settings.max_upload_mb)
                    st.session_state.file_identity = identity
                except CSVLoadError as exc:
                    st.session_state.pop("loaded_csv", None)
                    st.error(str(exc))
        else:
            st.session_state.pop("loaded_csv", None)
            st.session_state.pop("file_identity", None)
            st.session_state.pop("triage_result", None)
            st.session_state.pop("triage_error", None)
        loaded = st.session_state.get("loaded_csv")
        st.write("Loaded" if loaded else "No valid CSV loaded")
        target = st.selectbox("Target column (optional)", [None] + list(loaded.frame.columns) if loaded else [None],
                              format_func=lambda value: "None selected" if value is None else str(value))
        if target != st.session_state.get("selected_target"):
            st.session_state.selected_target = target
            st.session_state.pop("triage_result", None)
            st.session_state.pop("triage_error", None)
        st.caption(f"Model: {settings.provider} / {settings.model}")
        st.write("API key configured" if provider_ready(settings) else "API key not configured")

    if not loaded:
        st.info("Upload a CSV to see its profile and ask a question.")
        return
    frame = loaded.frame
    for warning in loaded.warnings:
        st.warning(warning)
    st.subheader("Dataset overview")
    st.write(f"**{loaded.filename}** · {len(frame)} rows · {len(frame.columns)} columns · {loaded.encoding}")
    profile = dataset_profile(frame)["data"]
    st.dataframe([{"column": str(c), "dtype": profile["dtypes"].get(str(c), str(frame[c].dtype)),
                   "nulls": int(frame[c].isna().sum())} for c in frame.columns], hide_index=True)
    with st.expander("Preview (first 10 rows)"):
        st.dataframe(frame.head(10), hide_index=True)

    st.subheader("Ask a question")
    st.caption("Examples: " + " · ".join(EXAMPLES))
    with st.form("triage_form"):
        question = st.text_area("Data-quality question", value=EXAMPLES[0])
        submitted = st.form_submit_button("Run Triage", disabled=not provider_ready(settings))
    if not provider_ready(settings):
        st.info("Set the selected provider's API key in .env to enable agent triage. Dataset preview works without it.")
    if submitted:
        with st.spinner("The agent is selecting and running diagnostics..."):
            try:
                st.session_state.triage_result = run_triage(frame, question, target, settings)
                st.session_state.pop("triage_error", None)
            except TriageError as exc:
                st.session_state.pop("triage_result", None)
                st.session_state.triage_error = exc
    error = st.session_state.get("triage_error")
    if error:
        st.error(str(error))
        show_trace(error.trace)
        if error.raw_response:
            with st.expander("Raw report response for debugging"):
                st.code(error.raw_response)
    result = st.session_state.get("triage_result")
    if result:
        show_trace(result.trace)
        show_report(result.report)


if __name__ == "__main__":
    main()
