# Codex Workflow

## Goal

Make Codex CLI and VS Code Codex Chat follow the same repo-level rules, memory, and task workflow.

## Required read order

1. `AGENTS.md`
2. `memory/project.md`
3. `memory/decisions.md`
4. `memory/current-focus.md`
5. `memory/active-tasks.md`
6. the task directory under `tasks/active/<task_id>/` when working on an active task

## Task rules

- Preview tasks before writing tracked task files
- After approval, materialize the task under `tasks/drafts/`
- Start work by moving the task into `tasks/active/` and running the harness
- Keep task-local memory in `tasks/*/<task_id>/memory.md`
- Keep long-term memory in `memory/`

## Bootstrap

Use `uv run harness codex bootstrap --check` to verify this repo has a Codex project entry.

Use `uv run harness codex bootstrap --apply` to add or correct the repo trust entry while preserving the rest of your Codex configuration.
