from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class TaskSpec(BaseModel):
    goal: str
    acceptance_criteria: list[str]
    constraints: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)

    @property
    def task_id(self) -> str:
        raw = self.inputs.get("task_id")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return "task"


def load_task(path: Path) -> TaskSpec:
    payload = yaml.safe_load(path.read_text()) or {}
    return TaskSpec.model_validate(payload)
