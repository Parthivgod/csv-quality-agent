# Implementation Notes

## Source documents and priority

The official Lab 9 Activity 2 brief, the submitted Phase 1 PDF, and the supplied PRD, decisions, architecture, plan, and README were reviewed before implementation. The original brief and proposal are retained in `docs/source/`.

The official brief says groups should have three members; the submitted Phase 1 proposal lists Parthiv Godrihal (I024) and Nilay Jain (I029). This repository preserves the submitted responsibility split because the implementation cannot resolve enrollment. The team should confirm the roster with the instructor before submission.

The supplied folder had no architecture PNG even though the Markdown documents referenced one. `scripts/generate_architecture.py` produced `docs/assets/csv_agent_architecture.png` from the implemented flow.

## Decisions made during implementation

- Use LangChain 1.x `create_agent` and per-request `StructuredTool` closures. This avoids global mutable DataFrame state and avoids obsolete `AgentExecutor` examples.
- Use two model adapters in `src/agent/factory.py`. Mistral is the documented default; OpenAI is an optional replacement. Credentials stay in environment variables.
- Keep report generation separate from investigation. `PydanticOutputParser` checks shape; an additional check requires each report issue to match an exact deterministic tool finding. One retry handles malformed or unsupported output.
- Count diagnostic executions in a lock-protected trace collector because an agent may request parallel tools. Repeated or over-budget calls return a skipped observation.
- Use Pandas/NumPy for the current checks. scikit-learn is unnecessary for these methods, so it is not installed solely to meet a stack label.
- Reject header-only CSVs, binary files, oversize files, and inconsistent CSV rows. Pandas numbers repeated header names; the app warns about possible duplicates.
- Use a local scripted chat model in integration tests. It proves the LangChain graph and selective trace wiring, not live provider behavior.

## Problems encountered and solutions

- `langchain-mistralai` was absent from the local Python environment. It was added to `requirements.txt` and installed for import verification. The application still needs a user API key for a live call.
- A first `StructuredTool` wrapper exposed unintended `args/config/kwargs` fields. It was replaced with an explicit empty Pydantic argument schema; the model now sees `{}` for each tool.
- The source architecture image was missing. A matching diagram was generated and checked visually.
- In the clean virtual environment, Streamlit 1.64 resolved `AppTest.from_file()` relative to its calling test file. The smoke test now passes an absolute path to `app.py`.

## Validation boundary

At the initial validation point, the fresh `.venv` installed `requirements.txt` successfully, `pip check` found no broken requirements, 19 tests passed, compilation passed, and Streamlit returned HTTP 200 on port 8503. Local tests covered deterministic diagnostics, CSV errors, tool wrappers, two successful agent paths, a numeric path, missing-target handling, parser repair, and the initial Streamlit render. No live Mistral/OpenAI request was run because neither provider key was configured. Subsequent Groq validation is recorded below and in `LIVE_GROQ_VALIDATION.md`.

## Provider update

At the user's request, Groq's `openai/gpt-oss-120b` became the default through `langchain-groq`. The key belongs in the Git-ignored root `.env` as `GROQ_API_KEY`. The model ID was verified against Groq's model documentation, and LangChain documents `ChatGroq` with local tool calling support. Earlier Mistral/OpenAI options remain available. A live Groq request still requires the user's key; local construction and tests do not establish live behavior.

References: [Groq model ID](https://console.groq.com/docs/model/openai/gpt-oss-120b), [LangChain ChatGroq setup](https://docs.langchain.com/oss/python/integrations/chat/groq).

## Live-run repairs

The user first placed the Groq key in tracked `.env.example`. It was moved to the ignored `.env` without printing it, and `.env.example` was cleared before committing any new work.

The first broad Groq run exposed a noisy high-cardinality rule for continuous numeric fields. The rule now tests categorical fields and identifier-named numeric fields. A unit test covers the distinction. The first missing-target run gave a generic limitation; report validation now adds an explicit target-selection instruction. Both cases were rerun live. See `LIVE_GROQ_VALIDATION.md` for the observed results.

## Submission screenshot capture

Computer Use captured the running Streamlit app with the already-loaded `corrupted_outliers_corr.csv` fixture. A fresh UI question selected only `outlier_check` and `correlation_check` and produced the expected evidence-grounded report. Four unedited screenshots are stored in `docs/screenshots/`, and `PHASE2_SUBMISSION_TEMPLATE.md` links and captions them. The browser error-handling and target-specific examples remain uncaptured. The repository was later connected to `https://github.com/Parthivgod/csv-quality-agent`.
