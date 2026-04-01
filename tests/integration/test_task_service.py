from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from harness.config import HarnessConfig
from harness.dashboard.app import create_app
from harness.orchestrator.runner import RunService
from harness.tasks.service import TaskService


def _git(command: list[str], cwd: Path) -> None:
    subprocess.run(["git", *command], cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(repo: Path) -> None:
    (repo / "README.md").write_text("fixture\n")
    (repo / "harness.toml").write_text("")
    _git(["init"], repo)
    _git(["config", "user.email", "test@example.com"], repo)
    _git(["config", "user.name", "Test User"], repo)
    _git(["add", "."], repo)
    _git(["commit", "-m", "init"], repo)


def test_task_preview_start_and_memory_suggestion_flow(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    monkeypatch.chdir(repo)

    config = HarnessConfig.load(path=repo / "harness.toml", repo_root=repo)
    tasks = TaskService(config)
    preview = tasks.preview_task(
        goal="Document Codex task flow",
        acceptance_criteria=["Task is previewed", "Task can be started"],
        task_id="codex-task-flow",
    )
    assert Path(preview.task_file).exists()
    assert (repo / "tasks/drafts/codex-task-flow/task.meta.json").exists()

    task_file = tasks.start_task("codex-task-flow")
    assert task_file == repo / "tasks/active/codex-task-flow/task.yaml"

    manifest = RunService(config).run(task_file)
    assert manifest.status == "completed"
    archived_dir = repo / "tasks/archive/codex-task-flow"
    assert archived_dir.exists()
    metadata = tasks.list_tasks()[0]
    assert metadata["task_id"] == "codex-task-flow"
    assert metadata["state"] == "archived"
    assert metadata["latest_run_id"] == manifest.run_id
    assert manifest.run_id in (archived_dir / "memory.md").read_text()

    suggestion_path = tasks.suggest_memory(task_id="codex-task-flow")
    assert suggestion_path.exists()
    assert "Memory Suggestions" in suggestion_path.read_text()


def test_dashboard_api_lists_tasks(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    config = HarnessConfig.load(path=repo / "harness.toml", repo_root=repo)
    tasks = TaskService(config)
    tasks.preview_task(goal="Preview task in dashboard", task_id="dashboard-task")

    app = create_app(config_path=repo / "harness.toml")
    client = TestClient(app)
    response = client.get("/api/tasks")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert payload[0]["task_id"] == "dashboard-task"
