# CSV Data Quality Triage Agent

An agentic LangChain application that helps users identify data-quality problems in CSV datasets before machine-learning model training.

The agent decides which diagnostics are relevant, invokes deterministic Pandas/NumPy-based tools, and returns a structured report with evidence and recommended next steps.

## Project Status

**Phase 2:** implementation in progress / partial working system.  
Target milestone: CSV upload → selective tool calls → visible trace → structured report.

## Core Features

- CSV upload through Streamlit
- compact dataset profiling
- natural-language questions
- selective LangChain tool calling
- deterministic data-quality diagnostics
- optional target-column selection
- visible tool-call trace
- structured JSON/Pydantic report
- deliberately corrupted test datasets

## Planned Diagnostic Tools

- dataset profile
- missing values
- duplicate rows
- constant / near-constant columns
- high-cardinality / identifier-like columns
- numeric outliers
- class imbalance
- suspicious numeric correlations
- optional dtype anomaly checks

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| UI | Streamlit |
| Agent framework | LangChain |
| Composition | LCEL |
| Prompting | ChatPromptTemplate / PromptTemplate |
| Agent tools | LangChain `@tool` / structured tools |
| Structured output | Pydantic + OutputParser |
| Data processing | Pandas, NumPy |
| ML utilities | scikit-learn where appropriate |
| LLM adapter | LangChain chat-model adapter; default proposed adapter: `langchain-mistralai` |
| Testing | pytest |
| Config | python-dotenv |
| Diagrams | Mermaid + committed PNG |
| Version control | Git/GitHub |

## Repository Structure

```text
csv-data-quality-agent/
├── app.py
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   └── context_builder.py
│   │
│   ├── diagnostics/
│   │   ├── __init__.py
│   │   ├── profile.py
│   │   ├── missing.py
│   │   ├── duplicates.py
│   │   ├── constants.py
│   │   ├── cardinality.py
│   │   ├── outliers.py
│   │   ├── imbalance.py
│   │   ├── correlation.py
│   │   └── dtype_anomalies.py
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── prompt.py
│   │   ├── tools.py
│   │   ├── factory.py
│   │   └── report_chain.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── triage_service.py
│   │   └── trace.py
│   │
│   └── ui/
│       ├── __init__.py
│       └── components.py
│
├── data/
│   ├── samples/
│   │   ├── clean_small.csv
│   │   ├── corrupted_missing_duplicates.csv
│   │   ├── corrupted_class_imbalance.csv
│   │   └── corrupted_outliers_corr.csv
│   └── expected/
│       ├── corrupted_missing_duplicates.json
│       ├── corrupted_class_imbalance.json
│       └── corrupted_outliers_corr.json
│
├── tests/
│   ├── unit/
│   │   ├── test_loader.py
│   │   ├── test_missing.py
│   │   ├── test_duplicates.py
│   │   ├── test_constants.py
│   │   ├── test_cardinality.py
│   │   ├── test_outliers.py
│   │   └── test_imbalance.py
│   └── integration/
│       ├── test_agent_tools.py
│       └── test_report_pipeline.py
│
└── docs/
    ├── PRD.md
    ├── IMPLEMENTATION_PLAN.md
    ├── ARCHITECTURE.md
    ├── DECISIONS.md
    ├── PHASE2_SUBMISSION_TEMPLATE.md
    └── assets/
        └── csv_agent_architecture.png
```

## Local Setup

### 1. Create environment

```bash
python -m venv .venv
```

Activate it using your OS-specific command.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Copy:

```bash
cp .env.example .env
```

Set the configured LLM provider API key and model name.

Example variables:

```env
LLM_PROVIDER=mistral
LLM_MODEL=<your-model-name>
MISTRAL_API_KEY=<your-key>
MAX_TOOL_CALLS=6
MAX_UPLOAD_MB=20
```

### 4. Run the app

```bash
streamlit run app.py
```

### 5. Run tests

```bash
pytest -q
```

## Demo Flow

1. Upload `data/samples/corrupted_missing_duplicates.csv`.
2. Review schema/profile.
3. Ask:
   - `Why could this dataset cause problems during model training?`
4. Observe which tools the agent selects.
5. Expand the tool trace.
6. Review the structured diagnosis.
7. Repeat with an imbalanced-target sample and select the target column.

## Agent Guardrails

- Do not fabricate numeric evidence.
- Use diagnostic tools for factual claims.
- Do not run all tools unless the user explicitly asks for a complete scan.
- Do not modify the dataset.
- Do not execute arbitrary model-generated Python.
- Do not run class-imbalance checks without a target.
- Surface tool failures explicitly.
- Respect the configured tool-call budget.

## Phase 2 Evidence

Before submission, commit:
- working repository link,
- progress notes,
- upload/profile screenshot,
- tool-trace screenshot,
- structured-report screenshot,
- at least one error-handling example.

Use `docs/PHASE2_SUBMISSION_TEMPLATE.md`.

## Documentation

- `docs/PRD.md` — product requirements and acceptance criteria
- `docs/IMPLEMENTATION_PLAN.md` — step-by-step build plan
- `docs/ARCHITECTURE.md` — logical architecture and sequence
- `docs/DECISIONS.md` — important technical decisions
- `docs/PHASE2_SUBMISSION_TEMPLATE.md` — submission-ready progress note template

## Scope

This project diagnoses CSV quality problems and recommends next steps. It does **not** automatically clean the file or train a machine-learning model in Phase 2.
