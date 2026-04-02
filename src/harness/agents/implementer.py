from __future__ import annotations

from pathlib import Path

from harness.config import HarnessConfig
from harness.schemas.task import TaskSpec
from harness.tools.browser import BrowserTool
from harness.tools.codex_exec import CodexExecTool
from harness.tools.tests import TestTool
from harness.tools.web_fetch import WebFetchTool
from harness.tools.web_search import WebSearchTool


class ImplementerAgent:
    def __init__(self, config: HarnessConfig) -> None:
        self.config = config
        self.web_fetch = WebFetchTool()
        self.web_search = WebSearchTool()
        self.browser = BrowserTool()
        self.code_exec = CodexExecTool(timeout_seconds=config.budgets.max_runtime_seconds)
        self.tests = TestTool()

    def execute(
        self,
        task: TaskSpec,
        run_dir: Path,
        worktree_path: Path,
        plan_summary: str = "",
    ) -> tuple[str, list[dict[str, object]]]:
        tool_results: list[dict[str, object]] = []

        for query in task.inputs.get("search_queries", []):
            result = self.web_search.search(str(query))
            tool_results.append(result.model_dump(mode="json"))

        for index, url in enumerate(task.inputs.get("urls", [])):
            artifact_dir = run_dir / f"web_fetch_{index}"
            result = self.web_fetch.fetch(str(url), artifact_dir=artifact_dir)
            tool_results.append(result.model_dump(mode="json"))

        browser_urls = task.inputs.get("browser_urls", task.inputs.get("urls", []))
        for index, url in enumerate(browser_urls[:1]):
            artifact_dir = run_dir / f"browser_{index}"
            result = self.browser.capture(str(url), artifact_dir=artifact_dir)
            tool_results.append(result.model_dump(mode="json"))

        if self.config.tool_policy.allow_code_exec and bool(task.inputs.get("code_exec")):
            artifact_dir = run_dir / "code_exec"
            prompt = self._code_exec_prompt(task, plan_summary, run_dir)
            result = self.code_exec.run(
                prompt=prompt,
                cwd=worktree_path,
                artifact_dir=artifact_dir,
            )
            tool_results.append(result.model_dump(mode="json"))

        command = task.inputs.get("test_command")
        if isinstance(command, str) and command.strip():
            result = self.tests.run(command.strip(), cwd=worktree_path)
            tool_results.append(result.model_dump(mode="json"))

        summary_lines = [
            "# Implementer Output",
            "",
            f"- Goal: {task.goal}",
            f"- Tool calls: {len(tool_results)}",
            f"- Workspace: {worktree_path}",
        ]
        if not tool_results:
            summary_lines.append("- No tool actions requested by task inputs.")
        else:
            for item in tool_results:
                summary_lines.append(f"- {item['tool']}: {item['summary']}")
        return "\n".join(summary_lines) + "\n", tool_results

    def _code_exec_prompt(self, task: TaskSpec, plan_summary: str, run_dir: Path) -> str:
        return (
            "You are implementing a coding task inside a git worktree.\n"
            "Modify files in the current repository to satisfy the task.\n"
            "Keep the scope tight, preserve existing structure, and avoid unrelated refactors.\n"
            "You may inspect execution artifacts under this path if useful:\n"
            f"{run_dir}\n\n"
            f"Goal:\n{task.goal}\n\n"
            f"Acceptance criteria:\n{task.acceptance_criteria}\n\n"
            f"Constraints:\n{task.constraints}\n\n"
            f"Planner summary:\n{plan_summary or 'No planner summary was available.'}\n\n"
            "Make the necessary code changes and include a concise final summary "
            "of files changed and checks run."
        )
