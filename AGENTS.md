# AGENTS.md

## Setup Commands

- Install dependencies: `uv sync --extra dev`
- Run tests: `uv run pytest -m "not live"`
- Lint: `uv run ruff check .`
- Format check: `uv run ruff format --check .`
- Type check: `uv run pyright`
- Run offline smoke: `uv run python scripts/run_smoke.py --task examples/tasks/offline-smoke.yaml --resume-if-paused`

## Repo Map

- `src/harness/`: runtime code for the CLI, orchestrator, tools, dashboard, storage, and observability
- `docs/`: source-of-truth documentation for system behavior and runbooks
- `.runs/`: per-run artifacts, logs, manifests, and review outputs
- `.worktrees/`: isolated task workspaces
- `ops/observability/`: local Grafana/Loki/Tempo/Prometheus/Alloy stack
- `.github/workflows/`: CI and nightly evaluation workflows

## Hard Constraints

- Do not write run artifacts anywhere except `.runs/<run_id>/`
- Use isolated workspaces under `.worktrees/<run_id>/` for task execution
- Update `docs/` when behavior changes
- Keep `AGENTS.md` concise and point to `docs/` for detail
- Preserve planner, implementer, and reviewer separation

## Required Docs

- [docs/index.md](docs/index.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/operations.md](docs/operations.md)

## Testing And Recovery Rules

- Before finishing a change, run lint, type-check, and the relevant test subset
- If a run pauses, resume with `uv run harness resume <run-id>`
- If review needs to be re-generated, use `uv run harness review <run-id>`
- Treat `.runs/` as audit history; do not mutate old run artifacts in place unless the command is explicitly for review regeneration
