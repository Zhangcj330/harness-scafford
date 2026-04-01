from __future__ import annotations

from harness.agents.provider import OpenAIProvider, ProviderUnavailableError
from harness.schemas.task import TaskSpec


class PlannerAgent:
    def __init__(self, provider: OpenAIProvider) -> None:
        self.provider = provider

    def plan(self, task: TaskSpec) -> str:
        fallback = self._fallback_plan(task)
        try:
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
        except ProviderUnavailableError:
            return fallback

    def _fallback_plan(self, task: TaskSpec) -> str:
        criteria = "\n".join(f"- {item}" for item in task.acceptance_criteria)
        constraints = (
            "\n".join(f"- {item}" for item in task.constraints) or "- No extra constraints supplied"
        )
        return (
            "# Planner Output\n\n"
            f"## Goal\n{task.goal}\n\n"
            "## Acceptance Criteria\n"
            f"{criteria}\n\n"
            "## Constraints\n"
            f"{constraints}\n\n"
            "## Execution Plan\n"
            "- Read the task inputs and prepare an isolated workspace.\n"
            "- Run the requested web, browser, or test actions.\n"
            "- Emit artifacts and checkpoints after each phase.\n"
            "- Produce an independent review based on execution evidence.\n"
        )
