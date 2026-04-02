from __future__ import annotations

import subprocess
from pathlib import Path

from harness.tools.codex_exec import CodexExecTool


def test_codex_exec_tool_records_changed_files(monkeypatch, tmp_path) -> None:
    def fake_which(name: str) -> str | None:
        return "/opt/homebrew/bin/codex" if name == "codex" else None

    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[:3] == ["/opt/homebrew/bin/codex", "exec", "--skip-git-repo-check"]:
            output_path = Path(command[command.index("-o") + 1])
            output_path.write_text("implemented\n")
            return subprocess.CompletedProcess(command, 0, "codex stdout", "")
        if command[:3] == ["git", "diff", "--name-only"]:
            return subprocess.CompletedProcess(command, 0, "src/app.py\nREADME.md\n", "")
        raise AssertionError(command)

    monkeypatch.setattr("harness.tools.codex_exec.shutil.which", fake_which)
    monkeypatch.setattr("harness.tools.codex_exec.subprocess.run", fake_run)

    result = CodexExecTool(timeout_seconds=10).run(
        prompt="make it work",
        cwd=tmp_path,
        artifact_dir=tmp_path / "artifacts",
    )

    assert result.ok is True
    assert result.data["changed_files"] == ["src/app.py", "README.md"]
    assert (tmp_path / "artifacts" / "last_message.txt").read_text() == "implemented\n"
    assert len(calls) == 2
