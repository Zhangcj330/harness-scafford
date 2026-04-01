from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TaskState = Literal["draft", "active", "archived"]


class TaskMetadata(BaseModel):
    task_id: str
    state: TaskState
    task_file: str
    brief_file: str
    memory_file: str
    latest_run_id: str | None = None
    latest_run_status: str | None = None
    latest_run_artifacts: dict[str, str] = Field(default_factory=dict)
    run_ids: list[str] = Field(default_factory=list)
    source: str = "cli"
    created_at: str
    updated_at: str


class TaskPreview(BaseModel):
    task_id: str
    state: TaskState
    task_dir: str
    task_file: str
    brief_file: str
    memory_file: str
