# Final repository package validation

Reviewed on **2 October 2026**. This is a repository and deliverable check; earlier provider, recording and large-file measurements keep their original dates.

| Check | Observed result | Record |
| --- | --- | --- |
| Automated suite | 149 passed in 32.86 seconds | [Test output](test_results.txt) |
| Dependencies | No broken requirements found | [Dependency output](test_results.txt) |
| Python compilation | app.py, src, scripts and tests compiled; exit 0 | [Command record](test_results.txt) |
| Technical report | Four pages, all rendered pages inspected | [Document verification](document_validation.json) |
| Contributions | Two-page PDF, matching reviewed Word export; unchanged during cleanup | [Document verification](document_validation.json) |
| Silent demo | SHA-256 and size match the original successful 390-second, video-only decode record | [Original video validation](../../../../submission/recording_evidence_20261001/final_validation.json) |
| Filmed runs | Both original exported JSON hashes match recording validation | [Recorded evidence](../../../../submission/recording_evidence_20261001/) |
| Repository package | Deliverable hashes, tracked files, current Markdown links and credential/editor-file exclusions checked | [Package audit](package_validation.json), [artifact manifest](../../../../submission/SUBMISSION_MANIFEST.json) |
| Git copy and mismatch control | Staged Git snapshot passes; an intentionally incorrect checksum is rejected | [Portability verification](portability_check.json) |

The package auditor uses only the Python standard library:

```powershell
.\.venv\Scripts\python.exe scripts/verify_submission.py
```

The audit is read-only unless an output path is explicitly requested. Saved metadata is trusted only after the referenced media hash matches. It does not replace a semantic review of model output, certify signatures, or claim that the silent video has narration. PDF layout was checked separately from the standard-library audit.

No new API calls or large-data benchmarks were needed for this cleanup. Earlier failed/throttled attempts and historical reports remain available. Remaining course actions are in the [submission checklist](../../../../submission/README.md).
