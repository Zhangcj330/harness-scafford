from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from harness.config import HarnessConfig
from harness.memory.store import RunStore
from harness.tasks.service import TaskService


def create_app(config_path: Path | None = None) -> FastAPI:
    repo_root = config_path.resolve().parent if config_path else Path.cwd()
    config = HarnessConfig.load(path=config_path, repo_root=repo_root)
    store = RunStore(config)
    tasks = TaskService(config)
    app = FastAPI(title="Harness Dashboard")

    @app.get("/api/runs")
    def list_runs() -> list[dict[str, object]]:
        return store.list_runs()

    @app.get("/api/tasks")
    def list_tasks() -> list[dict[str, object]]:
        return tasks.list_tasks()

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, object]:
        try:
            manifest = store.load_manifest(run_id)
            result = store.load_result(run_id)
            handoff = store.load_handoff(run_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "manifest": manifest.model_dump(mode="json"),
            "result": result.model_dump(mode="json"),
            "handoff": handoff,
        }

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        return """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Harness Dashboard</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f3efe6;
        --panel: #fffdf8;
        --ink: #1f2a30;
        --accent: #9b3d12;
        --border: #d5c7b8;
      }
      body {
        margin: 0;
        font-family: "Iowan Old Style", "Palatino Linotype", serif;
        background:
          radial-gradient(circle at top left, #efe3c7 0, transparent 35%),
          linear-gradient(180deg, #f9f4ea 0%, var(--bg) 100%);
        color: var(--ink);
      }
      main {
        max-width: 980px;
        margin: 0 auto;
        padding: 48px 20px 80px;
      }
      h1 {
        font-size: 2.5rem;
        margin-bottom: 0.2rem;
      }
      p {
        max-width: 62ch;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        background: var(--panel);
        border: 1px solid var(--border);
        box-shadow: 0 10px 30px rgba(70, 48, 27, 0.08);
      }
      th, td {
        text-align: left;
        padding: 12px;
        border-bottom: 1px solid var(--border);
        vertical-align: top;
      }
      .status {
        color: var(--accent);
        font-weight: 700;
      }
    </style>
  </head>
  <body>
    <main>
      <h1>Harness Dashboard</h1>
      <p>Recent runs, stored artifacts, and review status from the local run index.</p>
      <h2>Tasks</h2>
      <table>
        <thead>
          <tr>
            <th>Task</th>
            <th>State</th>
            <th>Latest Run</th>
            <th>Status</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody id="tasks"></tbody>
      </table>
      <h2>Runs</h2>
      <table>
        <thead>
          <tr>
            <th>Run</th>
            <th>Status</th>
            <th>Phase</th>
            <th>Updated</th>
            <th>Task</th>
          </tr>
        </thead>
        <tbody id="runs"></tbody>
      </table>
    </main>
    <script>
      async function loadDashboard() {
        const [runsResponse, tasksResponse] = await Promise.all([
          fetch('/api/runs'),
          fetch('/api/tasks'),
        ]);
        const [runs, tasks] = await Promise.all([
          runsResponse.json(),
          tasksResponse.json(),
        ]);
        const runsBody = document.getElementById('runs');
        runsBody.innerHTML = runs.map((run) => `
          <tr>
            <td><a href="/api/runs/${run.run_id}" target="_blank">${run.run_id}</a></td>
            <td class="status">${run.status}</td>
            <td>${run.current_phase || ''}</td>
            <td>${run.updated_at}</td>
            <td>${run.task_file}</td>
          </tr>
        `).join('');
        const tasksBody = document.getElementById('tasks');
        tasksBody.innerHTML = tasks.map((task) => `
          <tr>
            <td>${task.task_id}</td>
            <td class="status">${task.state}</td>
            <td>${task.latest_run_id || ''}</td>
            <td>${task.latest_run_status || ''}</td>
            <td>${task.updated_at}</td>
          </tr>
        `).join('');
      }
      loadDashboard();
      setInterval(loadDashboard, 5000);
    </script>
  </body>
</html>
        """

    return app
