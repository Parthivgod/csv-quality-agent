# Phase 3 scenario results

Original attempts are retained; scripted runs are wiring tests, live runs measure actual provider tool selection.

| ID | Mode | Result | Actual calls | Seconds | Evidence |
| --- | --- | --- | --- | --- | --- |
| T01 | live Groq | pass | missing_values_check | 3.091842 | [T01_missing_live_1790832606589647000](T01_missing_live_1790832606589647000_result.json) |
| T02 | live Groq | pass | missing_values_check, constant_columns_check, duplicate_rows_check | 52.431791 | [T02_broad_live_1790832609686127300](T02_broad_live_1790832609686127300_result.json) |
| T03 | live Groq | error | class_imbalance_check | 21.180169 | [T03_target_live_1790832662123856100](T03_target_live_1790832662123856100_result.json) |
| T03 | live Groq | pass | class_imbalance_check | 12.533745 | [T03_target_live_1790833041719148300](T03_target_live_1790833041719148300_result.json) |
| T04 | live Groq | pass | outlier_check, correlation_check | 38.395891 | [T04_numeric_live_1790832683307010900](T04_numeric_live_1790832683307010900_result.json) |
| T05 | live Groq | error |  | 9.332953 | [T05_unexpected_target_live_1790832721713928600](T05_unexpected_target_live_1790832721713928600_result.json) |
| T05 | live Groq | error | class_imbalance_check | 16.144705 | [T05_unexpected_target_live_1790833054267021200](T05_unexpected_target_live_1790833054267021200_result.json) |
| T05 | live Groq | pass | class_imbalance_check | 4.330422 | [T05_unexpected_target_live_1790833312344947400](T05_unexpected_target_live_1790833312344947400_result.json) |
| T06 | live Groq | fail | duplicate_rows_check, duplicate_rows_check, duplicate_rows_check | 45.053655 | [T06_controlled_failure_live_1790832731062843700](T06_controlled_failure_live_1790832731062843700_result.json) |
| T06 | live Groq | pass | duplicate_rows_check | 4.941361 | [T06_controlled_failure_live_1790833070427350200](T06_controlled_failure_live_1790833070427350200_result.json) |
| T07 | live Groq | error |  | 9.319585 | [T07_missing_target_live_1790832776119549700](T07_missing_target_live_1790832776119549700_result.json) |
| T07 | live Groq | pass |  | 11.159181 | [T07_missing_target_live_1790833075373812000](T07_missing_target_live_1790833075373812000_result.json) |
| T08 | live Groq | pass | missing_values_check | 15.956249 | [T08_clean_live_1790832785441542100](T08_clean_live_1790832785441542100_result.json) |
| T09 | live Groq | pass |  | 0.021354 | [T09_invalid_input_live_1790832801405734300](T09_invalid_input_live_1790832801405734300_result.json) |
