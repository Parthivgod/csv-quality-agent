# Phase 2 Screenshot Checklist

Run `python -m streamlit run app.py` after configuring `.env`. Save genuine screenshots in `docs/screenshots/` with these names:

1. `01_upload.png`: upload `corrupted_missing_duplicates.csv`; include filename, dimensions, column/dtype table, and preview.
2. `02_tool_trace.png`: ask “Why could this dataset cause problems during model training?”; include the observable tool trace.
3. `03_structured_report.png`: on the same run, include an issue card with evidence, recommendation, and source tool.
4. `04_error_handling.png`: upload an empty or malformed CSV and include the friendly validation error.
5. `05_selective_target.png`: upload `corrupted_class_imbalance.csv`, select `label`, ask “Is my target distribution a problem?”, and show the shorter target-specific trace.

Capture the app's actual output. Do not paste scripted test output into a screenshot or present it as live provider behavior. Add the GitHub URL and screenshot paths to `PHASE2_PROGRESS.md` before submission.
