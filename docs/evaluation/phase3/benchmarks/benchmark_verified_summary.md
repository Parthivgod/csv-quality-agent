# Verified benchmark summary

Original failed 60-second imports and original verifier judgments remain in benchmark_results.csv. This summary uses the separate verified CSV and audit; expected wide skips are guard passes with exact count correctness unassessed. Each statistical tool still requires independent small-fixture parity tests.

| Profile | MiB | Successful imports | Import failures | Max successful ingest s | Peak sampled RSS MiB | Exact count checks passed | Expected guards | Actual count/shape failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tall_numeric | 1.000 | 3 | 0 | 0.268 | 110.0 | 9 | 0 | 0 |
| tall_numeric | 20.000 | 3 | 0 | 3.521 | 158.8 | 9 | 0 | 0 |
| tall_numeric | 50.000 | 3 | 0 | 11.070 | 240.7 | 9 | 0 | 0 |
| tall_numeric | 100.000 | 3 | 0 | 21.468 | 353.2 | 9 | 0 | 0 |
| tall_numeric | 250.000 | 4 | 6 | 93.338 | 824.4 | 13 | 0 | 0 |
| high_unique_strings | 250.000 | 7 | 0 | 41.804 | 730.2 | 22 | 0 | 0 |
| null_heavy | 250.000 | 3 | 0 | 96.977 | 1076.0 | 9 | 0 | 0 |
| quoted_unicode | 250.000 | 3 | 0 | 23.616 | 1002.4 | 9 | 0 | 0 |
| wide_numeric | 250.000 | 3 | 0 | 78.977 | 959.2 | 6 | 3 | 0 |

Peak RSS covers harness and recursive children, excludes uploader/browser memory. Filesystem cache and other desktop load were uncontrolled. Import gate was explicitly revised to 120 seconds; initial 60-second goal flags remain. Three required release imports exist per size/profile; additional diagnostic risk runs may increase import counts.
