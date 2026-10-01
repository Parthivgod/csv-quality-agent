# Phase 3 evaluation and submission checklist

**Status: implementation and evaluation completed; student recording and course hand-in actions remain.** Results below distinguish live Groq, scripted integration, actual browser use and CLI benchmarks. Original failed attempts are retained. The browser/capture record is [UI_VALIDATION.md](evaluation/phase3/ui/UI_VALIDATION.md); it controls claims about screenshots and upload-buffer measurements.

See [implementation/completion record](PHASE3_IMPLEMENTATION_PLAN.md), [6:30 recording script](PHASE3_DEMO_SCRIPT.md), and the original [Lab 9 brief](source/Lab%209_2026_27.docx), Activity 2 and Phase 3 Submission.

## 1. Completed scenario matrix

Each T01–T09 has a successful saved live attempt. This does not mean every original attempt passed: earlier triage errors remain, and one captured a real Groq 429 token-rate limit before an isolated successful retry. Actual tool selection is recorded; tests requiring a tool are incomplete if it is never called.

| ID | Input / target | Exact prompt or action | Required observed evidence |
| --- | --- | --- | --- |
| T01 Missing | `corrupted_missing_duplicates.csv`; None selected | `Does this CSV contain missing data?` | Missing tool; age 6/30 (20%), income 3/30 (10%) |
| T02 Broad | Same file; None selected | `Why could this dataset cause problems during model training?` | Missing, duplicate and constant checks; duplicate count 2, constant_feature constant; profile is optional |
| T03 Target | `corrupted_class_imbalance.csv`; label | `Is my target distribution a problem?` | Negative 90, positive 10, majority/minority ratio 9; supported report |
| T04 Numeric | `corrupted_outliers_corr.csv`; None selected | `Do the numerical features contain suspicious values or relationships?` | One outlier in each feature_x/feature_y; Pearson r = 1; contextual recommendations |
| T05 Unsuitable target | `corrupted_class_imbalance.csv`; record_id | `Check class imbalance in my selected target using the class imbalance tool.` | Skipped unsuitable 100-class target; visible reason and limitation, no invented issue |
| T06 Controlled failure | `corrupted_missing_duplicates.csv`; None selected | `Check this dataset for duplicate rows using the duplicate rows tool.` | Full agent → injected duplicate exception → error trace → report limitation; no fabricated duplicate finding |
| T07 Missing target | `corrupted_class_imbalance.csv`; None selected | `Is my target distribution a problem?` | Missing-target limitation; no invented distribution |
| T08 Clean | `clean_small.csv`; None selected | `Does this CSV contain missing data?` | Zero affected columns in 12 rows; no missing-value issue |
| T09 Invalid input | `invalid_header_only.csv` | Upload only | Rejected before agent execution; stale result cleared and no valid CSV loaded |

Evidence: [scenario results](evaluation/phase3/scenarios/scenario_results.md) plus original per-attempt `_trace.json`, `_report.json`, and `_result.json` files. T06 injection is explicitly labeled; T05 is a skipped/unexpected response, not an exception. A separate T06 verification audit corrects the old harness's use of the last repeated skip rather than the earlier observed error; original records remain unchanged.

Automated validation: [122-test final run, compilation and dependency check](evaluation/phase3/test_results.txt). Tests use local scripted chat models to exercise the real LangChain graph, including failed-tool handling and recovery, without claiming live model quality.

## 2. Reproduce evaluation

From the repository root in PowerShell:

```powershell
# Repeatable graph/evaluation, no API calls
.\.venv\Scripts\python.exe scripts/evaluate_phase3.py --output-dir docs/evaluation/phase3/scenarios

# Real configured Groq model, preserves each original attempt
.\.venv\Scripts\python.exe scripts/evaluate_phase3.py --live --output-dir docs/evaluation/phase3/scenarios

# Isolated unsuitable-target retry if provider quota interrupted a batch
.\.venv\Scripts\python.exe scripts/evaluate_phase3.py --live --scenarios T05 --output-dir docs/evaluation/phase3/scenarios
```

