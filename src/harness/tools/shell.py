from __future__ import annotations

import subprocess
from pathlib import Path

from harness.tools.base import ToolResult


class ShellTool:
    def run(self, command: str, cwd: Path) -> ToolResult:
        completed = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            text=True,
            capture_output=True,
            check=False,
        )
        return ToolResult(
            tool="shell",
            ok=completed.returncode == 0,
            summary=f"Command exited with code {completed.returncode}",
            data={
                "command": command,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "returncode": completed.returncode,
            },
        )
