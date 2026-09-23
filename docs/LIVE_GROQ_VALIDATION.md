# Live Groq Validation — 23 September 2026

Model: Groq-hosted `openai/gpt-oss-120b` through `ChatGroq`. The API key was loaded from the Git-ignored `.env` and was never printed or committed. These runs used the actual LangChain agent and Groq API, not the scripted test model.

| Scenario | Question / target | Observed tool calls | Result |
|---|---|---|---|
| Missing values | “Does this CSV contain missing data?” / none | `missing_values_check` | Parsed report: `age` 6/30 missing (20.0%); `income` 3/30 missing (10.0%). |
| Class imbalance | “Is my target distribution a problem?” / `label` | `class_imbalance_check` | Parsed report: 90 negative, 10 positive, 9.0:1 ratio. |
| Numeric issues | “Do the numerical features contain suspicious values or relationships?” / none | `outlier_check`, `correlation_check` | Parsed report: one IQR outlier each in `feature_x` and `feature_y`; Pearson r = 1.0 for that pair. |
| Broad training issue | “Why could this dataset cause problems during model training?” / none | `missing_values_check`, `constant_columns_check`, `high_cardinality_check`, `duplicate_rows_check` | Parsed report after repair: missing `age`/`income`, constant `constant_feature`, and two duplicate rows. The cardinality tool returned no findings for continuous numeric fields. |
| No target selected | “Is my target imbalanced?” / none | No tool call | Parsed report with no issue and an explicit “Select a target column to assess class imbalance” limitation. |

The four diagnostic question traces differed according to the question. Each tool status was `ok`. The no-target run made no target-specific tool call.

## Problem found and fixed

The first broad live run flagged continuous numeric `age` and `income` as high-cardinality candidates. The diagnostic now examines categorical fields and numeric fields with identifier-like names. A deterministic regression test was added, and the broad Groq run was repeated. It no longer reports those columns as identifier candidates; `record_id` in the class fixture remains detectable.

The first no-target run gave an underspecified limitation. Report validation now appends a direct target-selection instruction for target or imbalance questions without a selected target. A live rerun confirmed that instruction appears.

## Validation boundary

The clean virtual environment passed 22 tests. The restarted Streamlit page showed `groq / openai/gpt-oss-120b` and “API key configured”; its health endpoint returned HTTP 200. A subsequent live Streamlit UI run using the numeric-issues question selected only `outlier_check` and `correlation_check`. Its tool trace and report were captured in [the Phase 2 screenshot set](SCREENSHOT_CHECKLIST.md). The other scenarios above were service-level API runs. LLM tool choices and wording may vary between runs; these are observed results for the stated fixtures and questions.
