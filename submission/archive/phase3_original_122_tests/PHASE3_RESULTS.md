# Phase 3 measured results

Generated 1 October 2026 from saved evidence; latest attempts are summarized and original attempts retained.

Automated verification supplied after testing: **122 passed**. [Saved test, dependency and compile results](evaluation/phase3/test_results.txt).

## Live Groq scenarios

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

The PDF includes latest recorded results. Video, real feedback form, roster/deadline confirmation and individually confirmed contribution statements remain human deliverables.

## Actual browser upload

Completed **262,143,987 bytes / 3,274,752 rows / 13 columns** in DuckDB. Import **36.093s**, excluding HTTP transfer; live Groq missing-value diagnosis **3.9375s**. Sampled peak app/worker RSS **1312.97 MiB** includes the Streamlit buffer but excludes browser RSS. One desktop upload; OS cache and desktop load uncontrolled.

[Original downloaded app evidence](evaluation/phase3/ui/large_evidence.json), [resource record](evaluation/phase3/ui/large_upload_resources.json), and [browser validation](evaluation/phase3/ui/UI_VALIDATION.md). Earlier idle/rejected sampling windows are not successful upload evidence.
