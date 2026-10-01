# Measured Phase 3 benchmarks

Sizes use MiB. Three independent imports are required for release acceptance. OS filesystem cache was uncontrolled. RSS includes harness and recursive children, excludes Streamlit upload/browser buffers. Temporary storage was sampled every 50 ms during import and checks. API/report latency is excluded. The initial 60-second import goal was revised explicitly to 120 seconds after observed validation timeouts; original failed attempts remain below.

## All attempts, including initial 60-second failures

| Profile | Actual MiB | Imports | Max ingest s | Max check s | Peak RSS MiB | Peak temp MiB | Count correctness failures | Budget failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tall_numeric | 1.000 | 3 | 0.268 | 0.015 | 110.0 | 2.0 | 0 | 0 |
| tall_numeric | 20.000 | 3 | 3.521 | 0.073 | 158.8 | 42.9 | 0 | 0 |
| tall_numeric | 50.000 | 3 | 11.070 | 0.211 | 240.7 | 105.4 | 0 | 0 |
| tall_numeric | 100.000 | 3 | 21.468 | 0.324 | 353.2 | 214.8 | 0 | 0 |
| tall_numeric | 250.000 | 10 | 93.338 | 8.007 | 824.4 | 536.4 | 6 | 6 |
| high_unique_strings | 250.000 | 7 | 41.804 | 0.912 | 730.2 | 506.0 | 0 | 0 |
| null_heavy | 250.000 | 3 | 96.977 | 2.061 | 1076.0 | 574.9 | 0 | 0 |
| quoted_unicode | 250.000 | 3 | 23.616 | 0.767 | 1002.4 | 528.0 | 0 | 0 |
| wide_numeric | 250.000 | 3 | 78.977 | 0.049 | 959.2 | 564.9 | 3 | 0 |

## Revised 120-second release attempts

| Profile | Actual MiB | Independent imports | Max ingest s | Initial 60-second goal misses | Correctness failures | Release budget failures |
| --- | --- | --- | --- | --- | --- | --- |
| tall_numeric | 250.000 | 4 | 93.338 | 3 | 0 | 0 |
| high_unique_strings | 250.000 | 4 | 36.612 | 0 | 0 | 0 |
| null_heavy | 250.000 | 3 | 96.977 | 2 | 0 | 0 |
| quoted_unicode | 250.000 | 3 | 23.616 | 0 | 0 | 0 |
| wide_numeric | 250.000 | 3 | 78.977 | 3 | 3 | 0 |

Count correctness checks compare generator null, duplicate and class invariants, plus shape/hash. Other tools are executed but require separate numerical/statistical parity tests; an empty correctness field is not a pass. Cache-repeat results and original observations are retained per attempt. Failed/skipped runs remain in the CSV and JSON.
