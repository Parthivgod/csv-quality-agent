# Phase 3 submission package

**Project:** CSV Data Quality Triage Agent

**Team:** Parthiv Godrihal (I024), Nilay Jain (I029)

**Package reviewed:** 2 October 2026

## Files for the instructor

| Deliverable | File | Status |
| --- | --- | --- |
| Working application and setup instructions | [Repository README](../README.md) | Code, configuration example and run commands included |
| Technical report | [Phase3_Technical_Report.pdf](Phase3_Technical_Report.pdf) | Four pages; includes architecture, scenarios, failure handling, results and limits |
| Demo video | [Phase3_CSV_Data_Quality_Demo.mp4](Phase3_CSV_Data_Quality_Demo.mp4) | Recorded silent base, 6:30, 1080p; add your narration before narrated hand-in |
| Narration | [Phase3_Voiceover_Script.md](Phase3_Voiceover_Script.md) | Matched to the recorded video's chapter timestamps |
| Individual contributions | [Individual_Contribution_Statement.pdf](Individual_Contribution_Statement.pdf) | Two pages, one per member; confirmed split; signatures and dates remaining |
| Editable contributions | [Individual_Contribution_Statement.docx](Individual_Contribution_Statement.docx) | Word copy for corrections and signing |
| Architecture | [Diagram](../docs/assets/phase3_architecture.png), [editable SVG](../docs/assets/phase3_architecture.svg), [explanation](../docs/ARCHITECTURE.md) | Matches the implemented workflow |
| Sample inputs and outputs | [Sample CSVs](../data/samples/), [recorded case A](recording_evidence_20261001/case_A_numeric_recorded.json), [recorded case B](recording_evidence_20261001/case_B_moderate_recorded.json) | Synthetic inputs and original downloaded run evidence |
| Tests and evaluation | [Final package checks](../docs/evaluation/phase3/submission/README.md), [measured results](../docs/PHASE3_RESULTS.md) | Automated checks, live scenarios, retained failures and earlier size benchmarks |
| Screenshots | [Phase 3 captures](../docs/screenshots/phase3/), [capture guide](../docs/PHASE3_EVALUATION_AND_SUBMISSION.md) | Actual UI captures with prompts, steps and captions |

The [technical report text](Phase3_Technical_Report.md) and [contribution text](Contribution_Statements.md) are editable sources. [Original report artifacts](archive/README.md) are historical reference, not the current hand-in.

## Video evidence

The film shows two fresh Groq runs on 1 October 2026: numerical outliers/correlation and a selected target with a 60/40 distribution. It also shows actual LangChain source, labeled saved benchmark results and earlier controlled-failure evidence. Navigation and processing waits were trimmed; some informational screens are held longer for narration.

[Recording log](../docs/VIDEO_RECORDING_2026-10-01.md), [original video validation](recording_evidence_20261001/final_validation.json) and [final chapter timeline](recording_evidence_20261001/final_timeline.json) preserve the recording boundaries. The MP4 contains no audio track. It must not be described as a completed narrated video.

## Remaining hand-in steps

1. Record your voice-over with the matched script, combine it with the silent MP4, and check final audio, playback and 5–7 minute duration.
2. Each member reviews, signs and dates their contribution statement. If you edit the Word copy, export a matching PDF.
3. Obtain and complete the actual course feedback form; apply any instructor feedback.
4. Confirm the accepted two-member roster and applicable submission instructions. The supplied brief lists 30 September 2026 and has inconsistent group-size wording; no extension or roster approval is claimed here.
5. Confirm the instructor can access the repository and the narrated video, then upload the required files to the course platform.

## Verify the repository package

From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/verify_submission.py
```

This read-only check verifies tracked deliverables against [SUBMISSION_MANIFEST.json](SUBMISSION_MANIFEST.json), local Markdown links, video integrity and excluded credentials/editor files. Binary files and original filmed-run exports use exact byte hashes; other text hashes normalize CRLF to LF for Windows/Linux portability. It does not submit coursework, certify signatures or evaluate narration. Replacing a final artifact requires updating its manifest hash after verification.

## Rebuild the technical report

The report builder needs ReportLab, Pillow and pypdf in addition to the app environment. These are authoring dependencies, not required to run Streamlit. Install [requirements-submission.txt](../requirements-submission.txt) in the environment used for report generation, then run:

```powershell
.\.venv\Scripts\python.exe scripts/build_phase3_report.py --test-count 149 --verified-limit-mb 250 --import-budget-seconds 120 --upload-evidence docs/evaluation/phase3/ui/large_upload_resources.json --synthesis-manifest docs/evaluation/phase3/llm_synthesis/revision_manifest.json --video-validation submission/recording_evidence_20261001/final_validation.json --report-date "2 October 2026"
```

This reads saved measurements without rerunning provider calls or large-file benchmarks. The editorial date does not change the dates of the underlying measurements. Recheck the four-page layout after rebuilding.
