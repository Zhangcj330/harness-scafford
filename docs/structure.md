# Repo Structure

This document defines what each top-level structure is for and checks whether the current implementation matches that contract.

## Structure Contract

### `AGENTS.md`

Use it for:

- the shortest entrypoint rules for Codex and CLI
- stable operating constraints
- commands and links into deeper docs

Do not use it for:

- long explanations
- fast-changing task progress
- raw run output

### `docs/`

Use it for:

- stable system documentation
- architecture, operations, observability, Codex workflow, and memory model
- knowledge that should remain valid across many runs and tasks

Do not use it for:

- per-task progress
- raw run artifacts
- fast-changing working memory

### `memory/`

Use it for repo-level shared working memory:

- `project.md`: stable project facts and conventions
- `decisions.md`: active durable decisions
- `current-focus.md`: current priority focus
- `active-tasks.md`: generated index of draft, active, and archived tasks

This layer sits between stable docs and raw run logs. It is expected to change more often than `docs/`.

### `tasks/`

Use it for task-level state:

- `drafts/`: previewed but not started tasks
- `active/`: tasks currently in progress
- `archive/`: completed tasks

Each task directory should contain:

- `task.yaml`: normalized task definition
- `brief.md`: human-readable task framing
- `memory.md`: task-local current state, next steps, and risks
- `task.meta.json`: machine-readable task state and linked runs

### `.runs/`

Use it for run-level raw artifacts:

- `run_manifest.json`
- `handoff.md`
- `events.jsonl`
- `result.json`

This is the audit trail. It should not be treated as the long-term shared memory surface.

### `.worktrees/`

Use it for isolated execution workspaces only.

It is not documentation, not memory, and not the source of truth for task progress.

## Current Conformance Check

### `AGENTS.md`

Status: complete

Why:

- it is short
- it acts as an entrypoint
- it links to deeper docs and memory files

### `docs/`

Status: complete

Why:

- architecture, operations, observability, Codex workflow, and memory model are documented here
- these files are stable explanations rather than raw progress state

Note:

- `docs/plans/` still exists from the earlier scaffold design
- under the current model, it is no longer the main location for live task progress

### `memory/`

Status: complete

Why:

- the expected repo-level memory files exist
- Codex-facing docs and AGENTS point to them

### `tasks/`

Status: complete

Why:

- the tracked task registry exists with `drafts/`, `active/`, and `archive/`
- the task service creates `task.yaml`, `brief.md`, `memory.md`, and `task.meta.json`
- tests cover preview, start, archive, and memory suggestion flow

### `.runs/`

Status: complete

Why:

- run artifacts are still stored under `.runs/<run_id>/`
- run lifecycle code continues to write manifest, handoff, events, and result artifacts there

### `.worktrees/`

Status: complete

Why:

- worktree creation remains isolated from docs, memory, and tasks

## Practical Reading Order

If a human or agent wants to understand current project state, read in this order:

1. `AGENTS.md`
2. `docs/index.md`
3. `memory/project.md`
4. `memory/decisions.md`
5. `memory/current-focus.md`
6. `memory/active-tasks.md`
7. the specific task directory under `tasks/active/`
8. linked run artifacts under `.runs/`
