# Phase 2 Submission — Progress Update
## CSV Data Quality Triage Agent

**Team listed in the Phase 1 proposal:** Parthiv Godrihal (I024), Nilay Jain (I029)

**Activity:** Tool-Augmented / Agentic LLM Application

**Prepared:** 23 September 2026

## 1. GitHub / Colab Link

**Repository:** [github.com/Parthivgod/csv-quality-agent](https://github.com/Parthivgod/csv-quality-agent). The official brief specifies three members while the Phase 1 proposal lists two, so the roster still needs instructor confirmation.

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

## 8. Exactly What Remains

### Required before sharing this Phase 2 submission

1. **Team roster:** The official brief specifies three members, while the submitted Phase 1 proposal names Parthiv and Nilay. Confirm the accepted roster with the instructor. If a third member is required, update the team lines in this file, [PHASE2_PROGRESS.md](PHASE2_PROGRESS.md), and the responsibility note in [IMPLEMENTATION_NOTES.md](IMPLEMENTATION_NOTES.md).

The public repository URL is now recorded in Section 1. The committed code, README, and screenshot evidence are published there.

### Additional screenshots to strengthen the evidence

The existing four screenshots in Section 5 already show the uploaded dataset, live tool trace, and structured report. [SCREENSHOT_CHECKLIST.md](SCREENSHOT_CHECKLIST.md) gives exact click-by-click instructions for these **uncaptured** additions:

| Save as | Upload file | UI label / choice | Exact question | Capture |
| --- | --- | --- | --- | --- |
| `docs/screenshots/04_error_handling.png` | `data/samples/invalid_header_only.csv` | **Upload CSV** after **Reset dataset and report** | None | **The CSV has no data rows.** and **No valid CSV loaded**. |
| `docs/screenshots/05_selective_target.png` | `data/samples/corrupted_class_imbalance.csv` | **Target column (optional)** → **label** | `Is my target distribution a problem?` | Selected target plus the actual **Tool-call trace** after **Run Triage**. |
| `docs/screenshots/06_class_report.png` (optional) | Same class-imbalance run | Keep **label** selected | Same question | **Structured diagnosis** with the class counts/ratio and recommendation. |

After capturing, verify each image and add its link to Section 5 and the **Screenshots** section of `PHASE2_PROGRESS.md`. The files above are planned paths; they are not present yet.

### Phase 3 work, separate from the Phase 2 hand-in

Evaluate a failed or unexpected tool call, incorporate instructor feedback, prepare the 5–7 minute demo and 3–4 page technical report, and finalize contribution statements.
