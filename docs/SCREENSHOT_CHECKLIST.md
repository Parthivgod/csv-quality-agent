# Phase 2 Screenshot Checklist

## Already captured — no need to repeat

These four files are genuine screenshots of the running Streamlit app and one live Groq agent run with `corrupted_outliers_corr.csv`:

| File | Visible evidence |
| --- | --- |
| [01_upload_profile.png](screenshots/01_upload_profile.png) | Uploaded CSV, 30 rows × 3 columns, data types, preview, and Groq configuration. |
| [02_tool_trace.png](screenshots/02_tool_trace.png) | `outlier_check` and `correlation_check` selected by the agent; correlation tool output. |
| [03_structured_report.png](screenshots/03_structured_report.png) | Outlier findings with severity, evidence, impact, recommendations, and source tool. |
| [03b_correlation_finding.png](screenshots/03b_correlation_finding.png) | Correlation finding and tools-used list. |

## Screenshots still to capture

The official Phase 2 brief asks for screenshot/output evidence from a partially working system; the four files above meet that baseline. The following two captures make the submission stronger and give the reviewer a visible second corrupted dataset and an input-error example. They have **not** been captured yet.

### 04_error_handling.png — invalid CSV

1. Open the local app at `http://localhost:8503/`. If it is not running, start it from the repository root with `.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8503`.
2. In the left sidebar, click **Reset dataset and report**.
3. At **Upload CSV**, choose [data/samples/invalid_header_only.csv](../data/samples/invalid_header_only.csv). This file has only the header `age,income` and no data row.
4. Confirm the app displays **The CSV has no data rows.** and **No valid CSV loaded** without crashing. No question or target selection is needed.
5. Capture the full app window with the uploaded filename and validation message visible. Save the PNG as `docs/screenshots/04_error_handling.png`.

### 05_selective_target.png — second corrupted dataset

1. Click **Reset dataset and report** again.
2. At **Upload CSV**, choose [data/samples/corrupted_class_imbalance.csv](../data/samples/corrupted_class_imbalance.csv). The dataset has 100 rows and a `label` column.
3. At **Target column (optional)**, choose **label**.
4. In **Data-quality question**, replace the example text with exactly: `Is my target distribution a problem?`
5. Click **Run Triage** and wait for **Tool-call trace** and **Structured diagnosis**. In the documented service run, the agent selected `class_imbalance_check` and found 90 `negative` vs 10 `positive` rows (9.0:1). Inspect the actual UI result before captioning it; LLM choices may vary.
6. Scroll so the sidebar's selected `label` and the **Tool-call trace** heading with its tool status are visible together. Save the PNG as `docs/screenshots/05_selective_target.png`.
7. If the trace and the finding do not fit in one view, capture the **Structured diagnosis** separately as `docs/screenshots/06_class_report.png`, showing the counts/ratio, evidence, and recommendation. This sixth image is optional.

## After capture

- Add links and captions for each newly created screenshot to [PHASE2_PROGRESS.md](PHASE2_PROGRESS.md) and [PHASE2_SUBMISSION_TEMPLATE.md](PHASE2_SUBMISSION_TEMPLATE.md). Mark a screenshot captured only after the file exists and its contents have been checked.
- Keep the screenshots as actual app output. The five runs in [LIVE_GROQ_VALIDATION.md](LIVE_GROQ_VALIDATION.md) were service-level API tests, except for the later numeric UI run; do not label service-only results as UI screenshots.
- The public GitHub URL is recorded in [PHASE2_SUBMISSION_TEMPLATE.md](PHASE2_SUBMISSION_TEMPLATE.md); team-roster confirmation remains.
