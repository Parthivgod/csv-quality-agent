# Voice-over for the silent demonstration

Target edit: 6 minutes 30 seconds. Record your own narration against the timestamps below. The app footage comes from two actual fresh Groq runs on 1 October 2026; navigation and waiting are trimmed. Bundled synthetic CSVs are used. Saved benchmark and controlled-failure evidence is labeled on screen.

## 0:00–0:45 — Purpose and input

Our application helps investigate CSV data before model training. The user loads a CSV and asks a data-quality question. Instead of running every check automatically, an agent chooses the relevant diagnostics. Local tools calculate statistics, and the report separates verified findings from model interpretation and suggestions. It can investigate missing values, duplicates, unusual numerical values, relationships between features and target imbalance. Here I use the bundled synthetic samples, so the inputs are reproducible. The application helps decide what to review; it does not automatically clean data or train a model.

## 0:45–1:15 — Architecture

The upload is copied and validated, with a hash retained for provenance. Small files use Pandas; larger files use DuckDB and a local Parquet dataset. The agent receives the question, schema and aggregate observations, while raw rows stay local. That reduces data transfer, although schema and aggregates can still be sensitive. Selected diagnostics return evidence and coverage through the visible tool trace, followed by the structured report.

## 1:15–1:35 — Prompt source

This is the actual system prompt built with ChatPromptTemplate. It requires tool evidence for statistical claims, asks the agent to choose a small relevant set of checks, and requires a brief public explanation of each tool choice. It also states that failed or skipped checks do not establish that the data is clean.

## 1:35–1:50 — Agent constructor

The constructor renders the prompt with dataset context, the selected target and available tool descriptions. LangChain's create_agent connects that prompt to the provider model and the supplied diagnostics. Today's runs use Groq with GPT OSS 120B.

## 1:50–2:00 — Tool wrappers

StructuredTool wraps the local diagnostics with a defined argument schema. Results include status, evidence, timing and coverage, and the trace preserves them for inspection.

## 2:00–2:15 — Report chain

The LCEL chain formats the observed results. A Pydantic output parser validates the report structure, and additional validation checks its evidence against actual observations. There is one repair attempt. These are four integrated LangChain components: prompt template, agent and structured tools, LCEL, and the output parser.

## 2:15–3:25 — Fresh numerical case

For the first case, I load the numerical sample with thirty rows and three columns. I ask whether the numerical features contain suspicious values or relationships. The agent chooses the outlier and correlation checks, and both complete successfully. The local evidence identifies one IQR outlier in feature x and one in feature y: each is one out of thirty values, about three point three percent. It also finds a Pearson correlation of one between those two features. The structured diagnosis contains three verified findings with their source tools and recommended review actions. A perfect correlation suggests a relationship worth investigating; it does not prove identical values or data leakage. The next steps remain proposals, and the original trace and report are saved in the JSON export.

## 3:25–4:30 — Fresh selected-target case

For the second case, I load the moderate-distribution sample with one hundred rows and select label as the target. I ask whether the distribution is a problem and request an explanation and next steps. The agent chooses the class-imbalance check. It finds sixty negative labels and forty positive labels, a majority-to-minority ratio of one point five to one. That is below the medium warning threshold of three to one, so there are zero verified issue findings from this check. The model still explains the modest skew and suggests stratified splits and class-aware evaluation. Resampling or class weighting would need evidence from later model evaluation; the app has not performed either. This demonstrates a useful response even when the selected diagnostic does not raise a warning.

## 4:30–5:10 — Scaling challenge

These are saved benchmark measurements, not a benchmark running during this video. Scaling required more than raising an upload limit. The implementation uses DuckDB, Parquet, cached metadata, bounded checks and controlled background jobs. The original sixty-second deadline rejected six large imports. We retained those failures and explicitly revised the release allowance to one hundred and twenty seconds. Five different 250 MiB profiles passed the required gates. The maximum successful import times shown here are measurements from the documented local setup, not universal performance promises.

## 5:10–5:30 — Controlled failure evidence

This saved screenshot comes from a deliberate exception injected into the duplicate diagnostic during an earlier live Groq run. It tests the full failure path: the trace shows the error, and the report discloses the incomplete check without inventing a duplicate finding. This is separate from today's two successful runs.

## 5:30–5:50 — Evaluation

The fresh regression suite passed all one hundred and forty-nine tests, and the dependency check found no broken requirements. Nine saved scenarios cover normal inputs, missing targets, invalid files and controlled failure. Scripted tests, today's two live model runs and the size benchmarks provide different forms of evidence. Automated tests alone do not establish model interpretation quality.

## 5:50–6:30 — Limits and improvements

Results apply only to selected checks and their stated coverage. A report with no flagged issues does not certify a clean dataset. Correlation does not confirm leakage, and model advice still needs human review. Wide checks have explicit limits: duplicate checks accept at most fifty columns, and numerical checks at most twenty. The upload buffer still uses memory, even with a disk-backed backend. Future work includes streaming uploads, more CSV shapes, concurrent-user benchmarks and broader evaluation of statistical correctness and narrative quality. The aim is an inspectable investigation, with evidence and limitations kept visible.