The live harness requires Groq `openai/gpt-oss-120b` and `GROQ_API_KEY` in ignored root `.env`. It records sanitized error context and actual latency; it does not print credentials. Rapid consecutive model calls can hit the provider token quota. Wait for the allowed retry interval, avoid competing API requests and retain both attempts.

### Controlled failure procedure

1. Run T06 with the harness above; `--scenarios T06` selects only that case.
2. The harness temporarily replaces only the dataset duplicate diagnostic with a callable raising `RuntimeError`. The real wrapper, trace, agent, LCEL chain and parser still run.
3. Confirm at least one duplicate event is `error`, even if a later repeated call is `skipped`.
4. Confirm the report has a failed-check limitation and no issue from the failed tool.
5. Confirm the scoped patch is removed; integration tests run a healthy investigation afterward.
6. Caption the evidence **“Controlled duplicate-tool failure injection — live Groq”** or **“— scripted integration”**, matching actual mode. It is not a spontaneous production failure. There is no hidden production failure flag.

## 3. Measured size evidence and reproduction

The target is 250 MiB (262,144,000 bytes); generated files finish below that limit at a complete CSV record. Tall numeric fixtures cover 1/20/50/100/250 MiB. High-unique strings, null-heavy, quoted Unicode/multiline and wide numeric profiles additionally cover 250 MiB.

```powershell
.\.venv\Scripts\python.exe scripts/generate_benchmarks.py --sizes 1 20 50 100 250 --profiles tall_numeric
.\.venv\Scripts\python.exe scripts/generate_benchmarks.py --sizes 250 --profiles high_unique_strings null_heavy quoted_unicode wide_numeric
.\.venv\Scripts\python.exe scripts/benchmark_phase3.py --fixtures data/benchmarks/tall_numeric_250MiB.csv --runs 3
```

The generator is deterministic and chunked; manifests contain exact bytes, SHA-256, rows, columns, null/duplicate/class counts derived from construction. Generated datasets under `data/benchmarks/` are ignored by Git. Keep them for reproduction; do not add them to the submission repository.

Benchmark scope and results:

- 38 timed imports, 32 successful, six preserved initial 60-second validation timeouts; 112 diagnostic rows.
- Required revised-release imports passed 3/3 for each 250 MiB profile, within **120 seconds** and **2 GiB sampled harness RSS**. The original 60-second goal was missed and is retained separately.
- Narrow four profiles have exact null/duplicate/class invariants. Wide 202-column input has exact null/classes; duplicate grouping is explicitly guarded above 50 columns and its exact count is **unassessed**.
- All eight checks additionally executed successfully on 250 MiB tall and high-unique inputs. Unknown large statistical ground truth is not a pass; small controlled backend-parity tests provide independent statistical correctness evidence.
- RSS includes harness process plus recursive children, not browser/Streamlit uploader memory. Temporary files were sampled every 50 ms in an isolated owned directory. API latency is excluded; OS filesystem cache and desktop load were uncontrolled.
- Separate actual Streamlit upload passed: 36.093-second local import, 3,274,752 rows and 1,312.97 MiB sampled server RSS **including its uploader buffer, excluding browser memory**. The live missing-value report took about 3.938 seconds; `nullable` had 327,476 missing values (10%). See the original UI JSON and sampler record.

Use these actual artifacts:

| Artifact | Purpose |
| --- | --- |
| [benchmark_manifest.json](evaluation/phase3/benchmarks/benchmark_manifest.json) | Nine fixture manifests, 38 actual attempts and environment snapshots |
| [benchmark_results.csv](evaluation/phase3/benchmarks/benchmark_results.csv) | Original rows, including failures and old verifier judgments |
| [benchmark_results_verified.csv](evaluation/phase3/benchmarks/benchmark_results_verified.csv) | Separate derived check results; expected wide guard is not an exact count pass |
| [benchmark_verification_audit.json](evaluation/phase3/benchmarks/benchmark_verification_audit.json) | Original CSV hash, guard correction and raw evidence references |
| [benchmark_verified_summary.md](evaluation/phase3/benchmarks/benchmark_verified_summary.md) | Measured summary separating actual failures and expected guards |
| [Browser evidence](evaluation/phase3/ui/UI_VALIDATION.md) | Actual app interactions and separately measured upload-buffer case |

