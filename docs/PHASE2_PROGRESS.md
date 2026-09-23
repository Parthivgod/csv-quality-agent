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

For `corrupted_class_imbalance.csv` with target `label`, the class tool found 90 `negative` and 10 `positive` rows, a 9.0:1 ratio. Both a scripted agent test and a separate live Groq service run used only `class_imbalance_check` for a target-distribution question.

## Example Tool Trace

Actual trace shape from the local scripted-model integration test:

```text
1. dataset_profile         ok  Dataset has 30 rows and 4 columns.
2. missing_values_check    ok  2 columns contain missing values.
3. duplicate_rows_check   ok  2 duplicate rows (6.67%). Contextual review is needed.
4. constant_columns_check ok  1 constant and 0 near-constant columns.
```

The trace block above is from a scripted test model. Live Groq observations are recorded in `LIVE_GROQ_VALIDATION.md` and the captured UI trace below.

## Current Output

The parsed report contains summary, issues with severity/evidence/impact/recommendation/source tool, tools used, and limitations. Unsupported evidence is rejected and the report stage retries once.

Local validation on 23 September 2026: `python -m pytest -q` passed 19 tests; `python -m compileall -q .` passed; Streamlit returned HTTP 200 from `/_stcore/health`; the Mistral model and LangChain agent graph constructed with a nonfunctional test credential without sending a request.

The same 19 tests and `pip check` passed in a fresh `.venv` installed from `requirements.txt`; the virtual-environment Streamlit server also returned HTTP 200.

## Problem Encountered and Solution

The first LangChain tool wrapper accidentally exposed internal callable arguments. An explicit empty `NoArgs` schema corrected the tool interface. The wrapper test now confirms every tool schema is `{}`.

## Screenshots

Four genuine Computer Use screenshots now document one live Groq UI run with `corrupted_outliers_corr.csv` and the question “Do the numerical features contain suspicious values or relationships?” The agent called `outlier_check` and `correlation_check`; the report showed 1/30 IQR outlier in each of `feature_x` and `feature_y` and Pearson r = 1.0 between them.

- [Uploaded CSV and dataset profile](screenshots/01_upload_profile.png)
- [Selected tool-call trace](screenshots/02_tool_trace.png)
- [Structured report and outlier evidence](screenshots/03_structured_report.png)
- [Correlation finding](screenshots/03b_correlation_finding.png)

See [PHASE2_SUBMISSION_TEMPLATE.md](PHASE2_SUBMISSION_TEMPLATE.md) for captions and the required repository/roster decisions. [SCREENSHOT_CHECKLIST.md](SCREENSHOT_CHECKLIST.md) names the exact files, UI labels, question, and steps for the two additional screenshots. No browser error-handling or target-specific screenshot has been captured yet.

## Current Limitations

CSV parsing supports UTF-8 and Windows-1252 and is limited to small/medium educational datasets. The target must be selected for class-imbalance analysis. No automatic cleaning or advanced leakage detection is implemented. Tool choice and wording can vary across live model runs; the observed Groq runs are documented separately.

## Remaining Work for Phase 3

For the Phase 2 hand-in, publish the GitHub repository and confirm the team roster. The error/target UI examples are additional evidence with exact instructions in `SCREENSHOT_CHECKLIST.md`. Phase 3 work remains: expand live Groq evaluation, assess one failed tool call, incorporate instructor feedback, record the demo video, prepare the technical report, and finalize individual contribution statements.

## Provider Update

The default model is now Groq-hosted `openai/gpt-oss-120b`. Configure `GROQ_API_KEY` in the root `.env`. The earlier Mistral/OpenAI validation notes above describe the initial implementation. Live Groq evaluation results are in `LIVE_GROQ_VALIDATION.md`.

After the provider change, the clean virtual environment passed 21 tests, compilation, and `pip check`. The provider tests construct `ChatGroq` and bind the diagnostic tools without making an API request.

After the live-run repairs, the suite passed 22 tests. Five live scenarios were run, including distinct tool selections and missing-target handling.
