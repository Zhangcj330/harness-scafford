from __future__ import annotations

from typing import Any

from harness.agents.provider import OpenAIProvider, ProviderUnavailableError
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
        fallback = self._fallback_review(task, packet)
        try:
            text = self.provider.complete(
                system_prompt=(
                    "You are the reviewer agent in a coding harness. "
                    "Review the execution evidence, note risks, and decide pass/fail."
                ),
                user_prompt=str(packet),
            )
            passed = "fail" not in text.lower()
            return text, passed
        except ProviderUnavailableError:
            return fallback

    def _fallback_review(self, task: TaskSpec, packet: dict[str, Any]) -> tuple[str, bool]:
        tool_results = packet.get("tool_results", [])
        failures = [item for item in tool_results if not item.get("ok", False)]
        missing = []
        if not packet.get("implementation_summary"):
            missing.append("implementation summary")
        body = [
            "# Reviewer Output",
            "",
            f"- Goal: {task.goal}",
            f"- Acceptance criteria count: {len(task.acceptance_criteria)}",
            f"- Tool failures: {len(failures)}",
            f"- Missing signals: {', '.join(missing) if missing else 'none'}",
        ]
        if failures:
            body.append("- Verdict: fail")
            for item in failures:
                body.append(f"- Failure: {item.get('tool')}: {item.get('summary')}")
            return "\n".join(body) + "\n", False
        body.append("- Verdict: pass")
        return "\n".join(body) + "\n", True
