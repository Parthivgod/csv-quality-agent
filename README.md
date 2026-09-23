# CSV Data Quality Triage Agent

A Phase 2 LangChain and Streamlit application for investigating quality problems in a CSV before model training. The user asks a question; a LangChain agent chooses relevant diagnostic tools; deterministic Pandas/NumPy functions calculate evidence; a separate LCEL chain creates a validated report.

## Problem and current status

Missing values, repeated rows, constant features, class imbalance, outliers, and related features can affect training. A fixed full scan can be noisy. This app aims to run a small set of checks relevant to the question and show every tool call.

The repository contains a runnable interface, eight diagnostics, sample CSVs with expected problems, an agent workflow, a tool trace, a Pydantic report, and automated tests. Local integration tests use a scripted chat model. A live Groq call requires your Groq API key; no live provider call was possible in the development environment.

## Features

- CSV upload, validation, in-memory session state, schema and preview
- Optional explicit target selection
- Natural-language questions and LangChain `create_agent` tool selection
- Eight allowlisted diagnostics and a per-request six-call default budget
- Observable tool trace: name, arguments, status, summary, and evidence
- Separate LCEL reporting chain with `PydanticOutputParser`, one repair attempt, and evidence validation
- Friendly errors for bad CSVs, missing target, provider errors, and parser failures

## Architecture

![Architecture](docs/assets/csv_agent_architecture.png)

`Streamlit → CSV loader → in-memory DataFrame → compact schema → ChatPromptTemplate + LangChain agent → selected tools → trace → LCEL report chain → PydanticOutputParser → report UI`

The DataFrame stays in the Streamlit process. The model receives column names/types, row count, the question, target name, and aggregate tool observations. The entire CSV and row samples are not sent in model prompts. A tool's deterministic finding must exactly support every issue in the final report.

### LangChain components

| Component | Implementation |
|---|---|
| PromptTemplate | `ChatPromptTemplate` in `src/agent/prompt.py` |
| Agent / Tools | `create_agent` in `src/agent/factory.py`; `StructuredTool` wrappers in `src/agent/tools.py` |
| LCEL | `REPORT_PROMPT | model | StrOutputParser()` in `src/agent/report_chain.py` |
| OutputParser | `PydanticOutputParser` validating `DataQualityReport` |

## Diagnostics

| Tool | Evidence |
|---|---|
| `dataset_profile` | Shape, dtypes, unique and null counts |
| `missing_values_check` | Per-column missing counts, percentages, heuristic severity |
| `duplicate_rows_check` | Exact duplicate count and percentage |
| `constant_columns_check` | Constant and near-constant features |
| `high_cardinality_check` | Unique ratios and possible identifier-like features |
| `outlier_check` | Numeric IQR bounds and outlier counts |
| `class_imbalance_check` | Selected target's class counts, proportions, majority/minority ratio |
| `correlation_check` | Numeric feature pairs with high absolute Pearson correlation |

The default thresholds are project heuristics, not universal quality rules. Duplicates and outliers can be valid; correlation alone does not establish leakage. No data is automatically changed.

## Tech stack and files

Python 3.11+, Streamlit, LangChain 1.x, Pydantic 2.x, Pandas, NumPy, python-dotenv, pytest. Groq's `openai/gpt-oss-120b` is the default chat model. The existing Mistral and OpenAI adapters remain available through the same factory. scikit-learn is not needed for the current deterministic checks.

```text
app.py                 Streamlit entry point
src/config.py          Environment settings and thresholds
src/data/              CSV loader and bounded model context
src/diagnostics/       Eight deterministic tools
src/agent/             Prompts, model factory, tool registry, report chain
src/models/            Pydantic report schema
src/services/          Triage orchestration and observable trace
src/ui/                Trace/report display components
data/samples/          Four generated CSV fixtures
data/expected/         Ground-truth manifests for corrupted fixtures
scripts/               Reproducible fixture and architecture generation
tests/                 Unit and integration tests
docs/                  Source documents, architecture, progress, screenshot checklist
```

## Local setup

From this repository directory in PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit **`.env` in the repository root** and paste your Groq key after `GROQ_API_KEY=`:

```env
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=gsk_your_key_here
```

