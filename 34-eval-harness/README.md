# Seat 34: Eval Harness

## Start here
- **Rules for people and coding agents:** [AGENTS.md](AGENTS.md)
- **What happened last, and what is next:** [docs/processed/project/status.md](docs/processed/project/status.md)
- **Plan and milestones:** [docs/processed/project/plan.md](docs/processed/project/plan.md). **Task board:** [board.md](docs/processed/project/board.md)
- **Wiki** (platform, access, evaluation design, decisions): [docs/processed/README.md](docs/processed/README.md)

**Run it:** `uv sync`, fill in `.env` (see `.env.example`), then
`uv run python scripts/run_local.py --instance both -- --suite suites/example --out runs/results.json`.
Runbook: [docs/processed/evaluation/how-to-run.md](docs/processed/evaluation/how-to-run.md). For other seats: [agent contract](docs/processed/evaluation/agent-contract.md).

*The sections below are the course brief, kept as given. Our checked view of access is kept in local platform notes; see [docs/processed/platform/README.md](docs/processed/platform/README.md).*

## Scope
Golden-task suites with verified-pass checks for the seat agents, a nightly regression run and a score history.

## First task
A 12-task suite for two existing seats, with verifiers, run end to end.

## Access
knowledgebase, agent tools, read access across modules

## Task format
See [TASK_FORMAT.md](TASK_FORMAT.md).

## Milestones
- 15 Nov 2026: first task delivered
- 30 Nov 2026: version 1, with a 12-task test suite
- 20 Dec 2026: integration run of all eight seats
- 31 Dec 2026: final

## Working rules
See the top-level README. Put your agent code, tests and notes in this folder; open a pull request for every change.
