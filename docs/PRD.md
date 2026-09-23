# Product Requirements Document (PRD)
## CSV Data Quality Triage Agent — Phase 2 Implementation

**Project:** CSV Data Quality Triage Agent  
**Activity:** Tool-Augmented / Agentic LLM Application  
**Phase:** Phase 2 — Partial Working System / Progress Update  
**Team:** Parthiv Godrihal (I024), Nilay Jain (I029)  
**Target submission:** 23 September 2026

---

## 1. Product Summary

The CSV Data Quality Triage Agent is an LLM-powered diagnostic application that accepts a CSV file and a natural-language question such as:

> “Why is this dataset causing problems during model training?”

Instead of blindly running every possible diagnostic, the LangChain agent should inspect the user objective and available dataset context, select only the relevant deterministic diagnostic tools, interpret their outputs, and return a structured data-quality report.

The deterministic tools are implemented with Pandas / NumPy / scikit-learn-style logic. The LLM is responsible for **orchestration and explanation**, not for inventing statistics.

---

## 2. Source-of-Truth Requirements

This implementation is derived from the Phase 1 proposal and the Lab 9 Activity 2 requirements.

### Phase 1 commitments to preserve
- CSV upload + natural-language user query.
- PromptTemplate + LCEL composition.
- LangChain agent with diagnostic tools.
- Deterministic Pandas / sklearn checks.
- Structured report with fields such as issue, severity, column, evidence and recommendation.
- Tool-call trace visible in the Streamlit interface.
- Deliberately corrupted datasets for evaluation against known ground truth.
- Selective tool invocation rather than running every check indiscriminately.

### Phase 2 deliverable target
Phase 2 must be able to show:
1. A GitHub repository or Colab link.
2. Brief implementation/progress notes.
3. Screenshot(s) or output from a partially working system.

The design also keeps Phase 3 requirements in view: a working repository, README, architecture diagram, sample inputs/outputs, test results, demo video and technical report.

---

## 3. Problem Statement

Machine-learning CSV datasets frequently contain problems that degrade model quality or cause training failures:
- missing values,
- duplicate rows,
- class imbalance,
- outliers,
- constant or near-constant columns,
- high-cardinality / identifier-like columns,
- suspiciously strong feature relationships,
- invalid or inconsistent data types.

Beginners often do not know which checks are relevant, how to interpret the results, or which issue should be fixed first. A fixed “run everything” profiler can also produce noisy output.

The proposed system solves this by combining:
- an LLM agent for selecting appropriate checks and explaining results, and
- deterministic diagnostic tools for reliable evidence.

---

## 4. Phase 2 Objective

Build a demonstrable vertical slice of the final application.

By the end of Phase 2, the system should support this flow:

1. User uploads a valid CSV.
2. App displays basic dataset metadata.
3. User optionally selects a target column.
4. User enters a data-quality question.
5. LangChain agent receives:
   - user objective,
   - compact dataset schema/profile,
   - available tool descriptions,
   - constraints.
6. Agent selectively calls diagnostic tools.
7. Tool outputs are logged and displayed.
8. Final result is transformed into a structured report.
9. At least two deliberately corrupted CSVs are used to produce screenshot/output evidence.

---

## 5. Users

### Primary user
A student, beginner ML practitioner, or analyst trying to understand why a tabular dataset may be unsuitable for model training.

### Secondary user
An instructor/evaluator reviewing whether the application correctly integrates LangChain components and demonstrates meaningful agent-tool interaction.

---

## 6. Functional Requirements

### FR-1: CSV Upload
The application shall allow a user to upload one CSV file through Streamlit.

**Acceptance criteria**
- Valid CSV loads successfully.
- Dataset dimensions and columns are displayed.
- Invalid/empty files return a readable error rather than crashing.
- Dataset is not written to permanent storage by default.

### FR-2: Dataset Context Builder
The system shall create a compact, deterministic context summary for the agent.

**Context should include**
- row count,
- column count,
- column names,
- inferred dtypes,
- numeric/categorical candidates,
- optional selected target,
- small safe sample or aggregated schema summary.

The full dataset should not be inserted into the LLM prompt.

### FR-3: Natural-Language Query
The user shall be able to ask questions such as:
- “Why might this dataset be bad for classification?”
- “Check whether the target is imbalanced.”
- “Are there suspicious ID columns?”
- “Why might a regression model struggle with this CSV?”

