from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from harness.config import HarnessConfig
from harness.dashboard.app import create_app
from harness.orchestrator.runner import RunService


def _git(command: list[str], cwd: Path) -> None:
    subprocess.run(["git", *command], cwd=cwd, check=True, capture_output=True, text=True)


def test_run_service_can_pause_and_resume(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("fixture\n")
    (repo / "harness.toml").write_text(
        """
[provider]
name = "openai"
model = "gpt-5.1"

[budgets]
max_steps = 2
max_tool_calls = 10
max_runtime_seconds = 60
"""
    )
    task_file = repo / "task.yaml"
    task_file.write_text(
        yaml.safe_dump(
            {
                "goal": "pause then resume",
                "acceptance_criteria": ["planner and implementer run", "resume reaches review"],
                "constraints": [],
                "inputs": {"task_id": "pause-resume", "test_command": "python -c \"print('ok')\""},
            }
        )
    )
    _git(["init"], repo)
    _git(["config", "user.email", "test@example.com"], repo)
    _git(["config", "user.name", "Test User"], repo)
    _git(["add", "."], repo)
    _git(["commit", "-m", "init"], repo)

    def fake_complete(self, system_prompt: str, user_prompt: str) -> str:
        if "planning agent" in system_prompt:
            return "# Planner Output\n\n- ready\n"
        return "# Reviewer Output\n\nVerdict: pass\n"

    monkeypatch.setattr("harness.agents.provider.OpenAIProvider.complete", fake_complete)

    config = HarnessConfig.load(path=repo / "harness.toml", repo_root=repo)
    service = RunService(config)
    manifest = service.run(task_file)
    assert manifest.status == "paused"

    resumed = service.resume(manifest.run_id)
    assert resumed.status == "completed"
    result = service.store.load_result(manifest.run_id)
    assert result.phase_states["planner"] == "completed"
    assert result.phase_states["implementer"] == "completed"
    assert result.phase_states["reviewer"] == "completed"


def test_dashboard_api_lists_runs(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "harness.toml").write_text("")
    config = HarnessConfig.load(path=repo / "harness.toml", repo_root=repo)
    service = RunService(config)
    service.store._ensure_layout()

    app = create_app(config_path=repo / "harness.toml")
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/api/runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
