from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

import yaml

from harness.config import HarnessConfig
from harness.observability.logging import JsonEventLogger
from harness.schemas.run import RunManifest, RunResult
from harness.tasks.models import TaskMetadata, TaskPreview, TaskState


class TaskService:
    def __init__(self, config: HarnessConfig) -> None:
        self.config = config
        self.tasks_dir = config.tasks_dir
        self.memory_dir = config.memory_dir
        self.logger = JsonEventLogger()
        self._ensure_layout()

    @property
    def drafts_dir(self) -> Path:
        return self.tasks_dir / "drafts"

    @property
    def active_dir(self) -> Path:
        return self.tasks_dir / "active"

    @property
    def archive_dir(self) -> Path:
        return self.tasks_dir / "archive"

    @property
    def suggestions_dir(self) -> Path:
        return self.memory_dir / "suggestions"

    def preview_task(
        self,
        *,
        goal: str,
        acceptance_criteria: list[str] | None = None,
        constraints: list[str] | None = None,
        brief_text: str | None = None,
        source: str = "cli",
        task_id: str | None = None,
    ) -> TaskPreview:
        now = datetime.now(UTC).isoformat()
        normalized_task_id = task_id or self._slugify(goal)
        task_dir = self.drafts_dir / normalized_task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        criteria = acceptance_criteria or ["Task goal completed with documented evidence."]
        task_payload = {
            "goal": goal,
            "acceptance_criteria": criteria,
            "constraints": constraints or [],
            "inputs": {"task_id": normalized_task_id},
        }
        task_file = task_dir / "task.yaml"
        task_file.write_text(yaml.safe_dump(task_payload, sort_keys=False))

        brief_file = task_dir / "brief.md"
        brief_file.write_text(
            brief_text
            or (
                f"# Task Brief\n\n"
                f"## Goal\n\n{goal}\n\n"
                f"## Acceptance Criteria\n\n" + "\n".join(f"- {item}" for item in criteria) + "\n"
            )
        )
        memory_file = task_dir / "memory.md"
        memory_file.write_text(
            "# Task Memory\n\n"
            "## Current State\n\nDraft preview created.\n\n"
            "## Open Threads\n\n"
            + "\n".join(f"- {item}" for item in criteria)
            + "\n\n## Next Steps\n\n- Review the draft.\n- Start the task when ready.\n"
        )
        metadata = TaskMetadata(
            task_id=normalized_task_id,
            state="draft",
            task_file=str(task_file),
            brief_file=str(brief_file),
            memory_file=str(memory_file),
            source=source,
            created_at=now,
            updated_at=now,
        )
        self._write_metadata(task_dir, metadata)
        self.rebuild_indexes()
        self.logger.emit(
            "task_preview_created",
            task_id=normalized_task_id,
            state="draft",
            task_dir=str(task_dir),
        )
        return TaskPreview(
            task_id=normalized_task_id,
            state="draft",
            task_dir=str(task_dir),
            task_file=str(task_file),
            brief_file=str(brief_file),
            memory_file=str(memory_file),
        )

    def start_task(self, task_id: str) -> Path:
        if (self.active_dir / task_id).exists():
            task_dir = self.active_dir / task_id
            metadata = self._load_metadata(task_dir)
        else:
            draft_dir = self.drafts_dir / task_id
            if not draft_dir.exists():
                raise FileNotFoundError(f"Task {task_id!r} not found in drafts or active tasks.")
            task_dir = self.active_dir / task_id
            task_dir.parent.mkdir(parents=True, exist_ok=True)
            if task_dir.exists():
                shutil.rmtree(task_dir)
            shutil.move(str(draft_dir), str(task_dir))
            metadata = self._load_metadata(task_dir)
            metadata.state = "active"
            metadata.task_file = str(task_dir / "task.yaml")
            metadata.brief_file = str(task_dir / "brief.md")
            metadata.memory_file = str(task_dir / "memory.md")
            metadata.updated_at = datetime.now(UTC).isoformat()
            self._write_metadata(task_dir, metadata)

        self.rebuild_indexes()
        self.logger.emit(
            "task_started",
            task_id=task_id,
            state="active",
            task_dir=str(task_dir),
        )
        return task_dir / "task.yaml"

    def suggest_memory(
        self,
        *,
        task_id: str | None = None,
        run_id: str | None = None,
        apply: bool = False,
    ) -> Path:
        if task_id:
            task_dir = self._find_task_dir(task_id)
            metadata = self._load_metadata(task_dir)
            memory_text = Path(metadata.memory_file).read_text()
            suggestion_key = task_id
            latest_run = metadata.latest_run_id
        elif run_id:
            task_dir = None
            memory_text = ""
            suggestion_key = run_id
            latest_run = run_id
        else:
            raise ValueError("Either task_id or run_id must be provided.")

        suggestion = (
            "# Memory Suggestions\n\n"
            f"## Source\n\n- task: {task_id or 'n/a'}\n- run: {latest_run or run_id or 'n/a'}\n\n"
            "## Candidate Updates\n\n"
            "- Capture any new stable repo conventions discovered in this task.\n"
            "- Promote only verified architecture or workflow changes.\n"
            "- Keep transient debugging notes out of long-term project memory.\n\n"
            "## Task Context\n\n"
            f"{memory_text or 'No task-local memory was available for this run.'}\n"
        )
        self.suggestions_dir.mkdir(parents=True, exist_ok=True)
        suggestion_path = self.suggestions_dir / f"{suggestion_key}.md"
        suggestion_path.write_text(suggestion)

        if task_dir is not None:
            (task_dir / "memory-suggestions.md").write_text(suggestion)

        self.logger.emit(
            "task_memory_suggested",
            task_id=task_id,
            run_id=run_id or latest_run,
            suggestion_path=str(suggestion_path),
        )
        if apply:
            self._apply_suggestion(suggestion_path)
        return suggestion_path

    def has_task(self, task_id: str) -> bool:
        try:
            self._find_task_dir(task_id)
        except FileNotFoundError:
            return False
        return True

    def sync_from_run(
        self,
        manifest: RunManifest,
        result: RunResult,
        handoff_markdown: str,
    ) -> RunManifest:
        task_dir = self._task_dir_for_task_file(Path(manifest.task_file))
        if task_dir is None:
            return manifest

        metadata = self._load_metadata(task_dir)
        if manifest.run_id not in metadata.run_ids:
            metadata.run_ids.append(manifest.run_id)
        metadata.latest_run_id = manifest.run_id
        metadata.latest_run_status = manifest.status
        metadata.latest_run_artifacts = manifest.artifacts
        metadata.updated_at = datetime.now(UTC).isoformat()

        memory_path = task_dir / "memory.md"
        memory_path.write_text(
            "# Task Memory\n\n"
            f"## Current State\n\n{self._extract_section(handoff_markdown, 'Current State')}\n\n"
            f"## Open Threads\n\n{self._extract_section(handoff_markdown, 'Open Threads')}\n\n"
            f"## Next Steps\n\n{self._extract_section(handoff_markdown, 'Next Steps')}\n\n"
            f"## Known Risks\n\n{self._extract_section(handoff_markdown, 'Known Risks')}\n\n"
            f"## Latest Run\n\n- run_id: {manifest.run_id}\n- status: {manifest.status}\n"
        )
        metadata.memory_file = str(memory_path)

        if manifest.status in {"completed", "reviewed"} and task_dir.parent == self.active_dir:
            archive_dir = self.archive_dir / metadata.task_id
            if archive_dir.exists():
                shutil.rmtree(archive_dir)
            shutil.move(str(task_dir), str(archive_dir))
            task_dir = archive_dir
            metadata.state = "archived"
            metadata.task_file = str(task_dir / "task.yaml")
            metadata.brief_file = str(task_dir / "brief.md")
            metadata.memory_file = str(task_dir / "memory.md")
            manifest.task_file = metadata.task_file

        self._write_metadata(task_dir, metadata)
        self.rebuild_indexes()
        self.logger.emit(
            "task_memory_updated",
            task_id=metadata.task_id,
            run_id=manifest.run_id,
            status=manifest.status,
            task_dir=str(task_dir),
        )
        return manifest

    def list_tasks(self) -> list[dict[str, object]]:
        tasks: list[TaskMetadata] = []
        for base in (self.drafts_dir, self.active_dir, self.archive_dir):
            if not base.exists():
                continue
            for child in sorted(base.iterdir()):
                if child.is_dir() and (child / "task.meta.json").exists():
                    tasks.append(self._load_metadata(child))
        tasks.sort(key=lambda item: item.updated_at, reverse=True)
        return [task.model_dump(mode="json") for task in tasks]

    def rebuild_indexes(self) -> None:
        self._ensure_layout()
        drafts = self._tasks_for_state("draft")
        active = self._tasks_for_state("active")
        archived = self._tasks_for_state("archived")
        content = ["# Active Task Index", ""]
        for title, rows in (("Drafts", drafts), ("Active", active), ("Archived", archived)):
            content.append(f"## {title}")
            content.append("")
            if not rows:
                content.append("- None")
            else:
                for task in rows:
                    content.append(
                        f"- `{task.task_id}`: {task.state}, "
                        f"latest run `{task.latest_run_id or 'n/a'}`"
                    )
            content.append("")
        (self.memory_dir / "active-tasks.md").write_text("\n".join(content).rstrip() + "\n")

    def _apply_suggestion(self, suggestion_path: Path) -> None:
        decisions_path = self.memory_dir / "decisions.md"
        existing = (
            decisions_path.read_text() if decisions_path.exists() else "# Active Decisions\n\n"
        )
        updated = (
            existing.rstrip() + "\n\n## Applied Memory Suggestion\n\n" + suggestion_path.read_text()
        )
        decisions_path.write_text(updated + "\n")
        self.logger.emit("memory_promotion_applied", suggestion_path=str(suggestion_path))

    def _tasks_for_state(self, state: TaskState) -> list[TaskMetadata]:
        base = {
            "draft": self.drafts_dir,
            "active": self.active_dir,
            "archived": self.archive_dir,
        }[state]
        if not base.exists():
            return []
        items = []
        for child in sorted(base.iterdir()):
            if child.is_dir() and (child / "task.meta.json").exists():
                items.append(self._load_metadata(child))
        return items

    def _ensure_layout(self) -> None:
        for path in (
            self.drafts_dir,
            self.active_dir,
            self.archive_dir,
            self.memory_dir,
            self.suggestions_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
        self._ensure_memory_file(
            self.memory_dir / "project.md",
            "# Project Memory\n\n"
            "- Use `AGENTS.md` and `docs/` as the source of truth.\n"
            "- Runs are durable under `.runs/` and workspaces are isolated under `.worktrees/`.\n"
            "- Codex chat should preview tasks before materializing tracked task files.\n",
        )
        self._ensure_memory_file(
            self.memory_dir / "decisions.md",
            "# Active Decisions\n\n- No promoted long-term memory yet.\n",
        )
        self._ensure_memory_file(
            self.memory_dir / "current-focus.md",
            "# Current Focus\n\n"
            "- Update this file when the team wants Codex to prioritize a specific area.\n",
        )
        self._ensure_memory_file(
            self.memory_dir / "active-tasks.md",
            "# Active Task Index\n\n- None\n",
        )

    def _ensure_memory_file(self, path: Path, content: str) -> None:
        if not path.exists():
            path.write_text(content)

    def _write_metadata(self, task_dir: Path, metadata: TaskMetadata) -> None:
        (task_dir / "task.meta.json").write_text(
            json.dumps(metadata.model_dump(mode="json"), indent=2, sort_keys=True)
        )

    def _load_metadata(self, task_dir: Path) -> TaskMetadata:
        return TaskMetadata.model_validate_json((task_dir / "task.meta.json").read_text())

    def _find_task_dir(self, task_id: str) -> Path:
        for base in (self.drafts_dir, self.active_dir, self.archive_dir):
            candidate = base / task_id
            if candidate.exists():
                return candidate
        raise FileNotFoundError(f"Task {task_id!r} was not found.")

    def _task_dir_for_task_file(self, task_file: Path) -> Path | None:
        try:
            task_file.relative_to(self.tasks_dir)
        except ValueError:
            return None
        if task_file.name != "task.yaml":
            return None
        return task_file.parent

    def _extract_section(self, markdown: str, heading: str) -> str:
        pattern = rf"## {re.escape(heading)}\n\n(.*?)(?:\n## |\Z)"
        match = re.search(pattern, markdown, flags=re.S)
        if not match:
            return "- None"
        return match.group(1).strip() or "- None"

    def _slugify(self, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return normalized or "task"
