# CSV Data Quality Triage Agent

A local Streamlit application for investigating CSV quality before model training. Ask a question, select an optional target, and a LangChain agent chooses relevant diagnostic tools. Local Python/DuckDB code computes the evidence; an LCEL reporting chain produces a structured report whose findings are validated against those observations.

**Phase 3:** disk-backed analysis for CSVs up to **250 MB (250 MiB / 262,144,000 bytes)** on the measured local setup. Groq-hosted `openai/gpt-oss-120b` is the default model. See [measured results and limits](docs/PHASE3_RESULTS.md).

## Features

- Strict CSV validation, full-column type inference, bounded preview, and cached basic metadata.
- Pandas for files up to 20 MB; DuckDB with local Parquet for larger files. Forced Pandas imports above the small-file threshold are rejected.
- Eight deterministic diagnostics, selected by the agent under execution and output budgets.
- Brief LLM explanations of tool choices, shown during execution and alongside the ordered tool trace.
- Tool trace with status, arguments, backend, exactness, timing, cache use, and coverage.
- LLM-written summary, source-linked interpretation, and suggested next steps, including when no issue threshold is triggered.
- Separate verified findings with severity, impact, recommendations, and explicit failed/skipped-check limitations.
- Background import/triage, cancellation, owned temporary storage cleanup, and stale-report invalidation.
- Downloadable JSON containing the question, dataset fingerprint, trace, report, and local tool results.

The app diagnoses candidates for review. It does not clean datasets, train models, or establish leakage from correlation alone.

## Quick start

Use Python 3.11 or newer. From the repository root in **PowerShell**:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Put your Groq API key in the **root `.env`**:

```env
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=<your-Groq-key>
MAX_UPLOAD_MB=250
```

