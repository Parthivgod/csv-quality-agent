# Phase 3 measured results

LLM synthesis revision, 1 October 2026. Original benchmark/live measurements below are retained, not rerun or relabeled. [Original 122-test report and source](../submission/archive/phase3_original_122_tests/).

Original automated baseline: **122 passed**. [Original test, dependency and compile results](evaluation/phase3/test_results.txt).

## Original live Groq scenarios

| ID | Result | Calls | Seconds |
| --- | --- | --- | --- |
| T01 | pass | missing_values_check | 3.09 |
| T02 | pass | missing_values_check, constant_columns_check, duplicate_rows_check | 52.43 |
| T03 | pass | class_imbalance_check | 12.53 |
| T04 | pass | outlier_check, correlation_check | 38.40 |
| T05 | pass | class_imbalance_check | 4.33 |
| T06 | pass | duplicate_rows_check, duplicate_rows_check, duplicate_rows_check, duplicate_rows_check | 7.69 |
| T07 | pass |  | 11.16 |
| T08 | pass | missing_values_check | 15.96 |
| T09 | pass |  | 0.02 |

[All attempts and evidence](evaluation/phase3/scenarios/scenario_results.md)

## Diagnostic benchmarks

| Profile | MiB | Runs | Max import s | Peak RSS MiB | Peak temp MiB | Gate |
| --- | --- | --- | --- | --- | --- | --- |
| tall_numeric | 1 | 3 | 0.27 | 110.0 | 2.0 | pass |
| tall_numeric | 20 | 3 | 3.52 | 158.8 | 42.9 | pass |
| tall_numeric | 50 | 3 | 11.07 | 240.7 | 105.4 | pass |
| tall_numeric | 100 | 3 | 21.47 | 353.2 | 214.8 | pass |
| high_unique_strings | 250 | 3 | 36.61 | 730.2 | 506.0 | pass |
| null_heavy | 250 | 3 | 96.98 | 1076.0 | 574.9 | pass |
| quoted_unicode | 250 | 3 | 23.62 | 1002.4 | 528.0 | pass |
| tall_numeric | 250 | 3 | 62.09 | 813.0 | 534.9 | pass |
| wide_numeric | 250 | 3 | 78.98 | 959.2 | 564.9 | guarded |

[Verified benchmark CSV](evaluation/phase3/benchmarks/benchmark_results_verified.csv), [verification audit](evaluation/phase3/benchmarks/benchmark_verification_audit.json), and [original raw CSV](evaluation/phase3/benchmarks/benchmark_results.csv). Pass covers independently checked counts/shape and resource gates; statistical large-file correctness without independent truth remains unassessed. Guarded means expected scope skips, not computed exact statistics. Process plus child RSS excludes browser/uploader. OS cache uncontrolled. Latest run per profile/size/repeat selected; initial failed attempts remain in raw records.

Release upload limit recorded for this report: 250 MiB. Release import budget: 120s. The original 60s import goal failed on 250MiB tall data; budget revision is documented and does not erase failure.

The silent two-case demo is 6:30 with a matched script; contributions follow the confirmed split. Add narration, sign statements, complete the real feedback form and confirm course instructions. The brief's deadline was 30 September 2026. See submission/README.md.

## Actual browser upload

Completed **262,143,987 bytes / 3,274,752 rows / 13 columns** in DuckDB. Import **36.093s**, excluding HTTP transfer; live Groq missing-value diagnosis **3.9375s**. Sampled peak app/worker RSS **1312.97 MiB** includes the Streamlit buffer but excludes browser RSS. One desktop upload; OS cache and desktop load uncontrolled.

[Original downloaded app evidence](evaluation/phase3/ui/large_evidence.json), [resource record](evaluation/phase3/ui/large_upload_resources.json), and [browser validation](evaluation/phase3/ui/UI_VALIDATION.md). Earlier idle/rejected sampling windows are not successful upload evidence.

## LLM synthesis revision: fresh verification

**149 passing tests**. [Separate revision test record](evaluation/phase3/llm_synthesis/test_results.txt).

| Case | Status | Calls | Seconds | Evidence |
| --- | --- | --- | --- | --- |
| N01 | pass | class_imbalance_check | 5.12 | [Original evidence](evaluation/phase3/llm_synthesis/N01_moderate_synthesis_live_1790849109222287800_result.json) |
| T04 | pass | outlier_check, correlation_check | 27.78 | [Original evidence](evaluation/phase3/llm_synthesis/T04_numeric_live_1790849139329035600_result.json) |
| T07 | pass |  | 2.76 | [Original evidence](evaluation/phase3/llm_synthesis/T07_missing_target_live_1790849288256192700_result.json) |

N01 explains the observed 60/40 class distribution and ratio 1.5 without a flagged issue under the unchanged 3/9 thresholds. T07 provides target-selection guidance with no diagnostic call. Its first revision HTTP 429 failure remains saved alongside the successful retry.

The model-written summary, cited interpretations and next-step suggestions are retained. Exact issue matching and deterministic assessment/coverage remain separate. Cited tools must have been called and narrative numeric literals must occur in observed results (restricted to cited tools for interpretations). Broad clean/safe/leakage assurances are rejected. Numeric containment, which can include execution metadata, does not prove correct number-to-column attachment or semantic validity. Public pre-call reasons explain relevance and are not private chain of thought.

The imbalance observations now include class percentages and the unchanged 3/9 ratio thresholds. No scaling benchmark was rerun for this revision.

A separate fresh browser run took **4.6215s**. [Original downloaded revision evidence](evaluation/phase3/llm_synthesis/ui_evidence.json). Computer-use screenshots: [summary and public tool purpose](screenshots/phase3/11_llm_summary.jpg), [cited interpretation](screenshots/phase3/12_llm_interpretation.jpg), [proposed next steps](screenshots/phase3/13_llm_next_steps.jpg). These are fresh revision evidence, separate from the original 250 MiB upload.
