# LLM synthesis update - verified evidence

Date: **1 October 2026**. This revision adds model-written summary, source-linked interpretation, suggested next steps, and brief tool-choice explanations. Original Phase 3 provider, upload and benchmark records remain unchanged. No 250 MiB benchmarks were rerun for this reporting update.

## Fresh checks

| Case | Result | Actual tools | Total seconds | Original evidence |
| --- | --- | --- | --- | --- |
| N01 Moderate 60/40 | pass | class_imbalance_check | 5.123 | [Result](N01_moderate_synthesis_live_1790849109222287800_result.json), [report](N01_moderate_synthesis_live_1790849109222287800_report.json), [trace](N01_moderate_synthesis_live_1790849109222287800_trace.json) |
| T04 Numeric features | pass | outlier_check, correlation_check | 27.777 | [Result](T04_numeric_live_1790849139329035600_result.json), [report](T04_numeric_live_1790849139329035600_report.json), [trace](T04_numeric_live_1790849139329035600_trace.json) |
| T07 Missing target | pass | none (target not selected) | 2.755 | [Result](T07_missing_target_live_1790849288256192700_result.json), [report](T07_missing_target_live_1790849288256192700_report.json), [trace](T07_missing_target_live_1790849288256192700_trace.json) |

The first T07 attempt returned a Groq 429 token-limit error. Its original result/report/trace remain in this folder; the later completed attempt is linked above. The CLI harness verifies expected tool/evidence behavior; the regression suite checks retention, source/number rejection, exact findings, no-tool guidance and UI/export behavior.

**149 tests passed in 10.31s**; [full test/dependency/compile record](test_results.txt). Scripted tests validate wiring and rules, not live reasoning quality.

## Actual browser run

A separate app session loaded `class_distribution_moderate.csv` (100 rows, 3 columns, 2,115 bytes), selected `label`, and submitted:

> Is my target distribution a problem? Explain what the observed distribution means and suggest next steps.

Live Groq `openai/gpt-oss-120b` called only `class_imbalance_check` and supplied a brief reason. The app displayed its own summary of 60/40 (1.5:1), a cited interpretation, and five suggested next steps even though there were zero verified findings. Original [downloaded UI evidence](ui_evidence.json) records 4.6215s total (the screen rounds to 4.622s).

| Capture | Exact actions after completion | Evidence shown |
| --- | --- | --- |
| [11_llm_summary.jpg](../../../screenshots/phase3/11_llm_summary.jpg) | Scroll to **LLM summary** | Tool-choice explanation, own-word summary, separate verified scope and zero-findings result |
| [12_llm_interpretation.jpg](../../../screenshots/phase3/12_llm_interpretation.jpg) | Scroll to **LLM interpretation** | Source-linked interpretation and first suggestions |
| [13_llm_next_steps.jpg](../../../screenshots/phase3/13_llm_next_steps.jpg) | Scroll to **Suggested next steps** | All proposed next steps, clearly distinct from performed checks |

## Reproduce

Use the sample dropdown in the app, select the file/target/question above, and run. Re-run existing numeric/missing-target cases with:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_phase3.py --live --scenarios T04 T07 --output-dir docs/evaluation/phase3/llm_synthesis
```

Each run gets a new timestamped filename; the command does not replace original attempt JSON. The combined revision manifest lists the three observed CLI runs and is separate from the UI export.

## Validation boundaries

Verified issue fields remain exact copies of tool findings; code derives tool list, coverage/limits and `assessment_summary`. It preserves LLM `summary`, `interpretation` and `next_steps`. Each interpretation names actual observed tools; numeric literals must be supplied by its sources; general clean-data assurances are guarded. These are structural and heuristic checks, not semantic proof of every sentence. Suggested actions are not completed computations. Brief reasons explain relevance and do not expose private deliberation. No observed issue threshold, class-count definition or large-data resource setting was changed; class percentages and thresholds are additionally exposed for evidence-based explanation.
