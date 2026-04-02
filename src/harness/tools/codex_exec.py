from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from harness.tools.base import ToolResult


class CodexExecTool:
    def __init__(self, *, timeout_seconds: int = 900) -> None:
        self.timeout_seconds = timeout_seconds

    def run(self, *, prompt: str, cwd: Path, artifact_dir: Path) -> ToolResult:
        codex_path = shutil.which("codex")
        if not codex_path:
            return ToolResult(
                tool="code_exec",
                ok=False,
                summary="Codex CLI is not installed",
                data={"error": "codex executable not found"},
            )

        artifact_dir.mkdir(parents=True, exist_ok=True)
        last_message_path = artifact_dir / "last_message.txt"
        stdout_path = artifact_dir / "stdout.txt"
        stderr_path = artifact_dir / "stderr.txt"

        command = [
            codex_path,
            "exec",
            "--skip-git-repo-check",
            "--color",
            "never",
            "--full-auto",
            "-C",
            str(cwd),
            "--add-dir",
            str(artifact_dir),
            "-o",
            str(last_message_path),
            prompt,
        ]
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
        )
        stdout_path.write_text(completed.stdout)
        stderr_path.write_text(completed.stderr)
        changed_files = self._changed_files(cwd)

        if completed.returncode != 0:
            return ToolResult(
                tool="code_exec",
                ok=False,
                summary=f"Codex exec exited with code {completed.returncode}",
                data={
                    "command": command,
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                    "changed_files": changed_files,
                },
                artifact_paths=[str(stdout_path), str(stderr_path)],
            )

        last_message = (
            last_message_path.read_text().strip()
            if last_message_path.exists()
            else completed.stdout.strip()
        )
        return ToolResult(
            tool="code_exec",
            ok=True,
            summary=f"Codex exec completed; changed {len(changed_files)} files",
            data={
                "command": command,
                "returncode": completed.returncode,
                "last_message": last_message,
                "changed_files": changed_files,
            },
            artifact_paths=[
                str(last_message_path),
                str(stdout_path),
                str(stderr_path),
            ],
        )

    def _changed_files(self, cwd: Path) -> list[str]:
        completed = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if completed.returncode != 0:
            return []
        return [line.strip() for line in completed.stdout.splitlines() if line.strip()]
