from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from harness.tools.base import ToolResult


class GitTool:
    def current_sha(self, repo_root: Path) -> str | None:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            return None
        return completed.stdout.strip()

    def create_workspace(self, repo_root: Path, target_dir: Path) -> ToolResult:
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        if target_dir.exists():
            return ToolResult(
                tool="git",
                ok=True,
                summary=f"Workspace already exists at {target_dir}",
                data={"mode": "existing", "path": str(target_dir)},
            )

        status = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        has_commit = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if status.returncode == 0 and has_commit.returncode == 0:
            completed = subprocess.run(
                ["git", "worktree", "add", "--detach", str(target_dir), "HEAD"],
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )
            return ToolResult(
                tool="git",
                ok=completed.returncode == 0,
                summary="Created detached git worktree"
                if completed.returncode == 0
                else "Failed to create git worktree",
                data={
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                    "path": str(target_dir),
                },
            )

        target_dir.mkdir(parents=True, exist_ok=True)
        for item in repo_root.iterdir():
            if item.name in {".git", ".runs", ".worktrees", ".venv", "__pycache__"}:
                continue
            destination = target_dir / item.name
            if item.is_dir():
                shutil.copytree(item, destination)
            else:
                shutil.copy2(item, destination)
        return ToolResult(
            tool="git",
            ok=True,
            summary="Created bootstrap workspace without git worktree support",
            data={"mode": "bootstrap-copy", "path": str(target_dir)},
        )
