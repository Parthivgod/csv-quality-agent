"""Presentation of observable diagnostic events and validated reports."""

import streamlit as st

from src.models.schemas import DataQualityReport


def show_trace(events: list[dict]) -> None:
    st.subheader("Tool-call trace")
    if not events:
        st.info("No diagnostic tool was called.")
    for event in events:
        with st.expander(f"{event['sequence']}. {event['tool']} — {event['status']}", expanded=True):
            st.write(event["summary"])
            st.caption(f"Arguments: {event['arguments']}")
            st.json(event["result"]["data"])


def show_report(report: DataQualityReport) -> None:
    st.subheader("Structured diagnosis")
    st.write(report.summary)
    if not report.issues:
        st.info("No issue was supported by the selected diagnostics.")
    for issue in report.issues:
        with st.container(border=True):
            st.markdown(f"**{issue.issue}** · {issue.severity.upper()}")
            st.write(f"Column: {issue.column or 'dataset-wide'}")
            st.write(f"Evidence: {issue.evidence}")
            st.write(f"Potential impact: {issue.impact}")
            st.write(f"Recommended action: {issue.recommendation}")
            st.caption(f"Source tool: {issue.source_tool}")
    st.write("Tools used: " + (", ".join(report.tools_used) or "none"))
    if report.limitations:
        st.write("Limitations")
        for item in report.limitations:
            st.write(f"- {item}")
    with st.expander("Raw structured JSON"):
        st.json(report.model_dump())
