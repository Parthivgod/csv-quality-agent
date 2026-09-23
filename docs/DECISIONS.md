# Technical Decisions
## CSV Data Quality Triage Agent

This file records implementation decisions so the team and a coding agent do not repeatedly reopen settled architecture questions.

---

## ADR-001 — Use Streamlit for the application shell

**Status:** Accepted

**Decision:** Use Streamlit rather than React/FastAPI for Phase 2 and Phase 3.

**Reasoning**
- Phase 1 already commits to Streamlit integration.
- The activity is evaluated on LangChain integration and working implementation, not frontend complexity.
- Streamlit allows upload, forms, expandable traces, tables and JSON views quickly.

**Consequence**
- Faster academic delivery.
- UI is sufficient for a 5–7 minute demo.
- Production-grade frontend separation is out of scope.

---

## ADR-002 — Keep diagnostics deterministic

**Status:** Accepted

**Decision:** Pandas/NumPy/sklearn-style functions compute all statistics. The LLM must not estimate dataset metrics from raw text.

**Reasoning**
- reproducible,
- testable,
- easy to validate against known corrupted datasets,
- reduces hallucination.

---

## ADR-003 — LLM is an orchestrator, not a code executor

**Status:** Accepted

**Decision:** Expose only allowlisted diagnostic tools. Do not provide a generic Python REPL or arbitrary execution tool.

**Reasoning**
- safer,
- easier to test,
- ensures the application demonstrates intentional tool design.

---

## ADR-004 — Separate investigation from final report formatting

**Status:** Accepted

**Decision:** Use:
1. an agent stage to call tools,
2. a reporting LCEL stage to convert observations into a structured report,
3. a Pydantic OutputParser for validation.

**Reasoning**
- cleaner than forcing the agent to both investigate and perfectly format final JSON,
- easier parser recovery,
- easier unit/integration testing.

---

## ADR-005 — Target column is explicit

**Status:** Accepted

**Decision:** User selects an optional target column in Streamlit.

**Reasoning**
- class imbalance is target-dependent,
- guessing target columns is unreliable,
- makes evaluation deterministic.

---

## ADR-006 — Provider adapter remains swappable

**Status:** Accepted

**Decision:** Put model construction in `src/agent/factory.py`. Use environment configuration. A practical default adapter may be `ChatMistralAI`, but application logic must not depend on one provider.

**Consequence**
- the same repo can be demonstrated with a different LangChain-supported chat model if API access changes.

---

## ADR-007 — Do not send the whole CSV to the LLM

**Status:** Accepted

**Decision:** Send schema/aggregates/tool results only.

**Reasoning**
- privacy,
- token efficiency,
- avoids the model attempting unsupported calculations,
- keeps deterministic tools authoritative.

---

## ADR-008 — Tool descriptions control selection behavior

**Status:** Accepted

**Decision:** Each tool description must state:
- when it should be used,
- when it should not be used,
- what it returns.

**Reasoning**
Good tool metadata is a major part of getting selective agent behavior.

---

## ADR-009 — Tool-call budget

**Status:** Accepted

**Decision:** Configure a maximum of approximately 6 diagnostic calls per request for Phase 2.

**Reasoning**
- prevents loops,
- keeps response time manageable,
- reinforces selective triage rather than blanket profiling.

---

## ADR-010 — No automatic cleaning in Phase 2

**Status:** Accepted

**Decision:** Recommendations are advisory. The app does not mutate and re-export the dataset.

**Reasoning**
- avoids scope creep,
- keeps the project centered on tool-augmented diagnosis,
- simplifies validation.

---

## ADR-011 — Ground-truth fixtures

**Status:** Accepted

**Decision:** Create deliberately corrupted CSVs plus expected-issues JSON manifests.

**Reasoning**
This supports the Phase 1 evaluation promise and provides direct evidence for testing and final reporting.

---

## ADR-012 — Observable trace, not chain-of-thought

**Status:** Accepted

**Decision:** Display tool names, arguments, statuses and concise outputs. Do not expose hidden model reasoning.

**Reasoning**
The evaluator needs proof of tool interaction; internal reasoning is unnecessary.

---

## ADR-013 — Architecture favors pure functions

**Status:** Accepted

**Decision:** Diagnostic logic lives in pure-ish functions independent of Streamlit and LangChain, then gets wrapped.

**Reasoning**
- unit testing,
- reuse,
- less framework coupling,
- easier debugging.

---

## ADR-014 — Basic severity rules are configurable

**Status:** Accepted

**Decision:** Use simple thresholds for initial severity labels, but isolate them from calculation logic.

**Reasoning**
Severity is context-dependent. We should not hard-code a universal scientific claim into each detector.

---

## ADR-015 — Use LangChain 1.x create_agent with per-request tool closures

**Status:** Accepted in Phase 2 implementation

The current LangChain API builds the agent graph with `create_agent`. Each tool closure holds only the active request's DataFrame. This keeps sessions separate and avoids placing raw data in tool arguments or global mutable state.

---

## ADR-016 — Validate report findings against tool observations

**Status:** Accepted in Phase 2 implementation

Pydantic checks the report structure. The service additionally checks that every issue, severity, column, evidence, impact, and recommendation matches a finding returned by the named source tool. This is stricter than JSON parsing alone and prevents unsupported numeric claims in the final report.

---

## ADR-017 — Groq GPT OSS 120B as default model

**Status:** Accepted after user request

Set `LLM_PROVIDER=groq`, `LLM_MODEL=openai/gpt-oss-120b`, and use `GROQ_API_KEY` from the root `.env`. The provider factory preserves the earlier Mistral and OpenAI adapters. The diagnostics, tool trace, and report validation do not depend on the chosen provider.
