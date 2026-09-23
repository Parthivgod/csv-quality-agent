# Phase 2 Submission — Progress Update
## CSV Data Quality Triage Agent

**Team listed in the Phase 1 proposal:** Parthiv Godrihal (I024), Nilay Jain (I029)

**Activity:** Tool-Augmented / Agentic LLM Application

**Prepared:** 23 September 2026

## 1. GitHub / Colab Link

**Repository:** Pending. This local Git repository has no remote configured; add the public URL after the team publishes it. The official brief specifies three members while the Phase 1 proposal lists two, so the roster also needs instructor confirmation.

## 2. Current Progress

- The Streamlit app accepts and validates CSV uploads, shows a dataset profile and preview, and accepts a natural-language data-quality question with an optional target column.
- Eight deterministic diagnostics are registered as LangChain tools. The Groq-hosted `openai/gpt-oss-120b` agent chooses tools, and an LCEL report chain produces a Pydantic-validated report grounded in tool findings.
- The app displays the tool-call trace, issue severity, evidence, potential impact, recommendations, and limitations.
- Deliberately corrupted CSV fixtures and expected results are included. The automated suite passed **22 tests** on 23 September 2026. The Streamlit health endpoint returned HTTP 200.
- Five live Groq API scenarios were exercised; the observed results and limitations are recorded in [LIVE_GROQ_VALIDATION.md](LIVE_GROQ_VALIDATION.md).

## 3. Current Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) and [the architecture diagram](assets/csv_agent_architecture.png).

`CSV upload → loader and in-memory DataFrame → compact context → LangChain agent → selected Python diagnostics → tool trace → LCEL report chain → PydanticOutputParser → Streamlit report`

The DataFrame stays local. The model receives schema context and aggregate diagnostic outputs.

## 4. Working UI Demonstration

**Dataset:** `data/samples/corrupted_outliers_corr.csv` (30 rows, 3 numeric columns)

**Question:** “Do the numerical features contain suspicious values or relationships?”

**Target:** None selected

**Live Groq tool trace:** `outlier_check` → `correlation_check`, both `ok`.

The structured report identified one IQR outlier in each of `feature_x` and `feature_y` (1/30, 3.33% per column) and a strong correlation between the two (Pearson r = 1.0). It recommends inspecting the outliers and feature provenance before changing the data. The screenshots below were captured from this actual Streamlit run through Computer Use.

## 5. Screenshot Evidence

| File | What it shows |
| --- | --- |
| [01_upload_profile.png](screenshots/01_upload_profile.png) | Uploaded CSV, 30 × 3 profile, preview, selected model, and configured-key status. |
| [02_tool_trace.png](screenshots/02_tool_trace.png) | The two selected tool calls and correlation tool evidence. |
| [03_structured_report.png](screenshots/03_structured_report.png) | Report summary and outlier issue cards with evidence and recommended action. |
| [03b_correlation_finding.png](screenshots/03b_correlation_finding.png) | Correlation finding, source tool, recommendation, and tools-used list. |

These are live UI screenshots. The other live API scenarios in `LIVE_GROQ_VALIDATION.md` were run through the service, so they are documented as results rather than presented as UI screenshots.

## 6. Problem Encountered and Solution

The first broad live Groq run treated continuous numeric `age` and `income` as high-cardinality features. The diagnostic now considers categorical fields and numeric fields with identifier-like names. A regression test was added, and the live scenario was rerun without those false positives. A no-target imbalance question also received a clearer target-selection limitation after a live rerun.

## 7. Current Limitations

- CSV parsing is intended for small and medium educational datasets and supports UTF-8 and Windows-1252.
- The target must be selected for class-imbalance assessment. The app does not automatically clean data or confirm data leakage from correlation alone.
- Groq API access is required for live agent orchestration. Model tool choices and wording may vary between runs.

## 8. Remaining Submission Items

- Publish the repository and insert its URL above.
- Confirm the team roster with the instructor.
- Capture a browser validation-error example and a target-specific UI example if required for the final evidence set.
- For Phase 3, evaluate a failed or unexpected tool call, incorporate instructor feedback, prepare the demo video and technical report, and finalize contribution statements.
