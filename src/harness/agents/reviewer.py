from __future__ import annotations

from typing import Any

from harness.agents.provider import OpenAIProvider
from harness.schemas.run import RunManifest, RunResult
from harness.schemas.task import TaskSpec


def build_review_packet(
    task: TaskSpec,
    manifest: RunManifest,
    result: RunResult,
    handoff_markdown: str,
) -> dict[str, Any]:
    return {
        "goal": task.goal,
        "acceptance_criteria": task.acceptance_criteria,
        "constraints": task.constraints,
        "status": manifest.status,
        "current_phase": manifest.current_phase,
        "tool_results": result.tool_results,
        "implementation_summary": result.implementation_summary,
        "telemetry_summary": result.telemetry_summary,
        "handoff": handoff_markdown,
    }


class ReviewerAgent:
    def __init__(self, provider: OpenAIProvider) -> None:
        self.provider = provider

    def review(self, task: TaskSpec, packet: dict[str, Any]) -> tuple[str, bool]:
        text = self.provider.complete(
            system_prompt=(
                "You are the reviewer agent in a coding harness. "
                "Review the execution evidence, note risks, and decide pass/fail."
            ),
            user_prompt=(
                f"Goal: {task.goal}\n"
                f"Acceptance criteria: {task.acceptance_criteria}\n"
                f"Execution packet: {packet}\n"
                "You must state an explicit verdict line containing either 'Verdict: pass' "
                "or 'Verdict: fail'."
            ),
        )
        passed = "verdict: fail" not in text.lower()
        return text, passed
