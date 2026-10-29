# CLAUDE.md: GraphGuard (read this first)

## What this project is
A data engineering portfolio project, built as a learning exercise. The goal is a portfolio that shows data engineering skill plus software engineering rigor, using a complex, messy dataset (Elliptic Bitcoin transactions). Target cloud: AWS (GCP free tier is acceptable).

The owner is a CS graduate, a beginner in data engineering and AWS, working on Windows with PowerShell. Python, Git and Docker are installed. Assume about 10 study hours per week.

## Your role: tutor first, pair-programmer second
- The owner's main aim is to understand the hows and whys and the architecture of what is being built, not to master syntax. Lead with the design reasoning: what problem this component solves, where it sits in the overall system, what the alternatives were, and what breaks if it is removed. Keep syntax explanations short.
- When a new component is introduced, show where it fits in the architecture (data flow, inputs, outputs, failure modes).
- Explain the problem a step solves before writing code, in plain terms.
- The owner may ask Claude to write code or tests; do so when asked, then explain the design reasoning behind it. Otherwise let the owner write the first attempt (tests first where sensible), then review it. Do NOT write core transformation or validation logic unless asked.
- You may write boilerplate (Docker, config, repetitive setup) but explain it.
- After each phase, suggest a deliberate "break it and fix it" exercise (bad data, duplicate run, killed container).
- The owner adds a short entry to DECISIONS.md for each real decision (what was chosen and why).
- Add a tool only if we can say in one sentence what problem it solves.
- Set a billing alert before touching any cloud service.
- Every phase must run from a clean checkout and have at least one test.
- No Makefile on Windows for now: use plain commands until we containerize, then `docker compose up` is the single entry point.

## Git hygiene (keep the repo portfolio-quality)
- Small, focused commits: one logical change each, with tests and the code they cover together. The history should read as a story of the project.
- Commit messages must be meaningful, never a bare one-liner like "update" or "fix stuff". Format: imperative subject (about 50 chars), blank line, then a body of a few lines covering what changed, why it was needed, and any trade-off or edge case a future reader would wonder about. Wrap the body at about 72 chars. Optionally Conventional Commits prefixes (`feat:`, `fix:`, `test:`, `docs:`, `chore:`), used consistently.
- Branching: `main` always passes tests and runs from a clean checkout. Work on short-lived branches named `type/short-description` (`feat/csv-loader`, `fix/duplicate-rows-on-rerun`, `docs/readme`), not by phase number, and merge when done, ideally via a pull request on GitHub even though the owner is solo.
- Tag the end of each phase with an annotated tag named `vMAJOR.MINOR.PATCH-short-description` (`v0.1.0-foundation`, `v0.2.0-local-batch-pipeline`, `v0.3.0-spark-transforms`, `v0.4.0-cloud-infrastructure`, `v0.5.0-airflow-orchestration`, `v0.6.0-kafka-streaming`, `v0.7.0-serving-and-drift`, `v1.0.0-core-release`). Fixes after a tag bump the patch number. Tag only merged commits on `main` whose tests pass, give each tag a message saying what shipped, and never move or delete a pushed tag. Milestones only, not every commit.
- Never commit: raw data (`data/raw/` is gitignored), secrets, AWS credentials, `.env` files, Terraform state (`*.tfstate`, `.terraform/`), or large generated files. Check `git status` and `git diff --staged` before each commit.
- Keep `.gitignore` current as new tools arrive (Terraform, Docker, Airflow logs, Spark artifacts).
- Commit `DECISIONS.md` and README updates in the same commit or branch as the change they describe.
- The owner approves every commit and every push. Claude never runs `git commit` or `git push` on its own: it proposes the files to stage and the commit message, and the owner approves (or runs the command personally). As tutor, explain what each git command does, since the owner is learning good habits.
- No `Co-Authored-By` or "Generated with Claude" trailers in commit messages or PR descriptions. The owner is the sole author in the history.
- Never rewrite published history (no force-push on `main`).

## Roadmap
| # | Project | Covers |
|---|---|---|
| 1 | GraphGuard Core (name still open) | Batch pipeline, Spark, cloud + Terraform, Airflow, Kafka streaming, minimal FastAPI/Streamlit, drift check (~4 months) |
| 2 | GraphGuard Investigator (name still open; "GraphGuard-Extended" is the alternative) | Neo4j, graph features, scoring engine with real business logic, backend API, React investigation UI, Gephi export (~3-4 months) |
| 3 | PulseShift (trimmed) | Streaming-first with replayed historical crypto data, Kafka, windowed job, lakehouse table; Python instead of Go; no KAN (decide later) |

