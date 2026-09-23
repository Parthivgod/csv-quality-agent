# Phase 2 Implementation Plan
## CSV Data Quality Triage Agent

This plan is optimized for the Lab 9 Phase 2 requirement: show a GitHub/Colab link, brief progress notes, and screenshot/output of a partially working system, while building directly toward the final Phase 3 submission.

---

## 1. Phase 2 Strategy

Do not try to finish every possible diagnostic before obtaining an end-to-end working vertical slice.

Build in this order:

**CSV upload → deterministic tools → LangChain tool wrapping → agent selection → structured report → Streamlit trace → tests/evidence**

The first milestone should be a minimal agent that can load a CSV and selectively call 3–4 tools. Additional diagnostics can then be added without changing the architecture.

---

## 2. Work Breakdown

### Milestone A — Repository and environment
**Goal:** project boots cleanly.

Tasks:
- create repository,
- add `.gitignore`,
- add `.env.example`,
- create `requirements.txt`,
- create `src/`, `tests/`, `data/`, `docs/`,
- add a minimal `app.py`,
- configure model provider through environment variables,
- verify `streamlit run app.py`.

**Done when:** Streamlit page launches and shows project title.

---

### Milestone B — CSV ingestion and session state
**Goal:** valid CSV becomes a reusable in-memory DataFrame.

Tasks:
- implement safe CSV loader,
- validate extension/content,
- catch parser/encoding errors,
- reject empty dataset,
- display rows, columns and preview,
- store DataFrame in `st.session_state`,
- add optional target-column selector.

Recommended loader behavior:
1. try UTF-8,
2. optionally fall back to a second encoding,
3. return a typed result object rather than throwing raw exceptions to the UI.

**Done when:** a sample CSV loads and metadata appears.

---

### Milestone C — Deterministic diagnostics
**Goal:** tools are correct before any LLM is introduced.

Implement in this order:
1. `dataset_profile`
2. `missing_values_check`
3. `duplicate_rows_check`
4. `constant_columns_check`
5. `high_cardinality_check`
6. `outlier_check`
7. `class_imbalance_check`
8. `correlation_check`

For every tool:
- write pure Python/Pandas logic,
- make the return value JSON-serializable,
- add one unit test,
- only then wrap it as a LangChain tool.

**Done when:** running the Python functions directly produces correct outputs on fixtures.

---

### Milestone D — Corrupted evaluation fixtures
**Goal:** create known ground truth for screenshots and tests.

Create small deterministic datasets:

#### `corrupted_missing_duplicates.csv`
Contains:
- missing values in selected columns,
- repeated rows,
- one constant column.

#### `corrupted_class_imbalance.csv`
Contains:
- target distribution such as 90/10,
- numeric features,
- a high-cardinality identifier column.

#### `corrupted_outliers_corr.csv`
Contains:
- obvious numeric outliers,
- two strongly correlated numeric columns.

Also keep:
- `clean_small.csv`.

For each file, create a small expected-issues manifest in JSON.

**Done when:** unit tests can compare detector outputs with known injected problems.

---

### Milestone E — LangChain tool wrappers
**Goal:** agent can discover tools through clean descriptions.

Tasks:
- use `@tool` or `StructuredTool`,
- keep descriptions very explicit about when a tool should/should not be used,
- pass a dataset/session identifier or use a controlled runtime context rather than serializing the whole DataFrame into the tool call,
- normalize tool output to concise JSON.

Example description pattern:

> “Use this tool when the user asks about missing data or when the dataset profile suggests nulls. Returns missing counts and percentages by column.”

**Done when:** tools appear in the agent tool registry and can be manually invoked.

---

### Milestone F — Prompt and agent
**Goal:** selective, constrained tool calling.

System instructions should include:
- You are a CSV data-quality triage agent.
- Use tools for factual/statistical claims.
- Never invent columns, counts or percentages.
- Do not run every tool by default.
- Prefer the smallest relevant set of tools.
- Do not call target-dependent tools without a target.
- Do not modify the dataset.
- If a tool errors, report that limitation and continue when possible.
- Maximum recommended diagnostic calls: 6.

Prompt variables:
- `user_query`
- `dataset_context`
- `target_column`
- `tool_names`
- `format_instructions`
- `agent_scratchpad` or equivalent required by the selected agent API.

**Done when:** the LLM chooses different tools for different queries.

---

### Milestone G — Structured output pipeline
**Goal:** stable report object.

Tasks:
- define Pydantic models:
  - `Issue`,
  - `DataQualityReport`,
- configure `PydanticOutputParser`,
- add parser formatting instructions to the final report prompt,
- add one repair/fallback path if the model returns invalid JSON.

Recommended pattern:
1. agent gathers observations,
2. reporting LCEL chain receives user query + tool transcript,
3. report chain emits parser-compatible structured output.

This separates:
- **investigation** from
- **final report formatting**.

**Done when:** successful runs create a validated `DataQualityReport`.

---

### Milestone H — Streamlit trace and report UI
**Goal:** produce Phase 2-visible evidence.

Main UI sections:
1. CSV upload
2. data preview
3. target selector
4. user query
5. run button
6. tool trace
7. structured issues table/cards
8. raw JSON expander

Trace events should record:
- sequence number,
- tool name,
- arguments,
- status,
- concise observation.

**Done when:** screenshot clearly proves the LLM called a diagnostic tool.

---

### Milestone I — Phase 2 validation
**Goal:** collect submission evidence.

