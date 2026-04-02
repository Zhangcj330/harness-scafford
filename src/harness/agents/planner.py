from __future__ import annotations

from harness.agents.provider import OpenAIProvider
from harness.schemas.task import TaskSpec


class PlannerAgent:
    def __init__(self, provider: OpenAIProvider) -> None:
        self.provider = provider

    def plan(self, task: TaskSpec) -> str:
        return self.provider.complete(
            system_prompt=(
                "You are the planning agent in a coding harness. "
                "Write a compact execution plan with risks and validation steps."
            ),
            user_prompt=(
                f"Goal: {task.goal}\n"
                f"Acceptance criteria: {task.acceptance_criteria}\n"
                f"Constraints: {task.constraints}\n"
                f"Inputs: {task.inputs}\n"
            ),
        )
