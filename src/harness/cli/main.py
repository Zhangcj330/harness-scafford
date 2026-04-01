from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from harness.codex.bootstrap import CodexBootstrapService
from harness.config import HarnessConfig
from harness.dashboard.app import create_app
from harness.orchestrator.runner import RunService
from harness.tasks.service import TaskService

app = typer.Typer(help="Local-first coding-agent harness scaffold.")
obs_app = typer.Typer(help="Observability stack helpers.")
codex_app = typer.Typer(help="Codex CLI and IDE helpers.")
task_app = typer.Typer(help="Task lifecycle helpers.")
app.add_typer(obs_app, name="obs")
app.add_typer(codex_app, name="codex")
app.add_typer(task_app, name="task")


def _config(config_path: Path | None = None) -> HarnessConfig:
    return HarnessConfig.load(path=config_path, repo_root=Path.cwd())


def _service(config_path: Path | None = None) -> RunService:
    return RunService(_config(config_path))


def _tasks(config_path: Path | None = None) -> TaskService:
    return TaskService(_config(config_path))


@app.command("run")
def run_task(task_file: Path) -> None:
    """Run a task file through planner, implementer, and reviewer phases."""
    manifest = _service().run(task_file)
    typer.echo(manifest.run_id)


@app.command("resume")
def resume_task(run_id: str) -> None:
    """Resume a paused run."""
    manifest = _service().resume(run_id)
    typer.echo(f"{manifest.run_id} {manifest.status}")


@app.command("review")
def review_task(run_id: str) -> None:
    """Re-run only the independent review phase."""
    manifest = _service().review(run_id)
    typer.echo(f"{manifest.run_id} {manifest.status}")


@app.command("dashboard")
def dashboard(host: str = "127.0.0.1", port: int = 8421) -> None:
    """Serve the lightweight local dashboard."""
    uvicorn.run(create_app(), host=host, port=port, log_level="warning")


@codex_app.command("bootstrap")
def codex_bootstrap(
    check: Annotated[
        bool,
        typer.Option("--check", help="Validate Codex project trust config."),
    ] = False,
    apply: Annotated[
        bool,
        typer.Option("--apply", help="Apply the Codex project trust config."),
    ] = False,
    codex_home: Annotated[
        Path | None,
        typer.Option("--codex-home", help="Override the Codex home directory. Useful for testing."),
    ] = None,
) -> None:
    """Ensure Codex CLI and IDE share the same trusted project config for this repo."""
    if check and apply:
        typer.echo("Use either --check or --apply, not both.")
        raise typer.Exit(code=2)
    service = CodexBootstrapService(Path.cwd(), codex_home=codex_home)
    result = service.apply() if apply else service.check()
    typer.echo(result.message)
    typer.echo(f"config: {result.config_path}")
    if result.backup_path:
        typer.echo(f"backup: {result.backup_path}")
    if not result.ok:
        raise typer.Exit(code=1)


@task_app.command("preview")
def preview_task(
    goal: Annotated[str | None, typer.Option("--goal", help="The task goal.")] = None,
    brief_file: Annotated[
        Path | None,
        typer.Option("--brief-file", help="Markdown brief to use for the draft task."),
    ] = None,
    acceptance: Annotated[
        list[str] | None,
        typer.Option("--acceptance", help="Repeat for additional acceptance criteria."),
    ] = None,
    constraint: Annotated[
        list[str] | None,
        typer.Option("--constraint", help="Repeat for task constraints."),
    ] = None,
    task_id: Annotated[
        str | None,
        typer.Option("--task-id", help="Optional task id override."),
    ] = None,
    source: Annotated[str, typer.Option("--source", help="cli or chat")] = "cli",
) -> None:
    """Create a draft task that Codex can review before starting."""
    if not goal and not brief_file:
        typer.echo("Provide --goal or --brief-file.")
        raise typer.Exit(code=2)
    brief_text = brief_file.read_text() if brief_file else None
    if goal is None and brief_text is not None:
        goal = _goal_from_brief(brief_text)
    preview = _tasks().preview_task(
        goal=goal or "task",
        acceptance_criteria=acceptance or None,
        constraints=constraint or None,
        brief_text=brief_text,
        source=source,
        task_id=task_id,
    )
    typer.echo(preview.task_id)
    typer.echo(preview.task_dir)


@task_app.command("start")
def start_task(task_id: str) -> None:
    """Move a draft task into active state and run it."""
    task_file = _tasks().start_task(task_id)
    manifest = _service().run(task_file)
    typer.echo(f"{task_id} {manifest.run_id} {manifest.status}")


@task_app.command("suggest-memory")
def suggest_task_memory(
    identifier: str,
    apply: Annotated[
        bool,
        typer.Option("--apply", help="Promote the suggestion into project memory."),
    ] = False,
) -> None:
    """Generate memory suggestions for a task id or run id."""
    tasks = _tasks()
    suggestion_path = (
        tasks.suggest_memory(task_id=identifier, apply=apply)
        if tasks.has_task(identifier)
        else tasks.suggest_memory(run_id=identifier, apply=apply)
    )
    typer.echo(str(suggestion_path))


@obs_app.command("up")
def obs_up() -> None:
    """Start the local Grafana stack."""
    if not shutil.which("docker"):
        typer.echo("Docker is not installed; observability stack cannot start.")
        raise typer.Exit(code=1)
    compose_file = Path("ops/observability/docker-compose.yml")
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "up", "-d"],
        check=False,
    )


@obs_app.command("down")
def obs_down() -> None:
    """Stop the local Grafana stack."""
    if not shutil.which("docker"):
        typer.echo("Docker is not installed; observability stack cannot stop.")
        raise typer.Exit(code=1)
    compose_file = Path("ops/observability/docker-compose.yml")
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "down"],
        check=False,
    )


def _goal_from_brief(brief_text: str) -> str:
    for line in brief_text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped
    return "task"
