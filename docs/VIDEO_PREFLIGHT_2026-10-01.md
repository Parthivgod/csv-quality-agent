# Video preflight — 1 October 2026

Status: technical preflight passed. This document records the earlier checks and unrecorded rehearsals. The user subsequently authorized recording and retry; the completed recording is documented in `VIDEO_RECORDING_2026-10-01.md`.

Source revision: `46a1c07` — Add LLM synthesis, next steps and visible tool-choice explanations. Application source and configuration were not modified during this preflight.

## Assignment coverage

The original brief is `docs/source/Lab 9_2026_27.docx`, Activity 2, Deliverables, and Phase 3 Submission. It requires a 5–7 minute video with a problem/use case, architecture and LangChain components, at least two live cases, one challenge and its handling, and limitations/improvements. At least three appropriate LangChain components must be integrated. The current app has a prompt template, agent/structured tools, LCEL, and a Pydantic output parser.

The five-test-scenario and failure-case requirements also apply to the technical report. The video will briefly show the saved evaluation matrix and clearly labeled controlled-failure evidence; it does not need nine fresh cases during recording.

| Final time | Visuals | Purpose |
| --- | --- | --- |
| 0:00–0:45 | App heading, upload/sample controls, preview | Problem and use case |
| 0:45–1:15 | `docs/assets/phase3_architecture.png` | Local tools / LLM / report workflow |
| 1:15–2:15 | Actual prompt, agent constructor, tool wrappers, report chain | Explain four LangChain components |
| 2:15–3:25 | Fresh numerical sample run | Question, selected tools, evidence, report |
| 3:25–4:30 | Fresh moderate-distribution run with target `label` | Useful explanation with no threshold finding |
| 4:30–5:30 | Saved benchmark summary and labeled failure evidence | Large-file challenge, solution and actual failure handling |
| 5:30–6:30 | Evaluation evidence and limitations | Tests, coverage boundaries and proposed improvements |

Total: 390 seconds (6:30). The original narration is in `docs/PHASE3_DEMO_SCRIPT.md`; retain its evidence boundaries while adding the explicit source-code views above. Final timestamps must follow the finished edit.

## Prepared code and app views

- Dedicated VS Code workspace: `tmp/video_preflight/demo.code-workspace`; folder resolves to this repository. Font size 18, word wrap enabled, minimap disabled. Primary and secondary sidebars were hidden for the code inspection. `.env`, `.venv`, `.git`, and temporary files are excluded from the workspace explorer.
- Source views: `src/agent/prompt.py` at `AGENT_PROMPT` (line 6), `factory.py` at `create_investigation_agent`, `tools.py` at the diagnostics map and `StructuredTool.from_function`, and `report_chain.py` at `create_report` (line 115; parser line 119).
- Show the actual system prompt rules and separately show each user question in the app.
- Dedicated Chrome app window created, maximized, and put into full screen. The existing user browser session and earlier dataset remain in their original window. Use the dedicated window for recording.
- The prior browser-policy failure was resolved by activating/restoring Chrome before state capture. The restored browser exposed `http://127.0.0.1:8503/` through its address bar and document URL.
- App health endpoint returned HTTP 200. Provider: Groq; model: `openai/gpt-oss-120b`; provider-key presence checked without printing the key.
- Recording uses bundled synthetic samples, loaded through **Try a sample → Sample CSV → Load sample CSV**. State that these are bundled samples. This avoids a file-dialog dependency and is allowed by the existing demo script.

## Two fresh live UI rehearsals

These used the real running Streamlit UI in the in-app browser and real Groq calls. They were not captured as the final demonstration. Downloaded JSON files are preserved under `tmp/video_preflight/`.

| Case | Exact input and question | Actual result |
| --- | --- | --- |
| A | `corrupted_outliers_corr.csv`; target None selected; `Do the numerical features contain suspicious values or relationships?` | 30 rows, 3 columns; `outlier_check` and `correlation_check`, both ok; 3 verified findings; total 18.9675s |
| B | `class_distribution_moderate.csv`; target `label`; `Is my target distribution a problem? Explain what the observed distribution means and suggest next steps.` | 100 rows, 3 columns; `class_imbalance_check` ok; negative 60, positive 40, ratio 1.5; 0 verified findings; total 13.8068s |

Original exports: `tmp/video_preflight/case_A_numeric_ui.json` and `case_B_moderate_ui.json`. Case A contains one outlier in each of `feature_x` and `feature_y`, plus Pearson correlation 1.0. Case B displays a model-written summary, cited interpretation and suggested next steps despite zero verified findings.

The numeric model narrative also proposes feature duplication/leakage and refers to the features as identical. These are not established by the verified correlation statistic. Narration must explicitly explain that perfect correlation means a perfect linear relationship, does not prove identical values or leakage, and that recommendations are proposed actions. The evidence validator is not a semantic proof of every model sentence.

