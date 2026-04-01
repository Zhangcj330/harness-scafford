from __future__ import annotations

from pathlib import Path

from harness.tools.base import ToolResult
from harness.tools.shell import ShellTool


class TestTool:
    def __init__(self) -> None:
        self.shell = ShellTool()

    def run(self, command: str, cwd: Path) -> ToolResult:
        result = self.shell.run(command, cwd)
        return ToolResult(
            tool="tests",
            ok=result.ok,
            summary=result.summary,
            data=result.data,
        )