Naming: the owner dislikes "lite" (it implies a bigger plan was dropped). Core = data platform; Investigator = analyst-facing layer on top.

## Project 1 phases
0. Setup (wk 1): repo skeleton, venv, pyproject, first pytest test
1. Local batch pipeline (wk 2-3): load the 3 Elliptic CSVs, validate, write partitioned Parquet, query with DuckDB
2. Spark (wk 4-5): redo heavy transforms in PySpark (joins, in/out degree per time step)
3. Cloud + Terraform (wk 6-8): S3, IAM roles, Athena tables via Terraform (GCS + BigQuery as alternative)
4. Orchestration (wk 9-10): Airflow DAG, one run per time step, idempotent, data quality checks
5. Streaming (wk 11-13): replay time steps into Kafka/Redpanda, consumer computing rolling features
6. Serving + drift (wk 14-15): FastAPI endpoint, one Streamlit page, KS-test drift check showing the shift after time step 43
7. Polish (wk 16): architecture diagram, benchmark numbers, CI running tests, README, DECISIONS.md

Stopping after Phase 4 is already a solid portfolio piece; Phase 5 makes it stand out.

## Dataset: Elliptic Bitcoin
- About 200k transactions across 49 time steps (numbered 1-49), graph-shaped and messy
- Files: elliptic_txs_features.csv, elliptic_txs_classes.csv, elliptic_txs_edgelist.csv
- Known real-world drift: model performance collapses after time step 43
- Stored in data/raw/ and gitignored

## Project 2 notes (later)
Neo4j for multi-hop queries; spectral graph features first, a GNN only after a baseline exists; scoring engine = testable multi-hop mixing-pattern logic (not CRUD); FastAPI backend (Spring Boot only if the owner wants Java); React UI; Gephi export small and last; live blockchain ingestion optional and last.

## Ideas deliberately dropped or deferred
- KAN drift detector (research, not engineering)
- NexusMCP as a full project (borrow only a small MCP server over the final tables later)
- EdgePulse (borrow only the pre-aggregation/backpressure idea)

## Repo skeleton
```
graphguard/
├── data/raw/            # Elliptic CSVs (gitignored)
├── src/graphguard/      # pipeline code
├── tests/
├── pyproject.toml       # setuptools, src layout, dev extra with pytest, requires-python >=3.11
├── DECISIONS.md
└── README.md
```
.gitignore: .venv/, __pycache__/, *.pyc, .pytest_cache/, *.egg-info/, data/raw/
Install with: `pip install -e ".[dev]"` inside an activated .venv.

## Current status (update this at the end of each session)
- Phase 0 is done apart from a fuller README and the phase tag. The repo is on GitHub (peiris830/GraphGuard); PR #1 (time step validation) is merged. Python 3.12.4 venv; pip needs `--use-feature=truststore` on this machine because of an HTTPS certificate interception issue.
- Phase 1 in progress on branch `feat/csv-loader` (PR not yet opened or merged). Done: `is_valid_time_step` in validation.py, `read_features` in loader.py, 28 passing tests, DECISIONS.md entries for validation, src layout, pandas and explicit columns.
- Dataset is in `data/raw/elliptic_bitcoin_dataset/` (one folder deeper than the skeleton shows). Facts found: features file has no header, 203,769 rows, 167 columns (tx_id, time_step, 165 features), time steps 1-49 with no gaps, no duplicate tx_ids, no nulls. Classes: 4,545 illicit (1), 42,019 licit (2), 157,205 `unknown`. Edgelist: 234,355 edges.
- Agreed Phase 1 design: rows that fail validation go to a quarantine file with a reason, and the run fails only if rejects exceed a threshold (about 1%); `unknown` class becomes null with the original value kept; output is Parquet partitioned by time step in gitignored `data/processed/`; check that every edge `txId` exists in the features file.
- Next: classes reader, edges reader, row-level validation with quarantine, partitioned Parquet output, cross-file integrity check, DuckDB queries, then a "break it and fix it" exercise (bad time step, running twice, edge to a missing txId, truncated file). Each piece is its own small commit, with the DECISIONS.md entry alongside.
