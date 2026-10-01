# Phase 3 demo script — 6 minutes 30 seconds

**Status: ready for student recording.** Implementation, saved live Groq cases, and size benchmarks exist. The **video itself has not been recorded by this script**. Use the actual app for two live cases; screenshots and saved traces are supplementary evidence. Course duration is 5–7 minutes; this script totals **390 seconds**.

## 1. Prepare and rehearse

1. Read [UI validation](evaluation/phase3/ui/UI_VALIDATION.md), [current synthesis tests](evaluation/phase3/llm_synthesis/test_results.txt), and [verified benchmark summary](evaluation/phase3/benchmarks/benchmark_verified_summary.md). Use the final evaluated commit when recording.
2. Configure ignored root `.env`: `LLM_PROVIDER=groq`, `LLM_MODEL=openai/gpt-oss-120b`, `GROQ_API_KEY=your_key`. Keep the key and `.env` off screen. The app displays **API key configured** without revealing it.
3. Start from the repository root in PowerShell:

   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8503
   ```

4. Open `http://localhost:8503/`, maximize the browser, and choose **Backend for next import → auto** unless you explicitly explain using DuckDB for a small demonstration. Set readable zoom.
5. Keep [architecture PNG](assets/phase3_architecture.png), evaluation summary, and benchmark table ready in separate tabs. Close credentials and unrelated pages.
6. Rehearse the two live questions below. Avoid many consecutive API runs immediately before recording: a real Groq 429 tokens-per-minute error was observed during rapid evaluation. If it happens, show the error, wait for the provider allowance, and start a new take; the original failed attempt remains evidence.
7. Optional large screen: import the generated `data/benchmarks/tall_numeric_250MiB.csv` **before recording**, and say it was previously imported. Its generated file is 262,143,987 bytes and 3,274,752 rows. Do not imply those import seconds elapsed during a short screen cut.
8. Save the recording as `submission/Phase3_CSV_Data_Quality_Demo.mp4` or use the course's accessible video link. Check 5–7 minute duration, legible text, audio and playback.

### Two exact live cases

| Case | File | Target | Exact `Data-quality question` |
| --- | --- | --- | --- |
| A: numerical investigation | `data/samples/corrupted_outliers_corr.csv` | **None selected** | `Do the numerical features contain suspicious values or relationships?` |
| B: selected target with no flagged issue | `data/samples/class_distribution_moderate.csv` | **label** | `Is my target distribution a problem? Explain what the observed distribution means and suggest next steps.` |

Use **Upload CSV** to choose the file. For a reliable rehearsal shortcut, open **Try a sample**, choose the same filename in **Sample CSV**, and click **Load sample CSV**; identify that input as the bundled sample. Wait for **Dataset overview** before asking the question. Click **Run Triage**, then inspect **Tool-call trace** and **Structured diagnosis**.

## 2. Timed narration and actions

### 0:00–0:45 — Purpose

**Screen:** app heading, upload control and preview.

**Say:**

> “Our application checks CSV data before model training. A user uploads a CSV and asks a question. The agent chooses relevant tools, which compute local statistics. The result gives severity, evidence, contextual recommendations and limitations. It helps us investigate missing values, repeated records, unusual numerical values and target imbalance. It does not automatically clean the dataset or train a model.”

### 0:45–2:15 — Architecture and LangChain

**Screen:** final architecture diagram, then app backend/trace controls.

**Say:**

> “The upload is copied and validated once. Small files use Pandas; larger files use DuckDB and a local Parquet dataset. The user can select a target and a bounded set of numeric columns. The LLM receives the question, schema and aggregate observations, while raw rows stay local. Schema and aggregates can still be sensitive.
>
> “Four LangChain components work together. A prompt template supplies the rules and context. The Groq-hosted GPT OSS 120B agent chooses from eight structured tools. An LCEL chain asks the model to write a summary, interpretation and suggested next steps from the observations, and a Pydantic parser validates the report. Our own validator requires every issue to match a real tool finding; failed, skipped or limited checks become limitations. Brief tool-choice explanations appear during execution and in the trace. Verified findings, model interpretation and suggested actions have separate labels. The JSON download preserves each layer.
>
> “The release accepts up to 250 MiB on our documented local setup. It uses caching, bounded output, spill settings, cancellation and explicit scope guards. The uploader still keeps a memory buffer, so the disk-backed backend does not eliminate upload memory.”

**Point to:** `src/agent/prompt.py`, `factory.py`, `tools.py`, `report_chain.py` only if discussing source. The [architecture document](ARCHITECTURE.md) has the component mapping.