## 4. Screenshots — exact files, labels, prompts and actions

Save computer-use captures under `docs/screenshots/phase3/`. Filenames below use **.jpg**; `_full` images supplement the readable cropped view. Check the capture log and current folder before marking a shot complete. Keep Phase 2 PNG captures as historical evidence.

The main numeric/target images were refreshed using the final 250 MiB release banner and auto/Pandas small-file path. The `_full` supplements retain an earlier implementation-stage 20 MB banner; their fixture findings are valid, but those banners are not evidence of the final upload limit. The large-data profile capture shows the actual final release path.

### S01 — `01_numeric_upload.jpg`

**Caption:** “Numeric CSV loaded: 30 rows, 3 columns and bounded preview.”

1. Choose **Backend for next import → auto** (or explicitly explain DuckDB if selected).
2. Use **Upload CSV** to choose `data/samples/corrupted_outliers_corr.csv`.
3. Select **None selected** in **Target column (optional)**.
4. Wait for **Dataset overview**, expand **Preview (first 10 rows)**, show actual backend/shape and capture before running.

### S02 — `02_numeric_trace.jpg`

**Caption:** “Live Groq numeric run: observed outlier and correlation calls with local evidence.”

1. On S01's file, paste `Do the numerical features contain suspicious values or relationships?` into **Data-quality question**.
2. Click **Run Triage**, wait for completion, scroll to **Tool-call trace**.
3. Expand the outlier/correlation entries that actually ran; show names, status and data. Do not caption an unobserved check.

### S03 — `03_numeric_report.jpg` and `03_numeric_report_full.jpg`

**Caption:** “Supported numeric findings: one IQR outlier per feature_x/feature_y and Pearson correlation one; recommendations require context.”

1. Keep the completed S02 run; scroll to **Structured diagnosis**.
2. Capture readable outlier/correlation evidence and source tools. Use `_full` for an additional view rather than shrinking text.
3. Click **Download run evidence (JSON)**; retain the original file with the UI record.

### S04 — `04_target_imbalance.jpg` and `04_target_imbalance_full.jpg`

**Caption:** “Selected label target: 90 negative and 10 positive examples, ratio 9:1.”

1. Upload `data/samples/corrupted_class_imbalance.csv`.
2. Select **label** in **Target column (optional)**.
3. Ask `Is my target distribution a problem?`; click **Run Triage**.
4. Show selected target, class-imbalance trace and report. Capture `_full` if needed for legible evidence.

### S05 — `05_unsuitable_target.jpg`

**Caption:** “An unsuitable record_id target returns an explicit skipped check and report limitation.”

1. On the same input, select **record_id**.
2. Ask `Check class imbalance in my selected target using the class imbalance tool.`
3. Run; show the actual skipped class tool and limitation. If no tool runs or provider quota interrupts reporting, retain that attempt and retry separately; the expected screenshot must show actual skipped-tool evidence.

### S06 — `06_invalid_upload.jpg`

**Caption:** “Header-only CSV rejected and the previous report cleared.”

1. Start after a completed valid run, then upload `data/samples/invalid_header_only.csv`.
2. Show **The CSV has no data rows.** and **No valid CSV loaded**.
3. Confirm old trace/report disappeared and capture the error state. Do not submit a model question for this case.

### S07 — `07_controlled_tool_failure.jpg` and `07_controlled_tool_failure_report.jpg`

**Caption:** “Controlled duplicate-tool failure injection — live Groq; failed check disclosed without an invented issue.”

1. Execute `scripts/evaluate_phase3.py --live --scenarios T06` using the procedure above.
2. Open the saved harness trace/report display used for the capture; show the mode, original error event and report limitation.
3. Preserve the original attempt identifier. It is harness evidence, not a hidden failure mode in the normal app.

### S08 — `08_large_dataset_profile.jpg`

**Caption:** “250 MiB acceptance fixture: actual bytes, row count, DuckDB backend and bounded preview.”