Obtain a key from the [Groq console](https://console.groq.com/keys), then start:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8503
```

Open [the local app](http://localhost:8503/). Restart Streamlit after changing `.env`. Credentials are Git-ignored; never put a real key in `.env.example` or a commit. Preview works without a provider key.

On macOS/Linux, use `python3 -m venv .venv`, `.venv/bin/python -m pip install -r requirements.txt`, and `.venv/bin/python -m streamlit run app.py`.

## Try it

Upload a file, or open **Try a sample**, select a fixture, and click **Load sample CSV**. Choose the target when needed, enter the question, and click **Run Triage**.

| File under `data/samples/` | Target | Question | Expected focus |
| --- | --- | --- | --- |
| `corrupted_missing_duplicates.csv` | None | `Does this CSV contain missing data?` | Missing age/income values |
| `corrupted_missing_duplicates.csv` | None | `Why could this dataset cause problems during model training?` | Missing values, duplicates, constant feature |
| `class_distribution_moderate.csv` | `label` | `Is my target distribution a problem? Explain what the observed distribution means and suggest next steps.` | 60/40 distribution, ratio 1.5, explanatory report with no flagged issue |
| `corrupted_class_imbalance.csv` | `label` | `Is my target distribution a problem?` | 90/10 target distribution, ratio 9 |
| `corrupted_outliers_corr.csv` | None | `Do the numerical features contain suspicious values or relationships?` | Two IQR outlier findings and correlation 1 |
| `invalid_header_only.csv` | None | Upload only | Friendly no-data-rows error |

Tool choices can vary between live model runs. The computed statistics are deterministic. Expand **Tool-call trace** to inspect observations, then read **Structured diagnosis** and download the original evidence.

## Architecture

![Phase 3 architecture](docs/assets/phase3_architecture.png)

`Upload -> chunked local copy and fingerprint -> shared strict CSV/type contract -> Pandas or DuckDB/Parquet handle -> compact schema/question -> agent-selected diagnostics -> bounded trace observations -> LCEL report chain -> Pydantic/evidence validation -> UI and JSON export`

| LangChain component | Source |
| --- | --- |
| `ChatPromptTemplate` | `src/agent/prompt.py` |
| `create_agent` and provider model factory | `src/agent/factory.py` |
| `StructuredTool` wrappers | `src/agent/tools.py` |
| LCEL chain and `PydanticOutputParser` | `src/agent/report_chain.py` |

The eight checks are profile, missing values, full-row duplicates, constant/near-constant columns, eligible high-cardinality columns, IQR outliers, selected-target class imbalance, and Pearson correlation. The agent has six executed checks and twelve attempted events per run by default. Report issues must exactly match tool findings. The LLM writes the summary, interpretation, and proposed next steps; code independently derives the scope caption and failed/skipped/partial-check limitations. Interpretations cite actual tool calls. Validation rejects numeric values absent from supplied observations, with one bounded repair attempt. These checks do not prove every natural-language inference: review the model interpretation against its cited evidence. The report before this update remains in the submission archive.

The dataset stays in local app storage. Groq receives the question, schema, target, and aggregate observations, including category labels when relevant. These can still contain sensitive information. Raw row samples are not included in the model context.

## Large-file support and limits

- The widget and loader cap files at 250 MiB. Streamlit transport allows 251 MiB to accommodate multipart framing near the exact file limit. The app requires Streamlit 1.53 or later for its [per-widget file limit](https://docs.streamlit.io/1.53.0/develop/api-reference/widgets/st.file_uploader). The measured release envelope covers the generated profiles in [Phase 3 results](docs/PHASE3_RESULTS.md); this is not a promise for every CSV shape or multiple simultaneous users.
- Streamlit retains an upload buffer. Disk-backed diagnostics avoid full DataFrame expansion for large files, but upload memory is still measured separately from the command-line harness.
- Strict validation scans the file before choosing types. The initial 60-second ingestion goal was missed by some 250 MiB cases; the revised release gate is 120 seconds. Original failed attempts remain in the evidence.
- UTF-8/BOM and Windows-1252 are supported. Short/long malformed records, empty headers, case-insensitive header collisions, and excessively long/wide schemas are rejected explicitly.
- Leading-zero numeric identifiers and mixed numeric/text columns stay text. Null tokens and type inference are shared across both backends; the legacy `load_csv()` API remains available for existing callers.
- Overview/schema context is capped at 50 columns with the chosen target retained. Inputs have a hard 1,000-column and 256-byte header limit.
- Numeric checks default to at most 20 eligible columns. Select a subset under **Numerical check coverage** for a wide dataset; omitted eligible columns are disclosed.
- Exact duplicate grouping is skipped above 50 columns. Exact IQR quantiles have a memory admission guard; a skipped check never implies clean data.
- DuckDB uses a 1 GB memory setting, two threads, and up to 2 GiB spill; session temporary storage is capped at 4 GiB. A single app job runs at a time. These settings are not a process-wide memory guarantee.
- Class imbalance needs a suitable selected target. Excessively many classes or long class labels produce a visible skip.

## Validation and reproducibility

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q app.py src scripts tests
```

The current suite passes **149 tests** covering both backends, exact diagnostic parity, adversarial CSVs, resource/cancellation guards, full LangChain integration, output/report validation, and actual Streamlit sample/reset/replacement flows. Scripted models test wiring without API calls. [Fresh synthesis checks](docs/evaluation/phase3/llm_synthesis/README.md), [original Phase 3 live scenarios](docs/evaluation/phase3/scenarios/scenario_results.md), [UI validation](docs/evaluation/phase3/ui/UI_VALIDATION.md), and size benchmarks are recorded separately; successes, failures, and retries are retained.

Generate and benchmark synthetic data (large files are ignored by Git):

```powershell
.\.venv\Scripts\python.exe scripts/generate_benchmarks.py --sizes 1 20 50 100 250 --profiles tall_numeric
.\.venv\Scripts\python.exe scripts/benchmark_phase3.py --fixtures data/benchmarks/tall_numeric_250MiB.csv --runs 3
.\.venv\Scripts\python.exe scripts/evaluate_phase3.py
.\.venv\Scripts\python.exe scripts/evaluate_phase3.py --live
```

The last command uses the configured API and may encounter account rate limits. Live failure injection is scoped to its harness run; it is not a production feature switch. To inspect the separate failure demo UI:

```powershell
.\.venv\Scripts\python.exe -m streamlit run scripts/phase3_failure_demo.py --server.port 8504
```

## Phase 3 submission

- [Measured implementation results](docs/PHASE3_RESULTS.md) and [work log](docs/PHASE3_WORK_LOG.md)
- [Architecture](docs/ARCHITECTURE.md) with editable diagram source
- [Implementation plan and requirement mapping](docs/PHASE3_IMPLEMENTATION_PLAN.md)
- [6:30 recording script: exact files, prompts, actions and narration](docs/PHASE3_DEMO_SCRIPT.md)
- [Evaluation, screenshot steps and remaining submission tasks](docs/PHASE3_EVALUATION_AND_SUBMISSION.md)
- [Technical report](submission/Phase3_Technical_Report.pdf) and editable source in `submission/`
- [Contribution statement drafts for author review](submission/Contribution_Statements.md)

The video will be recorded by the students using the script/screenshots. Instructor feedback, roster/deadline confirmation, and the course feedback form require real course information. Historical [Phase 2 evidence](docs/PHASE2_PROGRESS.md) and source assignment documents are preserved.

## Troubleshooting

- **Run Triage disabled:** set `GROQ_API_KEY` in the root `.env` and restart.
- **Groq rate limit/provider error:** inspect the error/trace, wait for the account limit to reset, then retry. A failed run is not a completed diagnosis.
- **Large import rejected:** check size, strict CSV rules, free temp disk, and the displayed reason. Use Auto or DuckDB above the Pandas threshold.
- **Check skipped:** inspect target, numeric subset, width, class labels, or resource limits. The report states what was not assessed.
- **Cancel pending:** wait for the owned query/API request to finish stopping before reset. Provider requests have bounded timeouts; cancellation does not instantly revoke an already sent request.
- **Upload cap changed:** update `MAX_UPLOAD_MB` and `.streamlit/config.toml` together, then restart; increasing the cap alone does not validate a larger workload.
