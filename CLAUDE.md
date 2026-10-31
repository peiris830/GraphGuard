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
- Stored in data/raw/elliptic_bitcoin_dataset/ and gitignored

## Project 2 notes (later)
Neo4j for multi-hop queries; spectral graph features first, a GNN only after a baseline exists; scoring engine = testable multi-hop mixing-pattern logic (not CRUD); FastAPI backend (Spring Boot only if the owner wants Java); React UI; Gephi export small and last; live blockchain ingestion optional and last.

## Ideas deliberately dropped or deferred
- KAN drift detector (research, not engineering)
- NexusMCP as a full project (borrow only a small MCP server over the final tables later)
- EdgePulse (borrow only the pre-aggregation/backpressure idea)

## Repo skeleton
```
graphguard/
├── data/raw/            # Elliptic CSVs in elliptic_bitcoin_dataset/ (gitignored)
├── data/processed/      # pipeline output (gitignored)
├── src/graphguard/      # loader, validation, integrity, quarantine, writer, pipeline
├── tests/
├── docs/                # data.md, architecture.md
├── pyproject.toml       # setuptools, src layout, deps pandas + pyarrow, dev extra with pytest, requires-python >=3.11
├── DECISIONS.md
├── LICENSE              # MIT
└── README.md
```
.gitignore: .venv/, __pycache__/, *.pyc, .pytest_cache/, *.egg-info/, data/raw/, data/processed/
Install with: `pip install -e ".[dev]"` inside an activated .venv (add `--use-feature=truststore` on this machine; see README troubleshooting).
Run the pipeline: `python -m graphguard.pipeline`. Run tests: `pytest`.

## Current status (update this at the end of each session)
- Repo: github.com/peiris830/GraphGuard, `main` always passes tests. Tag `v0.1.0-foundation` (Phase 0) is pushed. Python 3.12.4 venv.
- Phase 1 (local batch pipeline) is nearly done; only the failure drills and the tag remain. Merged: validation rule (accepts NumPy numbers), three CSV readers, four cross-file integrity checks, row quarantine with a 1% threshold, partitioned Parquet writer with safe reruns, the `python -m graphguard.pipeline` entry point (full real dataset in about 4 s, rerun-safe), and DuckDB queries in queries.py (step_summary, node_degrees; node_degrees is the baseline Spark must match in Phase 2). 109 tests.
- Real-data facts are in docs/data.md (no header on features, 157,205 `unknown` labels, 49 gap-free steps, no edge crosses a step, all integrity checks pass).
- OPEN ITEMS (do not defer without writing them here):
  1. "Break it and fix it" exercise for Phase 1: bad time step, running twice, edge to a missing txId, truncated file, killed run.
  2. Tag `v0.2.0-local-batch-pipeline` on main once item 1 is merged and tests pass (tags are pushed by name: `git push origin <tag>`).
  3. README status table and this section updated when Phase 1 closes.
- Docs branch `docs/readme-and-data-dictionary` adds README, docs/data.md, docs/architecture.md and LICENSE.
- Next after Phase 1: Phase 2, PySpark (joins, in/out degree per time step); `run_pipeline` will need a per-step parameter before Airflow in Phase 4.
