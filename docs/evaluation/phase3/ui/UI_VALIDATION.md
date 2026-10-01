# Phase 3 browser validation

Date: **1 October 2026**. Actual Streamlit browser interaction with live Groq `openai/gpt-oss-120b`. Screenshots are computer-use captures. Original Phase 2 evidence is preserved.

## Completed cases

| Case | Exact input / target / question | Observed result | Original app export |
| --- | --- | --- | --- |
| Numeric, final Auto/Pandas | `corrupted_outliers_corr.csv`; none; `Do the numerical features contain suspicious values or relationships?` | 30 rows, 3 columns; outlier and correlation calls both ok; 3 findings; 0.018s local / 6.207s total | [numeric_final_evidence.json](numeric_final_evidence.json) |
| Categorical target, final Auto/Pandas | `corrupted_class_imbalance.csv`; `label`; `Is my target distribution a problem?` | 100 rows; 90 negative / 10 positive; 9:1 ratio, high severity; 4.005s total | [target_final_evidence.json](target_final_evidence.json) |
| Unsuitable target, final Auto/Pandas | Same file; `record_id`; `Check class imbalance in my selected target using the class imbalance tool.` | Tool skipped: too many distinct values; zero supported findings and explicit limitation; 5.014s total | [unsuitable_target_evidence.json](unsuitable_target_evidence.json) |
| Invalid replacement | `invalid_header_only.csv`; no question | `The CSV has no data rows.`; no valid dataset, no previous report or question form | [Screenshot 06](../../../screenshots/phase3/06_invalid_upload.jpg) |
| Large Auto/DuckDB | `tall_numeric_250MiB.csv`; none; `Does this CSV contain missing data?` | 262,143,987 bytes, 3,274,752 rows, 13 columns; import 36.093s; nullable missing 327,476/3,274,752 (10.0%); 3.9375s live run | [large_evidence.json](large_evidence.json) |
| Controlled failure, separate harness | `corrupted_missing_duplicates.csv`; none; `Check this dataset for duplicate rows using the duplicate rows tool.` | Live Groq selected duplicates; injected RuntimeError visible; repeated calls skipped; zero invented findings; limitation retained | Original attempt `T06_controlled_failure_live_1790834576987859300` in [scenario evidence](../scenarios/scenario_results.md) |

Final screenshots 01-10 are in [Phase 3 screenshots](../../../screenshots/phase3/). The older `03_numeric_report_full.jpg` and `04_target_imbalance_full.jpg` were captured earlier during the 20 MB gate stage; they are supplemental historical captures, not final 250 MB gate proof. Original early DuckDB UI exports [numeric_evidence.json](numeric_evidence.json) and [target_evidence.json](target_evidence.json) are retained alongside refreshed Auto/Pandas cases.

## Actual upload memory

[Resource record](large_upload_resources.json) samples the selected Streamlit process and its recursive children every 50ms. Peak **1,376,751,616 bytes / 1312.97 MiB**, under the 2 GiB gate, includes the upload buffer and local backend. Peak owned application temp files: 562,470,858 bytes. Browser RSS is excluded. The sampling window includes waiting and diagnosis; **36.093s import time excludes HTTP upload transfer**. One desktop upload; OS cache and desktop load uncontrolled. This is not a concurrent-user capacity test.

File SHA-256 `af5521abc1b31bc89495128e9813e0c27c4e49749c5d12376272f8677bd3b8b0` matches the benchmark manifest. The missing count matches independently generated fixture truth. The UI reused its cached missing aggregate; the live LLM orchestration timing is separate from local diagnostic timing.

## Repairs observed in actual use

1. Question field reset after background completion despite the correct stored question. Added durable question state; a real Streamlit regression test verifies retained question/target. Final screenshots and original exports show the submitted question.
2. The near-cap 250 MiB file first failed HTTP413 because multipart framing exceeded Streamlit's 250 MiB request limit. Preserved [rejected sampling window](rejected_transport_sampling_window.json), then set transport to251 MiB while widget/loader enforce250 MiB. The same exact fixture then uploaded successfully. [Idle window](idle_sampling_window.json) had no upload and is explicitly not success evidence.
3. Concurrent process monitoring briefly held `owner.json` open on Windows and triggered sharing-lock cleanup errors. Added bounded retries, verified scope every retry, and retained recoverability after persistent locks. New regressions and the final **122-test suite** pass.

## State and coverage checks

Replacing the large dataset with the numeric CSV cleared the prior diagnosis and changed the shape/backend correctly. Changing target cleared the prior target report. Replacing a valid dataset with invalid input removed the old report and loaded state. Automated integration tests also exercise reset, actual import/query cancellation, bounded worker lifecycle, backend parity, and owned file cleanup. Tests are distinct from browser captures.

[Benchmark screenshot 10](../../../screenshots/phase3/10_benchmark_results.jpg) is the static page built from saved verified CSV/summary, not a new benchmark execution. It displays original failed attempts and expected guarded skips.
