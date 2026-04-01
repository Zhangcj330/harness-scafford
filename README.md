# harness-scaffold

Python-first scaffold for long-running coding-agent workflows.

中文版本: [README.zh-CN.md](README.zh-CN.md)

The repository is structured around a few non-negotiable constraints:

- runs are durable and resumable
- every run emits auditable artifacts under `.runs/`
- work happens in isolated workspaces under `.worktrees/`
- docs are the system source of truth for humans and agents
- observability is built in, not added later

## Quick start

```bash
uv sync --extra dev
uv run harness run examples/tasks/offline-smoke.yaml
uv run harness dashboard
```

For observability:

```bash
uv run harness obs up
uv run harness obs down
```

If Docker is not installed, the harness still runs locally and writes JSON artifacts, but the Grafana stack will stay disabled.

## Main commands

- `uv run harness run <task-file>`
- `uv run harness resume <run-id>`
- `uv run harness review <run-id>`
- `uv run harness codex bootstrap --check`
- `uv run harness codex bootstrap --apply`
- `uv run harness task preview --goal "<text>"`
- `uv run harness task start <task-id>`
- `uv run harness task suggest-memory <task-id>`
- `uv run harness dashboard`
- `uv run harness obs up`
- `uv run harness obs down`

## Docs

- [AGENTS.md](AGENTS.md)
- [docs/index.md](docs/index.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/operations.md](docs/operations.md)
- [docs/observability.md](docs/observability.md)
- [docs/codex.md](docs/codex.md)
- [docs/memory.md](docs/memory.md)

## Notes

This scaffold is intentionally local-first. It supports real OpenAI calls when `OPENAI_API_KEY` is set, but the default developer experience is deterministic and offline-safe so the repo can be tested in CI without live model access.
