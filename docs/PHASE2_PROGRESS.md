# CSV Data Quality Triage Agent — Phase 2 Progress

## Team

Parthiv Godrihal — I024: Agent, LangChain and app integration.  
Nilay Jain — I029: Data diagnostics, evaluation and testing.  
The official brief mentions three-person groups; the submitted proposal names these two members. See `IMPLEMENTATION_NOTES.md`.

## GitHub Link

Pending: add the repository URL after pushing this local Git repository.

## Work Completed

The repository has a Streamlit app, CSV validation, an in-memory DataFrame, a compact schema context, eight deterministic diagnostics, LangChain tool wrappers, an agent, an LCEL report chain, a Pydantic parser, a visible trace, sample datasets, ground-truth manifests, and automated tests.

## Working Components

The initial Streamlit page starts without an API key. Upload/profile behavior is implemented. The automated agent workflow runs with a scripted local chat model and selects different tools for different questions. Live Groq runs have now also selected different tools and produced validated reports; see `LIVE_GROQ_VALIDATION.md`.

## Diagnostic Tools Implemented

`dataset_profile`, `missing_values_check`, `duplicate_rows_check`, `constant_columns_check`, `high_cardinality_check`, `outlier_check`, `class_imbalance_check`, and `correlation_check` are implemented and tested. The optional dtype anomaly check is deferred.

## Current Architecture

`Streamlit → loader → schema context → ChatPromptTemplate + create_agent → selected diagnostic tools → trace → LCEL report chain → PydanticOutputParser → validated report UI`

The DataFrame stays local. The LLM sees schema and aggregate tool results.

## Example Test Case

For `corrupted_missing_duplicates.csv`, the deterministic tools found 6/30 missing `age` values (20.0%), 3/30 missing `income` values (10.0%), 2 duplicate rows (6.67%), and one constant feature. These match the fixture manifest.

For `corrupted_class_imbalance.csv` with target `label`, the class tool found 90 `negative` and 10 `positive` rows, a 9.0:1 ratio. The scripted agent path used only `class_imbalance_check` for the target-distribution question.

## Example Tool Trace

Actual trace shape from the local scripted-model integration test:

```text
1. dataset_profile         ok  Dataset has 30 rows and 4 columns.
2. missing_values_check    ok  2 columns contain missing values.
3. duplicate_rows_check   ok  2 duplicate rows (6.67%). Contextual review is needed.
4. constant_columns_check ok  1 constant and 0 near-constant columns.
```

The target-distribution question produces a one-tool trace. These are test-model traces, not a live Mistral/OpenAI run.

## Current Output

The parsed report contains summary, issues with severity/evidence/impact/recommendation/source tool, tools used, and limitations. Unsupported evidence is rejected and the report stage retries once.

Local validation on 23 September 2026: `python -m pytest -q` passed 19 tests; `python -m compileall -q .` passed; Streamlit returned HTTP 200 from `/_stcore/health`; the Mistral model and LangChain agent graph constructed with a nonfunctional test credential without sending a request.

The same 19 tests and `pip check` passed in a fresh `.venv` installed from `requirements.txt`; the virtual-environment Streamlit server also returned HTTP 200.

## Problem Encountered and Solution

The first LangChain tool wrapper accidentally exposed internal callable arguments. An explicit empty `NoArgs` schema corrected the tool interface. The wrapper test now confirms every tool schema is `{}`.

## Screenshots

No live-agent screenshots have been captured. Use `SCREENSHOT_CHECKLIST.md` after setting a provider key; do not represent the scripted test output as a live model screenshot.

## Current Limitations

CSV parsing supports UTF-8 and Windows-1252 and is limited to small/medium educational datasets. The target must be selected for class-imbalance analysis. No automatic cleaning or advanced leakage detection is implemented. Tool choice and wording can vary across live model runs; the observed Groq runs are documented separately.

## Remaining Work for Phase 3

Expand live Groq evaluation, capture real UI screenshots, push the GitHub repository, assess one failed tool call, incorporate instructor feedback, record the demo video, prepare the technical report, and finalize individual contribution statements.

## Provider Update

The default model is now Groq-hosted `openai/gpt-oss-120b`. Configure `GROQ_API_KEY` in the root `.env`. The earlier Mistral/OpenAI validation notes above describe the initial implementation. Live Groq evaluation results are in `LIVE_GROQ_VALIDATION.md`.

After the provider change, the clean virtual environment passed 21 tests, compilation, and `pip check`. The provider tests construct `ChatGroq` and bind the diagnostic tools without making an API request.

After the live-run repairs, the suite passed 22 tests. Five live scenarios were run, including distinct tool selections and missing-target handling.
