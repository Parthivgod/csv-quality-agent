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

The fresh `.venv` installed `requirements.txt` successfully, `pip check` found no broken requirements, 19 tests passed, compilation passed, and Streamlit returned HTTP 200 on port 8503. Local tests cover deterministic diagnostics, CSV errors, tool wrappers, two successful agent paths, a numeric path, missing-target handling, parser repair, and the initial Streamlit render. No live Mistral/OpenAI request was run because neither provider key is configured. Live provider screenshots and a public GitHub link remain submission tasks.