### 2:15–3:25 — Live case A

**Actions:**

1. Upload `corrupted_outliers_corr.csv`; keep **None selected** as target.
2. Show **30 rows · 3 columns** in **Dataset overview** and expand **Preview (first 10 rows)** briefly.
3. Paste case A's exact question; click **Run Triage**.
4. Wait for completion, then expand the actually observed numeric entries in **Tool-call trace**.
5. Scroll to **Structured diagnosis**.

**Say while running:**

> “This deliberately corrupted sample lets us check known numerical evidence. The question asks about numerical values and relationships. The trace shows which tools the model actually chose.”

**Say if those findings appear:**

> “There is one IQR outlier in feature_x and one in feature_y, each out of thirty rows. Their Pearson correlation is one. That shows a strong relationship; it does not prove leakage. We would inspect feature provenance before changing either column.”

If the agent omits a check, describe the observed coverage. Do not splice a different trace into this run. During rehearsal, retry with an explicit request if necessary.

### 3:25–4:30 — Live case B

**Actions:**

1. Upload `class_distribution_moderate.csv`.
2. Select **label** in **Target column (optional)**.
3. Paste case B's exact question; click **Run Triage**.
4. Show the model's brief tool-choice explanation, then its **LLM summary**, **Verified findings**, **LLM interpretation** and **Suggested next steps**.

**Say:**

> “This question needs a selected target. There are sixty negative and forty positive labels: a ratio of one point five to one. The tool does not flag it because the medium threshold is three to one. The model still explains the modest skew and proposes class-aware evaluation. The summary and interpretation are model-written; the counts and thresholds come from tools. Suggested next steps have not been performed, and the app does not automatically resample data.”

If the two runs finish early, use at most 15 seconds to show an already imported large dataset, saying **“This dataset was imported before recording.”** Otherwise reserve the benchmark screen for the final segment.

### 4:30–5:30 — Actual challenge and handling

**Screen:** saved original timeout records and revised benchmark table, then the labeled failure screenshot if time permits.

**Say:**

> “Scaling needed more than a larger upload limit. We replaced repeated whole-file copying and profiling with a dataset boundary, disk-backed diagnostics, cached metadata and controlled background work.
>
> “The initial sixty-second deadline rejected six large imports. A parsing fast path improved throughput, but sixty seconds remained unreliable. We explicitly revised the release allowance to two minutes and kept the failures. Five 250 MiB profiles passed the required gates; the worst successful import was under ninety-seven seconds.
>
> “We deliberately made the duplicate diagnostic raise an exception in a live Groq run. This controlled injection tests the full failure path. The trace records an error; the report discloses the failed check without inventing a duplicate finding.”

Show [controlled-failure evidence](evaluation/phase3/scenarios/scenario_results.md) or `07_controlled_tool_failure.jpg` with its explicit label. An unsuitable-target **skip** is a different case and should not be described as an exception.

### 5:30–6:30 — Evaluation and limits

**Screen:** scenario table and verified benchmark summary.

**Say:**

> “The original nine evaluation scenarios include input rejection, and 149 automated tests now pass. Fresh reporting runs cover modest imbalance, numerical features and a missing target. Earlier errors remain, including a Groq rate-limit error followed by a successful retry. Scripted, API, browser and benchmark evidence are separate.
>
> “The size ladder reaches 250 MiB across five profiles. Required counts matched the generator. Large statistical tools were exercised; independent numerical correctness comes from controlled small fixtures. Unassessed statistics are not counted as verified.
>
> “Wide checks have explicit guards: duplicates require at most fifty columns, and numeric checks at most twenty. Benchmark memory excludes the upload buffer; browser evidence measures it separately. Future work is streaming uploads and broader benchmarks. The app does not clean data or confirm leakage.”

## 3. Recording acceptance

- Segment lengths: **45 + 90 + 135 + 60 + 60 = 390 seconds**, or 6:30.
- Include **two actual live cases**. A saved screenshot or cached replay does not replace a fresh model run.
- Show tool names/status and report evidence legibly; do not shrink the UI to fit every finding in one frame.
- Preserve date/commit and original JSON downloads. Use **Download run evidence (JSON)** after each completed case.
- If Groq fails, explain the actual error, wait/retry, and record a clean new take. Do not conceal failed attempts in the evaluation records.
- Use the exact final test count if the saved test result changes after this script; there are no invented measurements to fill in.
- Verify duration, audio, playback, instructor access and the absence of keys before submitting.
