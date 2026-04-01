from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import typer
import uvicorn

from harness.config import HarnessConfig
from harness.dashboard.app import create_app
from harness.orchestrator.runner import RunService

app = typer.Typer(help="Local-first coding-agent harness scaffold.")
obs_app = typer.Typer(help="Observability stack helpers.")
app.add_typer(obs_app, name="obs")


def _service(config_path: Path | None = None) -> RunService:
    config = HarnessConfig.load(path=config_path, repo_root=Path.cwd())
    return RunService(config)


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
    typer.echo(f"Harness dashboard listening at http://{host}:{port}")
    typer.echo("Press Ctrl+C to stop.")
    uvicorn.run(create_app(), host=host, port=port, log_level="warning")


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
