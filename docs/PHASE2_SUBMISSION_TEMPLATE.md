# Phase 2 Submission — Progress Update
## CSV Data Quality Triage Agent

**Team:** Parthiv Godrihal (I024), Nilay Jain (I029)  
**Activity:** Tool-Augmented / Agentic LLM Application  
**Submission date:** 23 September 2026

---

## 1. GitHub / Colab Link

**Repository:** `<paste GitHub URL here>`

---

## 2. Current Progress

### Completed
- [ ] Repository and Python environment created
- [ ] Streamlit app launches
- [ ] CSV upload works
- [ ] Dataset profile shown
- [ ] Diagnostic functions implemented
- [ ] LangChain tools registered
- [ ] Agent can selectively call tools
- [ ] Tool-call trace visible
- [ ] Structured report parser working
- [ ] Corrupted sample dataset created
- [ ] Basic tests added

### In progress
- `<list current items>`

### Remaining for final submission
- `<list remaining items>`

---

## 3. Current Architecture

See `docs/ARCHITECTURE.md` and `docs/assets/csv_agent_architecture.png`.

Current flow:

`CSV Upload → Context Builder → Prompt / LangChain Agent → Selected Diagnostic Tools → Tool Trace → LCEL Report Chain → OutputParser → Streamlit Report`

---

## 4. Working Demonstration Scenario

**Dataset:** `<filename>`

**Question:**  
`<question asked to the agent>`

**Target column (if any):** `<target / none>`

**Tools selected by agent:**
1. `<tool>`
2. `<tool>`
3. `<tool>`

**Key findings:**
- `<finding with evidence>`
- `<finding with evidence>`

---

## 5. Screenshot / Output Evidence

Add committed screenshot paths:

- `docs/screenshots/01_upload.png`
- `docs/screenshots/02_tool_trace.png`
- `docs/screenshots/03_structured_report.png`

Suggested captions:
1. CSV successfully uploaded and profiled.
2. LangChain agent selectively invoking diagnostic tools.
3. Structured final report with severity, evidence and recommendation.

---

## 6. Problem Encountered

**Problem:**  
`<example: agent initially called every tool / parser returned invalid JSON / target-specific tool failed>`

**Cause:**  
`<brief cause>`

**Fix:**  
`<what was changed>`

**Result:**  
`<how behavior improved>`

---

## 7. Current Limitations

Examples:
- small/medium CSVs only,
- no automatic cleaning,
- target column must be selected manually for imbalance analysis,
- LLM API access is required for agent orchestration,
- advanced leakage detection is not yet implemented.

---

## 8. Next Steps Before Phase 3

- complete remaining tools,
- expand tests to at least five scenarios,
- document one tool failure/unexpected response and handling,
- add final sample inputs/outputs,
- polish README,
- incorporate instructor feedback,
- prepare 5–7 minute demo,
- prepare 3–4 page technical report,
- complete contribution statement.