### FR-4: Agentic Tool Selection
The LangChain agent shall choose which diagnostics to invoke.

**Required behavior**
- Do not call every tool by default.
- Call target-dependent tools only if a target column is available.
- Prefer a small number of relevant calls.
- Never fabricate tool outputs.
- Stop and explain if required information is missing.

### FR-5: Diagnostic Tools
The Phase 2 implementation should include at least the following tools:

| Tool | Purpose | Phase 2 priority |
|---|---|---|
| `dataset_profile` | Shape, dtypes, null summary, cardinality overview | Must |
| `missing_values_check` | Missing count and percentage by column | Must |
| `duplicate_rows_check` | Duplicate row count and rate | Must |
| `constant_columns_check` | Constant / near-constant features | Must |
| `high_cardinality_check` | Identifier-like or excessively unique categorical columns | Must |
| `outlier_check` | Numeric outliers using IQR rule | Must |
| `class_imbalance_check` | Target distribution and imbalance ratio | Must if target exists |
| `correlation_check` | Very strong numeric relationships / possible redundancy | Should |
| `dtype_anomaly_check` | Mixed or suspicious inferred types | Could |

### FR-6: Tool Trace
The UI shall show a trace of:
- tool name,
- tool input,
- status,
- concise result summary.

This is important evidence that the solution is genuinely agentic.

### FR-7: Structured Report
The final answer shall be parsed into a structured report.

Recommended schema:

```json
{
  "summary": "Short overall diagnosis",
  "issues": [
    {
      "issue": "Missing values",
      "severity": "high",
      "column": "age",
      "evidence": "31.4% of values are missing",
      "impact": "Training may fail or become biased depending on preprocessing",
      "recommendation": "Investigate missingness and impute or remove with justification",
      "source_tool": "missing_values_check"
    }
  ],
  "tools_used": ["dataset_profile", "missing_values_check"],
  "limitations": ["Target column was not provided"]
}
```

### FR-8: Error Handling
The app shall handle:
- malformed CSV,
- empty dataset,
- missing target column,
- non-numeric outlier request,
- LLM/API failure,
- tool exception,
- output parsing failure.

A tool error should be surfaced as an explicit diagnostic event and should not crash the whole app.

---

## 7. Non-Functional Requirements

### Reliability
Deterministic evidence must come from tools, not from LLM estimation.

### Explainability
Every reported issue should reference its supporting tool result.

### Privacy
CSV content remains in the local Streamlit process unless required context is explicitly sent to the configured LLM API. Only compact schema/statistical context should be sent.

### Performance
Target Phase 2 datasets: small/medium educational CSVs. Recommended default upload limit: **20 MB**, configurable.

### Maintainability
Diagnostic tools must be independent Python functions with unit tests and then wrapped as LangChain tools.

### Reproducibility
Dependencies shall be pinned or bounded in `requirements.txt`; `.env.example` shall document required API settings.

---

## 8. UX Requirements

### Screen layout
**Sidebar**
- CSV uploader
- dataset status
- target column selector
- model/provider status
- reset button

**Main panel**
1. Dataset preview / profile
2. User question input
3. “Run Triage” button
4. Tool-call trace
5. Structured diagnosis
6. Raw JSON expander for debugging

### UX principles
- The user should understand what the agent checked.
- Tool execution should be transparent.
- Evidence should be numerical where possible.
- Error messages should tell the user what to fix.

---

## 9. Technical Architecture

See `docs/ARCHITECTURE.md` and `docs/assets/csv_agent_architecture.png`.

High-level flow:

`Streamlit UI → CSV Loader → Context Builder → Prompt + Agent → Diagnostic Tools → Tool Trace → Output Parser → Report UI`

---

## 10. LangChain Components

The implementation intentionally uses at least four components promised in Phase 1:

1. **PromptTemplate / ChatPromptTemplate**
   - agent role,
   - user objective,
   - dataset context,
   - tool-use rules,
   - non-hallucination constraints.

2. **Tool / Agent**
   - wraps deterministic diagnostic functions,
   - decides which checks to call and in what sequence.

3. **LCEL composition**
   - composes prompt preparation, agent execution and final reporting.

4. **OutputParser**
   - converts the final report to a defined Pydantic/JSON structure.

---

## 11. Tool Contracts

Every diagnostic tool should:
- accept only the minimum required arguments,
- return JSON-serializable data,
- include an explicit status (`ok`, `skipped`, `error`),
- avoid returning huge raw tables,
- include evidence needed for the final report.

