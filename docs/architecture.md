# Architecture

## Core flow

The harness executes runs in three fixed roles:

1. `planner`: expands the task into an execution plan
2. `implementer`: runs web, browser, Codex CLI code execution, test, and workspace actions
3. `reviewer`: independently reviews only execution evidence and handoff state

Each run writes artifacts into `.runs/<run_id>/` and works inside `.worktrees/<run_id>/`.

## Main modules

- `src/harness/orchestrator/runner.py`: run lifecycle, checkpointing, pause/resume, review
- `src/harness/agents/`: provider adapter plus planner/implementer/reviewer roles
- `src/harness/tools/`: shell, fs, git, tests, web fetch, web search, browser, Codex CLI code execution
- `src/harness/memory/store.py`: per-run artifacts and SQLite run index
- `src/harness/tasks/`: tracked task lifecycle and repo memory integration
- `src/harness/codex/bootstrap.py`: local Codex project bootstrap
- `src/harness/dashboard/app.py`: local read-only dashboard
- `src/harness/observability/`: JSON logs, Prometheus metrics, OTLP traces

## Durability model

- `run_manifest.json` stores state, budget counters, active phase, and artifact pointers
- `handoff.md` stores resumable context after every checkpoint
- `events.jsonl` stores structured event history
- `result.json` stores planner, implementer, reviewer, and telemetry summaries
- `tasks/` stores previewed, active, and archived tasks
- `memory/` stores repo-tracked long-term memory and the active task index

## Workspace isolation

If the repository already has a commit, the harness uses `git worktree add --detach`.

If the repository is still bootstrapping and has no commit yet, the harness falls back to a copied bootstrap workspace so the system remains usable before the first commit. This fallback is intentionally temporary.