1. Generate `data/benchmarks/tall_numeric_250MiB.csv` and its manifest.
2. Set **Backend for next import → auto**, then upload that file through **Upload CSV**.
3. Wait for import completion; show filename, 3,274,752 rows, 262,143,987 bytes, backend **duckdb**, import wall time and preview.
4. Label upload transfer and import wall time correctly; they are different measurements. For the demo video, preload before recording and say so.

### S09 — `09_large_dataset_result.jpg`

**Caption:** “Large missing-value check: exact nullable count matches generation ground truth.”

1. On S08's dataset, select **None selected**.
2. Ask `Does this CSV contain missing data?`; click **Run Triage**.
3. Show the actual missing tool and report: `nullable` has 327,476 missing values out of 3,274,752 rows. Show execution metadata, scope and local time.
4. Retain downloaded JSON and the benchmark manifest. A screenshot alone does not establish the RSS gate or all large statistics.

### S10 — `10_benchmark_results.jpg`

**Caption:** “Measured size/profile results with revised 120-second import gate, retained failures and explicit wide guard.”

1. Open the verified benchmark table/summary in the browser display used for the submission.
2. Show size/profile, measured maxima, original 60-second misses and the revised gate.
3. Capture legibly through computer use; retain the CSV/audit. Do not describe an expected wide skip as a full duplicate-count pass.

## 5. Technical report and package

Lab 9 asks for **3–4 pages**. The final PDF must be rendered and its page count checked. Screenshots need captions directly below them. Contribution statements may be separate unless the instructor specifies otherwise.

| Page | Required content |
| --- | --- |
| 1 | Problem, Activity 2, local tools/Groq API, actual architecture and LangChain component mapping |
| 2 | Shipped ingestion/backend/trace/report controls, CSV semantics, target and coverage limits |
| 3 | At least five actual scenarios, observed results, failed or unexpected tool handling, selected readable screenshots |
| 4 | Measured size results, changed import allowance, memory boundaries, limitations, improvements and references |

| Submission item | Location / action |
| --- | --- |
| Working code, README, architecture, fixtures | Repository and final evaluated commit; confirm instructor access |
| Sample outputs, tests, live and benchmark evidence | `docs/evaluation/phase3/` |
| Fresh computer-use images | `docs/screenshots/phase3/` with captions above |
| Technical report | `submission/Phase3_Technical_Report.pdf`; verify 3–4 pages |
| Demo recording | Student creates `submission/Phase3_CSV_Data_Quality_Demo.mp4` or course-accessible link using the ready script |
| Individual contributions | Complete [Contribution_Statements.md](../submission/Contribution_Statements.md) truthfully, confirm names/work/AI assistance, export per course requirements |
| Course feedback form | Obtain actual instructor link/template and submit |

## 6. Clear remaining actions for the students

1. **Record the video:** use the ready 6:30 script; two live cases; readable trace/report; explain one challenge and limitations; check audio, duration and access.
2. **Confirm contributions:** fill actual personally completed/reviewed tasks and evidence; do not submit the templates as certified statements.
3. **Resolve course instructions:** the brief's 30 September deadline is past, group-size wording is inconsistent, and actual feedback/form link must come from the instructor.
4. **Check the final package:** report page count, current screenshot/capture log, final commit and instructor access; submit the real feedback form.

Implementation, generators, CLI measurements, live scenario evidence and reproducible tests are completed. The browser log records which final screenshots and actual upload measurements have been saved; this checklist does not turn an uncaptured screenshot or unrecorded video into evidence.

## LLM synthesis revision - 1 October 2026

The current report preserves an LLM-written summary, source-linked interpretation and suggested next steps. Brief tool-choice explanations appear in progress and beside trace entries. Verified findings and deterministic scope/limitations remain separate. **149 tests passed in 10.31s**; fresh Groq runs and captures 11-13 are documented in [synthesis validation](evaluation/phase3/llm_synthesis/README.md). The 122-test run, original screenshots, live attempts and size measurements above describe the prior release and remain preserved. The current 6:30 demo script demonstrates a no-finding 60/40 target distribution with a useful explanation. No benchmark rerun is claimed.