Example:

```python
{
    "status": "ok",
    "tool": "missing_values_check",
    "issues": [
        {"column": "age", "missing_count": 314, "missing_pct": 31.4}
    ]
}
```

---

## 12. Deterministic Diagnostic Rules

These are implementation defaults, not immutable scientific standards. Keep them configurable.

### Missing values
- report all columns with missing values,
- severity suggestion:
  - `< 5%`: low,
  - `5–30%`: medium,
  - `> 30%`: high.

### Duplicate rows
- compute absolute count and percentage.

### Constant / near-constant
- constant: `nunique(dropna=False) <= 1`.
- optional near-constant rule: dominant value >= 95%.

### High cardinality
Potential identifier-like column if:
- unique ratio >= 0.90, and
- at least 20 non-null observations.

### Outliers
For numeric columns use the IQR rule:
- lower = Q1 - 1.5 × IQR
- upper = Q3 + 1.5 × IQR

Return count and percentage; do not automatically claim outliers are “bad”.

### Class imbalance
Only if a target column is supplied. Return:
- class counts,
- class proportions,
- majority/minority ratio.

### Suspicious correlations
For numeric feature pairs, flag very high absolute correlation (default `|r| >= 0.95`) as possible redundancy/leakage for review, not as proof of leakage.

---

## 13. Product Decisions

1. **Streamlit instead of a separate frontend/backend**
   - Fastest route to a complete academic demo.
   - Directly matches the Phase 1 UI commitment.

2. **LLM orchestrates; Python computes**
   - The model chooses tools and explains outputs.
   - Pandas/NumPy/sklearn logic calculates evidence.

3. **Provider-agnostic model configuration**
   - The code exposes a single model factory.
   - Default adapter can use `ChatMistralAI`; model name and API key stay in environment variables.
   - Swapping to another LangChain chat model should require minimal change.

4. **Target column is user-selectable**
   - More reliable than forcing the model to infer the ML target.
   - Class-imbalance checks are disabled when no target is selected.

5. **No automatic data cleaning in Phase 2**
   - The system diagnoses and recommends.
   - It does not mutate the uploaded dataset.

6. **No unrestricted Python execution by the LLM**
   - Only allowlisted diagnostic tools are callable.

7. **Compact dataset context**
   - Avoid sending the entire CSV to the model.
   - Use schema + aggregated statistics.

8. **Tool-call budget**
   - Recommended maximum: 6 diagnostic calls per user request.
   - Prevents loops, latency and “run everything” behavior.

9. **Traceability over hidden reasoning**
   - Show observable tool calls and outputs.
   - Do not expose internal chain-of-thought.

---

## 14. Phase 2 Acceptance Criteria

Phase 2 is ready to submit when all of the following are true:

- [ ] Repository created with the documented structure.
- [ ] Streamlit starts locally.
- [ ] A CSV can be uploaded.
- [ ] Basic schema/profile is shown.
- [ ] User can ask a question.
- [ ] Agent calls at least one diagnostic tool.
- [ ] Tool trace is visible.
- [ ] At least six diagnostic tools exist, with four or more working end-to-end.
- [ ] Structured report renders successfully.
- [ ] One invalid/malformed input is handled without a crash.
- [ ] Two corrupted sample datasets have been tested.
- [ ] Screenshot/output evidence has been captured.
- [ ] Brief Phase 2 progress note is completed.
- [ ] GitHub link is ready to submit.

---

## 15. Phase 3 Forward Compatibility

Phase 2 code should make the remaining Phase 3 work straightforward:
- finish all diagnostic tools,
- complete unit/integration tests,
- prepare 5+ test scenarios,
- document one failed/unexpected tool call and handling,
- add sample inputs/outputs,
- finalize README,
- use the architecture diagram,
- record the 5–7 minute demo,
- write the 3–4 page technical report,
- add individual contribution statements.

---

## 16. Out of Scope for Phase 2

- automated dataset repair,
- model training,
- feature engineering pipeline generation,
- long-term user accounts or database persistence,
- cloud deployment,
- multi-user concurrency,
- very large datasets,
- arbitrary code execution,
- model fine-tuning,
- production security hardening.

---

## 17. Definition of Done

A reviewer can clone the repository, follow the README, run the Streamlit app, upload a corrupted CSV, ask a question, visibly observe the agent selecting and calling diagnostic tools, and see a structured diagnosis whose evidence matches deterministic calculations.
