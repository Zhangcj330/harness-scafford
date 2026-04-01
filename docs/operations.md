# Operations

## Common commands

- Run a task: `uv run harness run examples/tasks/offline-smoke.yaml`
- Resume a paused run: `uv run harness resume <run-id>`
- Re-run review: `uv run harness review <run-id>`
- Check Codex trust: `uv run harness codex bootstrap --check`
- Apply Codex trust: `uv run harness codex bootstrap --apply`
- Preview a tracked task: `uv run harness task preview --goal "..."`
- Start a tracked task: `uv run harness task start <task-id>`
- Generate memory suggestions: `uv run harness task suggest-memory <task-id>`
- Start dashboard: `uv run harness dashboard` then open `http://127.0.0.1:8421`
- Start observability stack: `uv run harness obs up`
- Stop observability stack: `uv run harness obs down`

## Resume flow

When a run pauses because of a step budget or interruption:

1. inspect `.runs/<run_id>/run_manifest.json`
2. inspect `.runs/<run_id>/handoff.md`
3. resume with `uv run harness resume <run-id>`

## Cleanup

- Delete stale task workspaces under `.worktrees/` after verifying they are no longer needed
- Keep `.runs/` as audit history unless retention policy is introduced
- Keep `tasks/archive/` as user-visible completed task history
- Treat `memory/` as durable shared memory, not a scratchpad

## Failure recovery

- Missing Docker: local run still works, but Grafana links are informational only
- Missing `OPENAI_API_KEY`: planner/reviewer fall back to deterministic local output
- Missing Brave API key: `web_search` degrades to an empty but successful result
- Missing Playwright browser binaries: browser capture returns a failed tool result and review should flag it
- Missing `~/.codex/config.toml`: Codex bootstrap must fail closed instead of inventing a config