Both recording takes must execute fresh model runs. Do not substitute these rehearsal exports or saved screenshots for live runs. Download the original JSON after each final take.

## Application verification

- Fresh regression run: `149 passed in 28.33s`.
- Fresh `pip check`: `No broken requirements found.`
- Sample A: 293 bytes, 30 rows, 3 columns (`feature_x`, `feature_y`, `feature_z`).
- Sample B: 2,115 bytes, 100 rows, 3 columns (`record_id`, `feature`, `label`); independently counted 60 negative and 40 positive labels.
- Existing architecture image, scenario matrix, verified benchmark summary and controlled-failure screenshot were located and checked for existence.
- Approximately 74.7 GB free disk space was available at preflight.

## Recorder and editing verification

Filmora's installed screen-recorder UI was inspected. It offers Area, Window and Full recording modes, microphone/system-audio controls, and a camera control. It is not the selected capture path; its editor license/watermark status was not needed for the final method.

Selected method: portable FFmpeg, kept within ignored temporary project storage. No system installation, PATH change or app-environment dependency change was made. The executable was extracted from the PyPI `imageio-ffmpeg==0.6.0` Windows wheel after comparing its SHA-256 with PyPI metadata. Manifest: `tmp/video_preflight/ffmpeg_manifest.json`. The included FFmpeg build reports version 7.1 and supports `gdigrab` and `libx264`.

- Recorder: Windows desktop capture through `gdigrab`, video-only input, `-an`, H.264 / yuv420p. Microphone and system audio are never acquired.
- Native desktop: 1920×1200. Capture at native resolution, then fit proportionally into 1920×1080 with side padding; do not stretch the picture.
- Retest capture requested 20 fps; final export normalizes to constant 30 fps. This duplicates frames where needed and does not claim 30 unique captured frames per second.
- FFmpeg can capture across window switches, trim processing waits, join segments, and export MP4 without adding a watermark.
- Capture only the dedicated code/app/evidence views. Leave credentials, personal datasets and unrelated windows out of the take.

### Test outcomes and retained attempts

The first 12-second capture verified encoding but missed the app switch because it occurred outside the captured interval. The first trim export also reported a non-exact average frame rate. Those attempts remain in `tmp/video_preflight/` and are not acceptance evidence.

A controlled retest started on the prepared code window and switched to the dedicated app four seconds later. Extracted frames at 1s and 9s were visually inspected and show the code and app respectively. A second editing test joins two two-second excerpts, one from each screen.

| Accepted output | Duration | Video | Audio tracks | Decode |
| --- | --- | --- | --- | --- |
| `capture_switch_retest_1080p.mp4` | 11.967s | 1920×1080, H.264, 30 fps | 0 | Full decode passed without errors |
| `edit_switch_retest_1080p.mp4` | 4.000s | 1920×1080, H.264, 30 fps | 0 | Full decode passed without errors |

MP4 track handlers were inspected directly: both contain only a `vide` track. Both have the `moov` atom before media data for fast-start playback. Exact metadata, file sizes and SHA-256 values are in `tmp/video_preflight/video_validation.json`. Reviewed frames: `retest_code.png` and `retest_app.png`.

## Recording execution after final go

1. Reconfirm the app, key-presence status, dedicated windows and available storage. Prepare architecture, benchmark and failure-evidence views; no new benchmark execution is needed.
2. Start a hidden video-only FFmpeg recorder. Use separate takes for the five required sections, keeping each complete live case with its own trace/report/export.
3. Hold the question before running, hold actual tool-choice explanations/trace, then scroll slowly through verified evidence, interpretation and next steps. Hold major explanatory screens long enough for voice-over.
4. Keep original captures and JSON exports. If the provider fails, retain that take, wait for the displayed allowance, and record a clean new take. Never transplant another run's findings into a live case.
5. Trim navigation and long processing waits. Label any shortened wait and any saved/pre-imported evidence explicitly. Fit the five sections to the 6:30 plan.
6. Export `submission/Phase3_CSV_Data_Quality_Demo.mp4` as a silent 1080p, 30 fps H.264 MP4 and create `submission/Phase3_Voiceover_Script.md` with timestamps matching the finished edit.
7. Inspect the edited video, fully decode it, verify 5–7 minute duration, no audio track, correct screen sequence, readability, and no credentials. Review narration against the final run evidence.

The silent MP4 is a base for the user's later voice-over. The narrated version still needs a final duration/audio/playback check after the voice-over is added. Instructor access and course upload are separate hand-in steps; neither was performed here.

## References for the recording method

- [FFmpeg Windows desktop capture documentation](https://ffmpeg.org/ffmpeg-devices.html#gdigrab)
- [ImageIO FFmpeg package used for the portable executable](https://pypi.org/project/imageio-ffmpeg/0.6.0/)

The larger direct Gyan download was stopped after the verified portable package became available. Its partial archive remains temporary and is not an executable used by this workflow.
