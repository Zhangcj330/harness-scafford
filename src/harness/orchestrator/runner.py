from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from harness.agents.implementer import ImplementerAgent
from harness.agents.planner import PlannerAgent
from harness.agents.provider import OpenAIProvider
from harness.agents.reviewer import ReviewerAgent, build_review_packet
from harness.config import HarnessConfig
from harness.memory.store import RunStore
from harness.observability.logging import JsonEventLogger
from harness.observability.telemetry import Telemetry
from harness.schemas.run import Handoff, RunManifest, RunResult
from harness.schemas.task import TaskSpec, load_task
from harness.tasks.service import TaskService
from harness.tools.git import GitTool

PHASES = ["planner", "implementer", "reviewer"]


class RunService:
    def __init__(self, config: HarnessConfig) -> None:
        self.config = config
        self.store = RunStore(config)
        self.logger = JsonEventLogger()
        self.git = GitTool()
        self.tasks = TaskService(config)
        provider = OpenAIProvider(config.provider.model)
        self.planner = PlannerAgent(provider)
        self.implementer = ImplementerAgent(config)
        self.reviewer = ReviewerAgent(provider)

    def run(self, task_file: Path) -> RunManifest:
        task = load_task(task_file)
        run_id = self._new_run_id(task)
        manifest = self._bootstrap_manifest(run_id, task, task_file)
        result = RunResult()
        self._execute(task, manifest, result, start_phase="planner")
        return self.store.load_manifest(run_id)

    def resume(self, run_id: str) -> RunManifest:
        manifest = self.store.load_manifest(run_id)
        result = self.store.load_result(run_id)
        task = load_task(Path(manifest.task_file))
        start_phase = self._next_phase(manifest)
        manifest.status = "running"
        manifest.steps_completed = 0
        manifest.timestamps["resumed_at"] = datetime.now(UTC).isoformat()
        manifest.notes.append("Budget counters reset for resumed invocation.")
        self.store.persist_manifest(manifest)
        self._execute(task, manifest, result, start_phase=start_phase)
        return self.store.load_manifest(run_id)

    def review(self, run_id: str) -> RunManifest:
        manifest = self.store.load_manifest(run_id)
        result = self.store.load_result(run_id)
        task = load_task(Path(manifest.task_file))
        handoff = self.store.load_handoff(run_id)
        packet = build_review_packet(task, manifest, result, handoff)
        review_text, passed = self.reviewer.review(task, packet)
        review_path = self.store.artifact_path(run_id, "review.md")
        self.store.write_text(review_path, review_text)
        result.review_summary = review_text
        result.passed = passed
        result.phase_states["reviewer"] = "completed"
        self.store.persist_result(run_id, result)
        manifest.artifacts["review"] = str(review_path)
        manifest.status = "reviewed"
        manifest.current_phase = "reviewer"
        manifest.timestamps["reviewed_at"] = datetime.now(UTC).isoformat()
        manifest = self.tasks.sync_from_run(manifest, result, self.store.load_handoff(run_id))
        self.store.persist_manifest(manifest)
        return manifest

    def _execute(
        self,
        task: TaskSpec,
        manifest: RunManifest,
        result: RunResult,
        start_phase: str,
    ) -> None:
        telemetry = Telemetry(self.config, manifest)
        start_index = PHASES.index(start_phase)
        for phase in PHASES[start_index:]:
            if manifest.steps_completed >= self.config.budgets.max_steps:
                self._pause(manifest, result, f"Step budget reached before {phase}")
                return
            if phase == "planner":
                self._run_planner(task, manifest, result, telemetry)
            elif phase == "implementer":
                self._run_implementer(task, manifest, result, telemetry)
            elif phase == "reviewer":
                self._run_reviewer(task, manifest, result, telemetry)
            self._checkpoint(manifest, result, f"Completed {phase}")
        result.telemetry_summary = telemetry.finish()
        self.store.persist_result(manifest.run_id, result)
        manifest.status = "completed"
        manifest.timestamps["completed_at"] = datetime.now(UTC).isoformat()
        manifest = self.tasks.sync_from_run(
            manifest,
            result,
            self.store.load_handoff(manifest.run_id),
        )
        self.store.persist_manifest(manifest)

    def _run_planner(
        self,
        task: TaskSpec,
        manifest: RunManifest,
        result: RunResult,
        telemetry: Telemetry,
    ) -> None:
        with telemetry.span("plan", agent_role="planner"):
            telemetry.record_turn("planner")
            plan_text = self.planner.plan(task)
            path = self.store.artifact_path(manifest.run_id, "planner_plan.md")
            self.store.write_text(path, plan_text)
            result.plan_summary = plan_text
            result.phase_states["planner"] = "completed"
            manifest.artifacts["planner_plan"] = str(path)
            manifest.current_phase = "planner"
            manifest.steps_completed += 1
            self._emit("phase_completed", manifest, phase="planner")

    def _run_implementer(
        self,
        task: TaskSpec,
        manifest: RunManifest,
        result: RunResult,
        telemetry: Telemetry,
    ) -> None:
        run_dir = self.store.run_dir(manifest.run_id)
        worktree_path = Path(manifest.worktree_path)
        with telemetry.span("implement", agent_role="implementer"):
            telemetry.record_turn("implementer")
            summary, tool_results = self.implementer.execute(
                task,
                run_dir=run_dir,
                worktree_path=worktree_path,
            )
            for item in tool_results:
                telemetry.record_tool_call("implementer")
                if not item.get("ok", False):
                    telemetry.record_failure("implementer")
            path = self.store.artifact_path(manifest.run_id, "implementer_summary.md")
            self.store.write_text(path, summary)
            result.implementation_summary = summary
            result.tool_results.extend(tool_results)
            result.phase_states["implementer"] = "completed"
            manifest.artifacts["implementer_summary"] = str(path)
            manifest.current_phase = "implementer"
            manifest.tool_calls = len(result.tool_results)
            manifest.steps_completed += 1
            self._emit("phase_completed", manifest, phase="implementer")

    def _run_reviewer(
        self,
        task: TaskSpec,
        manifest: RunManifest,
        result: RunResult,
        telemetry: Telemetry,
    ) -> None:
        handoff = self.store.load_handoff(manifest.run_id)
        packet = build_review_packet(task, manifest, result, handoff)
        with telemetry.span("review_pass", agent_role="reviewer"):
            telemetry.record_turn("reviewer")
            review_text, passed = self.reviewer.review(task, packet)
            path = self.store.artifact_path(manifest.run_id, "review.md")
            self.store.write_text(path, review_text)
            result.review_summary = review_text
            result.passed = passed
            result.phase_states["reviewer"] = "completed"
            manifest.artifacts["review"] = str(path)
            manifest.current_phase = "reviewer"
            manifest.steps_completed += 1
            self._emit("phase_completed", manifest, phase="reviewer")

    def _bootstrap_manifest(self, run_id: str, task: TaskSpec, task_file: Path) -> RunManifest:
        worktree_path = self.config.worktrees_dir / run_id
        workspace_result = self.git.create_workspace(self.config.repo_root, worktree_path)
        git_sha = self.git.current_sha(self.config.repo_root)
        manifest = RunManifest(
            run_id=run_id,
            task_id=task.task_id,
            task_file=str(task_file.resolve()),
            status="running",
            provider=self.config.provider.name,
            model=self.config.provider.model,
            worktree_path=str(worktree_path),
            artifacts={},
            budgets={
                "max_steps": self.config.budgets.max_steps,
                "max_tool_calls": self.config.budgets.max_tool_calls,
                "max_runtime_seconds": self.config.budgets.max_runtime_seconds,
            },
            timestamps={"created_at": datetime.now(UTC).isoformat()},
            git_sha=git_sha,
            notes=[workspace_result.summary],
        )
        self.store.persist_manifest(manifest)
        self._emit(
            "workspace_prepared",
            manifest,
            workspace=workspace_result.model_dump(mode="json"),
        )
        initial_handoff = Handoff(
            current_state="Run initialized",
            open_threads=task.acceptance_criteria,
            next_steps=["Execute planner phase."],
            known_risks=task.constraints,
        )
        self.store.persist_handoff(run_id, initial_handoff)
        self.store.persist_result(run_id, RunResult())
        return manifest

    def _checkpoint(self, manifest: RunManifest, result: RunResult, state: str) -> None:
        handoff = Handoff(
            current_state=state,
            open_threads=[] if result.passed else ["Review pending or failed checks remain"],
            next_steps=[self._resume_hint(manifest)],
            known_risks=[],
        )
        self.store.persist_handoff(manifest.run_id, handoff)
        self.store.persist_result(manifest.run_id, result)
        self.store.persist_manifest(manifest)
        manifest = self.tasks.sync_from_run(
            manifest,
            result,
            self.store.load_handoff(manifest.run_id),
        )
        self.store.persist_manifest(manifest)
        self._emit("checkpoint", manifest, state=state)

    def _pause(self, manifest: RunManifest, result: RunResult, reason: str) -> None:
        handoff = Handoff(
            current_state=reason,
            open_threads=["Resume from the next incomplete phase."],
            next_steps=[self._resume_hint(manifest)],
            known_risks=["Budget limit reached before all phases completed."],
        )
        self.store.persist_handoff(manifest.run_id, handoff)
        result.telemetry_summary = {"status": "paused"}
        self.store.persist_result(manifest.run_id, result)
        manifest.status = "paused"
        manifest.timestamps["paused_at"] = datetime.now(UTC).isoformat()
        self.store.persist_manifest(manifest)
        manifest = self.tasks.sync_from_run(
            manifest,
            result,
            self.store.load_handoff(manifest.run_id),
        )
        self.store.persist_manifest(manifest)
        self._emit("paused", manifest, reason=reason)

    def _resume_hint(self, manifest: RunManifest) -> str:
        return f"Run `uv run harness resume {manifest.run_id}`"

    def _emit(self, event_type: str, manifest: RunManifest, **payload: object) -> None:
        event = self.logger.emit(
            event_type,
            run_id=manifest.run_id,
            task_id=manifest.task_id,
            current_phase=manifest.current_phase,
            status=manifest.status,
            **payload,
        )
        self.store.append_event(manifest.run_id, event)

    def _next_phase(self, manifest: RunManifest) -> str:
        if manifest.current_phase is None:
            return "planner"
        current_index = PHASES.index(manifest.current_phase)
        if manifest.current_phase == "reviewer":
            return "reviewer"
        return PHASES[current_index + 1]

    def _new_run_id(self, task: TaskSpec) -> str:
        prefix = task.task_id.replace(" ", "-").lower()
        return f"{prefix}-{uuid4().hex[:8]}"
