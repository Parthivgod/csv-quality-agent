# Phase 3 implementation work log

Date: **1 October 2026**. This log records observed engineering work and validation. Human contribution attribution is separate and requires each student's confirmation.

| Milestone | Change and reason | Evidence / status |
| --- | --- | --- |
| Baseline preserved | Retained eight Pandas diagnostics, Groq orchestration, original fixtures, Phase 2 screenshots and source assignment documents | Original baseline: 22 tests; starting commit `e5f57218f291942ad37bc52bcfabd4ffd71f5db9` |
| Shared dataset access | DatasetHandle and Pandas adapter let agent/UI use either backend | Backend and actual graph integration tests |
| Strict bounded ingestion | Chunked hash/copy; owned OS temp paths; shared encoding, fields, nulls, headers and full-column type inference | CSV contract, ingestion and storage tests |
| Exact disk backend | Typed Parquet and eight SQL diagnostics; finite statistics; exact full-row distinct count; stable preview | All-eight parity on four original fixtures plus quoted/multiline/null/leading-zero/infinity cases |
| Query efficiency | Pearson pairs share one scan; both quartiles share one aggregate state | Backend parity tests; benchmark records |
| Resource and cancellation | Engine limits, spill/session quotas, numeric/duplicate-width guards, quartile preflight; actual query/import interruption | Tests interrupt a real huge aggregation and verify cleanup/new-run usability |
| Evidence context | Bounded observations and explicit omitted findings/data/eligible columns; cache provenance; full local export | Output cap and fullgraph integration tests |
| Report grounding | Exact matching, restoration of supplied findings, deterministic summary/limitations; unsupported issues rejected after retry | Scripted fullgraph tests; fresh live attempts and retained failures |
| Live evaluation | Executed Groq questions with observed selected tools; controlled exception only in harness | Scenario JSON/trace/report and attempt index; no production fault toggle |
| Scaling challenge | Initial 250 MiB tall imports exceeded the proposed 60-second strict-validation goal | Failed raw benchmark attempts retained |
| Budget decision | Revised release import budget to 120 seconds for measured full-column validation cost | Engineering decision; fresh benchmarks required before release claim |
| Final release proof | 250 MiB typical profiles passed repeat imports; all-eight risk runs completed; a real 262,143,987-byte browser upload loaded 3,274,752 rows | Verified CSV/audit; original UI evidence; sampled app RSS 1312.97 MiB including uploader, excluding browser |
| Transport repair | Retained initial rejected upload; allowed 251 MiB transport framing while keeping widget/loader file limit at 250 MiB | Actual browser upload of 262,143,987 bytes; no dedicated transport regression test is claimed |
| Final validation | 122 tests passed in 12.29s; dependencies and compile checks clean | `docs/evaluation/phase3/test_results.txt` |
| Submission preparation | Actual architecture SVG/PNG, reproducible four-page report, editable source, results page and contribution templates | PDF rendered and inspected after final evidence |

## Interpretation of evidence

Scripted tests verify actual wiring and constraints; they do not evaluate live LLM reasoning quality. Provider scenarios record real selection and latency. The diagnostic benchmark measures process/child RSS and owned temp storage, excludes browser/uploader memory, and does not control OS filesystem cache. A separate app upload measurement retains its own boundary.

Failed and throttled attempts remain in the evidence directory. Latest summaries do not erase initial results. Working-tree hashes and environment files identify benchmark snapshots; the original Git commit alone does not describe modified source.

## Remaining human actions

- Record the real 5-7 minute video using the timed script and at least two live cases.
- Confirm each individual's actual work and AI assistance in the contribution statements.
- Obtain the instructor's feedback form and Phase 2 feedback.
- Confirm roster and late/revised submission instructions. The brief's deadline was 30 September 2026; no extension is asserted.

## LLM synthesis revision - 1 October 2026

User requested model-written summary, interpretation/next steps, and short tool-choice explanations. The summary is now retained while exact tool findings and deterministic scope/limits remain separate. Class percentages and configured thresholds are exposed in tool results without changing trigger rules. Numeric/source checks reject unsupported narrative values and citations; they are not semantic proof of model prose. Regression tests found and fixed sentence-final numeric parsing and negation leaking across clauses. **149 tests passed in 10.31s**, plus three fresh CLI Groq cases and one actual browser run; a 429 attempt was retained before retry. Captures 11-13 and the original UI JSON are in [revision evidence](evaluation/phase3/llm_synthesis/README.md). Earlier 250 MiB benchmarks and upload records were preserved and not rerun. The technical report/architecture/demo script were updated; prior report artifacts are archived.
