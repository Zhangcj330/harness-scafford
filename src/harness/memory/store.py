from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from harness.config import HarnessConfig
from harness.schemas.run import Handoff, RunManifest, RunResult


class RunStore:
    def __init__(self, config: HarnessConfig) -> None:
        self.config = config
        self.runs_dir = config.runs_dir
        self.worktrees_dir = config.worktrees_dir
        self.db_path = config.db_path
        self._ensure_layout()

    def _ensure_layout(self) -> None:
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_phase TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    task_file TEXT NOT NULL,
                    manifest_path TEXT NOT NULL,
                    result_path TEXT NOT NULL
                )
                """
            )

    def run_dir(self, run_id: str) -> Path:
        path = self.runs_dir / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def artifact_path(self, run_id: str, name: str) -> Path:
        return self.run_dir(run_id) / name

    def write_json(self, path: Path, payload: Any) -> None:
        body = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
        path.write_text(json.dumps(body, indent=2, sort_keys=True))

    def write_text(self, path: Path, content: str) -> None:
        path.write_text(content)

    def append_event(self, run_id: str, event: dict[str, Any]) -> None:
        event_path = self.artifact_path(run_id, "events.jsonl")
        enriched = {
            "timestamp": datetime.now(UTC).isoformat(),
            **event,
        }
        with event_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(enriched, sort_keys=True) + "\n")

    def persist_manifest(self, manifest: RunManifest) -> Path:
        path = self.artifact_path(manifest.run_id, "run_manifest.json")
        self.write_json(path, manifest)
        created_at = manifest.timestamps.get("created_at", datetime.now(UTC).isoformat())
        updated_at = datetime.now(UTC).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO runs (
                    run_id, task_id, status, current_phase, created_at, updated_at,
                    task_file, manifest_path, result_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    status = excluded.status,
                    current_phase = excluded.current_phase,
                    updated_at = excluded.updated_at,
                    manifest_path = excluded.manifest_path,
                    result_path = excluded.result_path
                """,
                (
                    manifest.run_id,
                    manifest.task_id,
                    manifest.status,
                    manifest.current_phase,
                    created_at,
                    updated_at,
                    manifest.task_file,
                    str(path),
                    str(self.artifact_path(manifest.run_id, "result.json")),
                ),
            )
        return path

    def persist_result(self, run_id: str, result: RunResult) -> Path:
        path = self.artifact_path(run_id, "result.json")
        self.write_json(path, result)
        return path

    def persist_handoff(self, run_id: str, handoff: Handoff) -> Path:
        path = self.artifact_path(run_id, "handoff.md")
        content = (
            f"# Handoff\n\n"
            f"## Current State\n\n{handoff.current_state}\n\n"
            f"## Open Threads\n\n"
            + "\n".join(f"- {item}" for item in handoff.open_threads)
            + "\n\n## Next Steps\n\n"
            + "\n".join(f"- {item}" for item in handoff.next_steps)
            + "\n\n## Known Risks\n\n"
            + "\n".join(f"- {item}" for item in handoff.known_risks)
            + "\n"
        )
        self.write_text(path, content)
        return path

    def load_manifest(self, run_id: str) -> RunManifest:
        path = self.artifact_path(run_id, "run_manifest.json")
        return RunManifest.model_validate_json(path.read_text())

    def load_result(self, run_id: str) -> RunResult:
        path = self.artifact_path(run_id, "result.json")
        return RunResult.model_validate_json(path.read_text())

    def load_handoff(self, run_id: str) -> str:
        return self.artifact_path(run_id, "handoff.md").read_text()

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT run_id, task_id, status, current_phase, created_at, updated_at, task_file
                FROM runs
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "run_id": row[0],
                "task_id": row[1],
                "status": row[2],
                "current_phase": row[3],
                "created_at": row[4],
                "updated_at": row[5],
                "task_file": row[6],
            }
            for row in rows
        ]
