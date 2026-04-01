# Observability

## Signals

- Logs: structured JSON events to stdout and `.runs/<run_id>/events.jsonl`
- Metrics: `run_duration_seconds`, `tool_calls_total`, `agent_turns_total`, `failed_steps_total`
- Traces: `plan`, `implement`, `review_pass`, plus tool-specific spans as they are added

## Required labels

- `run_id`
- `task_id`
- `agent_role`
- `provider`
- `model`
- `git_sha`
- `worktree`

## Local stack

The local stack uses:

- Grafana
- Loki
- Tempo
- Prometheus
- Grafana Alloy

Compose file:

- [ops/observability/docker-compose.yml](../ops/observability/docker-compose.yml)

## Query examples

- Loki: `{run_id="<run-id>"}`
- Prometheus: `tool_calls_total{run_id="<run-id>"}`
- Tempo: filter spans by the `run_id` attribute

## Alerts

Start with these thresholds:

- `failed_steps_total > 0` for any run
- run duration materially above the normal smoke baseline
- repeated paused runs for the same task without a reviewed completion