Run at least these scenarios:

#### Scenario 1
Dataset: `corrupted_missing_duplicates.csv`  
Question: “Why could this dataset cause training problems?”  
Expected: profile + missing/duplicate/constant-related checks.

#### Scenario 2
Dataset: `corrupted_class_imbalance.csv`  
Target: `label`  
Question: “Is my target distribution a problem?”  
Expected: class imbalance check; high-cardinality tool may be called only if relevant.

#### Scenario 3
Invalid input:
- malformed/empty CSV,
- or ask for class imbalance without selecting target.

Expected: graceful error/limitation.

Capture:
- app upload/profile screenshot,
- tool trace screenshot,
- final report screenshot,
- terminal/test output screenshot if useful.

---

## 3. Recommended Implementation Sequence for Two Team Members

### Parthiv — Agent, LangChain & App Integration
1. repository bootstrap,
2. model factory + environment config,
3. PromptTemplate,
4. LangChain tool registry integration,
5. agent executor,
6. LCEL reporting chain,
7. Pydantic output parser,
8. Streamlit page,
9. tool-trace rendering,
10. integration test with one corrupted fixture.

### Nilay — Diagnostics, Evaluation & Testing
1. fixture CSVs,
2. pure diagnostic functions,
3. unit tests per diagnostic,
4. expected-issue manifests,
5. scenario matrix,
6. malformed input tests,
7. verify agent findings against ground truth,
8. screenshots / evaluation evidence.

### Integration checkpoints
Do not wait until all tools are finished.

Checkpoint 1:
- loader + 2 tools + basic UI.

Checkpoint 2:
- 4+ tools + agent + visible trace.

Checkpoint 3:
- structured parser + 2 fixture scenarios.

---

## 4. Priority Matrix

### P0 — Required for Phase 2 evidence
- repository structure,
- Streamlit upload,
- data profile,
- 4 deterministic tools,
- tool-wrapped LangChain agent,
- visible tool trace,
- structured final output,
- one corrupted dataset,
- screenshot.

### P1 — Strongly recommended before submission
- 6–8 tools,
- target selector,
- unit tests,
- second corrupted dataset,
- error handling,
- progress note.

### P2 — Can continue into Phase 3
- richer severity calibration,
- correlation/leakage heuristics,
- response evaluation table,
- polished UI,
- full test matrix,
- demo-video script,
- technical report.

---

## 5. Testing Plan

### Unit tests
Each diagnostic function should have:
- positive case,
- clean/no-issue case,
- edge case when relevant.

### Integration tests
Test:
- DataFrame → agent tool → observation,
- tool transcript → report parser,
- invalid target,
- tool exception fallback.

### Manual acceptance tests
At least five scenarios should eventually be documented for Phase 3:

| ID | Scenario | Expected agent behavior |
|---|---|---|
| T1 | Missing + duplicates | Call relevant missing/duplicate checks |
| T2 | Imbalanced target | Call class imbalance tool only with target |
| T3 | Outliers | Call outlier tool for numeric columns |
| T4 | ID/constant features | Call cardinality/constant checks |
| T5 | Tool/input failure | Surface error and produce bounded response |

---

## 6. Evidence to Commit

Recommended:
- `docs/screenshots/01_upload_profile.png`
- `docs/screenshots/02_tool_trace.png`
- `docs/screenshots/03_structured_report.png`
- `docs/screenshots/03b_correlation_finding.png`
- `docs/screenshots/04_error_handling.png`
- `docs/screenshots/05_selective_target.png`
- `docs/screenshots/06_class_report.png` (optional)
- `docs/PHASE2_PROGRESS.md`

Also commit:
- sample fixture CSVs,
- test results,
- architecture diagram.

---

## 7. Risks and Mitigations

### Risk: Agent calls all tools
Mitigation:
- explicit prompt,
- specific tool descriptions,
- max-call budget,
- test with narrowly phrased questions.

### Risk: LLM invents values
Mitigation:
- factual claims must reference tool observations,
- separate investigation and report formatting,
- Pydantic schema,
- no raw CSV reasoning in the prompt.

### Risk: LangChain version/API mismatch
Mitigation:
- pin/bound dependency versions,
- isolate agent creation in `src/agent/factory.py`,
- avoid spreading framework-specific imports across the project.

### Risk: Output parser failures
Mitigation:
- strong format instructions,
- one repair retry,
- raw text fallback stored for debugging.

### Risk: Tool errors crash the UI
Mitigation:
- wrap each tool call,
- return structured error objects,
- trace failures visibly.

### Risk: Deadline pressure
Mitigation:
- vertical slice first,
- P0/P1/P2 prioritization,
- no cloud deployment in Phase 2.

---

## 8. Phase 2 Submission Checklist

- [x] GitHub repository URL
- [x] README with setup/run steps
- [x] current architecture diagram
- [x] brief progress notes
- [x] screenshot of uploaded dataset
- [x] screenshot of agent tool trace
- [x] screenshot/output of structured report
- [x] at least one corrupted fixture committed
- [x] basic tests passing
- [x] known limitations listed

---

## 9. Handoff to Phase 3

After Phase 2 feedback:
1. incorporate instructor feedback,
2. finish remaining tools,
3. run 5+ documented scenarios,
4. intentionally capture one tool failure/unexpected response,
5. refine limitations/improvements,
6. finalize sample inputs/outputs,
7. record demo video,
8. write technical report,
9. add contribution statement.