Get the key from the [Groq console](https://console.groq.com/keys). The filename must be `.env`, not `.env.example`; `.env` is Git-ignored. Restart Streamlit after editing it. The model name starts with `openai/`, but it is served by Groq and uses `GROQ_API_KEY`.

To use an earlier adapter instead, set `LLM_PROVIDER=mistral` with `MISTRAL_API_KEY` and a Mistral model, or `LLM_PROVIDER=openai` with `OPENAI_API_KEY` and an OpenAI model.

```powershell
python -m streamlit run app.py
python -m pytest -q
python -m compileall -q app.py src scripts tests
```

Open the local Streamlit URL printed in the terminal. The upload/profile view works without an API key; running the agent requires one.

### Environment variables

| Variable | Default | Use |
|---|---|---|
| `LLM_PROVIDER` | `groq` | `groq`, `mistral`, or `openai` |
| `LLM_MODEL` | `openai/gpt-oss-120b` | Provider model with tool calling |
| `GROQ_API_KEY` | blank | Groq credential for the default model |
| `MISTRAL_API_KEY` / `OPENAI_API_KEY` | blank | Credentials for optional adapters |
| `MAX_TOOL_CALLS` | `6` | Maximum executed diagnostics per question |
| `MAX_UPLOAD_MB` | `20` | Application upload limit |
| `MISSING_MEDIUM_PCT` / `MISSING_HIGH_PCT` | `5` / `30` | Missing-value severity cutoffs |
| `NEAR_CONSTANT_RATIO` | `0.95` | Dominant-value fraction |
| `HIGH_CARDINALITY_RATIO` | `0.90` | Unique fraction |
| `HIGH_CARDINALITY_MIN_NON_NULL` | `20` | Minimum observations |
| `CORRELATION_THRESHOLD` | `0.95` | Absolute Pearson cutoff |

Streamlit's file-picker cap is also set to 20 MB in `.streamlit/config.toml`. If raising `MAX_UPLOAD_MB`, raise `server.maxUploadSize` there as well and restart Streamlit.

## Demo flow

1. Upload `data/samples/corrupted_missing_duplicates.csv`.
2. Review the 30-row schema and preview.
3. Ask **Why could this dataset cause problems during model training?**
4. Inspect the tools selected and the structured report.
5. Upload `data/samples/corrupted_class_imbalance.csv`, select `label`, and ask **Is my target distribution a problem?**
6. Compare the smaller target-specific trace.

Other useful questions: **Does this dataset contain missing values?**, **Are there duplicate rows?**, **Are any columns likely to be IDs?**, **Are there extreme numeric outliers?**, **Are any numerical features suspiciously correlated?**

An expected deterministic finding from the first fixture is `age: 6/30 values missing (20.0%)`, with two exact duplicate rows and one constant feature. The class fixture has 90 `negative` and 10 `positive` labels. The agent's live choice of tools and wording can vary by model.

## Testing and Phase 2 evidence

`python -m pytest -q` runs local tests without a paid API call. The integration tests execute the actual LangChain agent graph with a scripted chat model, so tool selection, trace collection, parsing, and evidence validation are exercised. They do not establish live Groq model reliability.

See [Phase 2 progress](docs/PHASE2_PROGRESS.md), [live Groq validation](docs/LIVE_GROQ_VALIDATION.md), [implementation notes](docs/IMPLEMENTATION_NOTES.md), and [screenshot checklist](docs/SCREENSHOT_CHECKLIST.md). The GitHub remote and UI screenshots must be added by the team before submission.

## Troubleshooting

- **No API key configured:** fill `GROQ_API_KEY` in the existing root `.env`, then restart the app. Copy `.env.example` to `.env` only if `.env` is missing.
- **Unsupported provider/model:** choose a supported provider and a model capable of tool calling.
- **Malformed CSV:** ensure a header row, at least one data row, consistent field counts, and UTF-8 or Windows-1252 text.
- **Target analysis skipped:** choose the target in the sidebar. A continuous or very high-cardinality target is unsuitable for the class-imbalance check.
- **Parser failure:** the app shows the tool trace and a raw report response in a debugging expander. Retry or change the model.

## Phase 3 remaining work

Collect live-model results and screenshots, evaluate at least five scenarios including a tool failure, incorporate instructor feedback, make sample input/output evidence, record the 5–7 minute demo, write the 3–4 page technical report, and finalize contribution statements.
