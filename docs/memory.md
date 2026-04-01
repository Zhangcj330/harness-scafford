# Memory Model

## Long-term repo memory

- `memory/project.md`: stable project facts and conventions
- `memory/decisions.md`: durable decisions to carry into new chats
- `memory/current-focus.md`: current work focus for Codex
- `memory/active-tasks.md`: generated index of draft, active, and archived tasks

## Task memory

Each task directory stores:

- `task.yaml`: normalized task spec
- `brief.md`: human-readable task framing
- `memory.md`: task-local current state, open threads, next steps, and latest run summary
- `task.meta.json`: task state and run pointers

## Promotion

Task completion does not automatically edit long-term memory.

Use `uv run harness task suggest-memory <task-id>` to generate suggestions.

Use `uv run harness task suggest-memory <task-id> --apply` only when you explicitly want to promote those suggestions into repo memory.
