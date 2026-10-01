"""Separate Streamlit evidence harness: controlled failure, never a production switch.

Run: python -m streamlit run scripts/phase3_failure_demo.py --server.port 8504
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from scripts.evaluate_phase3 import SCENARIOS, evaluate_scenario
from src.config import Settings, provider_ready
from src.models.schemas import DataQualityReport
from src.ui.components import show_report, show_trace

st.set_page_config(page_title="Controlled tool failure evidence", layout="wide")
st.title("Controlled tool failure evidence")
st.warning("This separate test harness deliberately makes the duplicate tool fail. The main app's diagnostics are unchanged.")
st.caption("Synthetic file: corrupted_missing_duplicates.csv · Target: none · Live Groq orchestration")
scenario = next(case for case in SCENARIOS if case.identifier == "T06")
st.write("Question: " + scenario.question)
settings = Settings()
if st.button("Run controlled failure", disabled=not provider_ready(settings)):
    output = ROOT / "docs/evaluation/phase3/scenarios"
    with st.spinner("Running the full live agent and report chain with controlled injection..."):
        st.session_state.record = evaluate_scenario(scenario, output, live=True, settings=settings)
record = st.session_state.get("record")
if record:
    output = ROOT / "docs/evaluation/phase3/scenarios"
    st.write("Evaluation result: " + record["status"])
    st.caption("Attempt: " + record["attempt"])
    trace = json.loads((output / record["trace_file"]).read_text(encoding="utf-8"))
    payload = json.loads((output / record["report_file"]).read_text(encoding="utf-8"))
    show_trace(trace)
    if payload:
        show_report(DataQualityReport.model_validate(payload))
    else:
        st.error("Report did not complete; inspect the saved attempt and retry after resolving the cause.")
    st.caption("Controlled injection is isolated to this process and scoped to the evaluated run.")
