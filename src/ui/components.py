"""Presentation of observable diagnostic events and validated reports."""

import streamlit as st

from src.models.schemas import DataQualityReport


def show_trace(events: list[dict]) -> None:
    st.subheader("Tool-call trace")
    if not events:
        st.info("No diagnostic tool was called.")
    for event in events:
        if event.get("selection_reason"):
            st.write("LLM tool choice: " + event["selection_reason"])
        with st.expander(f"{event['sequence']}. {event['tool']} — {event['status']}", expanded=False):
            st.write(event["summary"])
            st.caption(f"Arguments: {event['arguments']}")
            st.json(event["result"]["data"], expanded=False)
            if event["result"].get("execution"):
                execution = event["result"]["execution"]
                st.caption(f"{execution.get('backend', 'local')} · {execution.get('elapsed_ms', 0):.2f}ms · cache hit: {execution.get('cache_hit', False)} · omitted columns: {execution.get('columns_omitted', 0)}")
                st.json(execution, expanded=False)


def show_report(report: DataQualityReport) -> None:
    st.subheader("Structured diagnosis")
    # Older saved/session reports predate model-written narrative fields.
    assessment = getattr(report, "assessment_summary", "")
    st.markdown("**LLM summary**" if assessment else "**Summary**")
    st.write(report.summary)
    if assessment:
        st.caption("Verified scope: " + assessment)
    st.markdown("**Verified findings**")
    if not report.issues:
        st.info("No verified issue findings were returned by the selected diagnostics.")
    for issue in report.issues:
        with st.container(border=True):
            st.markdown(f"**{issue.issue}** · {issue.severity.upper()}")
            st.write(f"Column: {issue.column or 'dataset-wide'}")
            st.write(f"Evidence: {issue.evidence}")
            st.write(f"Potential impact: {issue.impact}")
            st.write(f"Recommended action: {issue.recommendation}")
            st.caption(f"Source tool: {issue.source_tool}")
    if getattr(report, "interpretation", []):
        st.markdown("**LLM interpretation**")
        for item in report.interpretation:
            st.write(item.text)
            st.caption("Based on: " + ", ".join(item.source_tools))
    if getattr(report, "next_steps", []):
        st.markdown("**Suggested next steps**")
        for index, step in enumerate(report.next_steps, 1):
            st.write(f"{index}. {step}")
    st.write("Tools used: " + (", ".join(report.tools_used) or "none"))
    if report.limitations:
        st.write("Limitations")
        for item in report.limitations:
            st.write(f"- {item}")
    with st.expander("Raw structured JSON"):
        st.json(report.model_dump())
