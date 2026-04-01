from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RunStatus = Literal["pending", "running", "paused", "completed", "failed", "reviewed"]
RunPhase = Literal["planner", "implementer", "reviewer"]


class RunManifest(BaseModel):
    run_id: str
    task_id: str
    task_file: str
    status: RunStatus
    provider: str
    model: str
    worktree_path: str
    artifacts: dict[str, str] = Field(default_factory=dict)
    budgets: dict[str, int] = Field(default_factory=dict)
    timestamps: dict[str, str] = Field(default_factory=dict)
    current_phase: RunPhase | None = None
    steps_completed: int = 0
    tool_calls: int = 0
    git_sha: str | None = None
    notes: list[str] = Field(default_factory=list)


class Handoff(BaseModel):
    current_state: str
    open_threads: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    known_risks: list[str] = Field(default_factory=list)


class RunResult(BaseModel):
    phase_states: dict[str, str] = Field(default_factory=dict)
    plan_summary: str = ""
    implementation_summary: str = ""
    review_summary: str = ""
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    passed: bool | None = None
    telemetry_summary: dict[str, Any] = Field(default_factory=dict)
