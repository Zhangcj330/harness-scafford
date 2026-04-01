from harness.agents.reviewer import build_review_packet
from harness.schemas.run import RunManifest, RunResult
from harness.schemas.task import TaskSpec


def test_review_packet_does_not_include_planner_output() -> None:
    task = TaskSpec(
        goal="test",
        acceptance_criteria=["criterion"],
        constraints=["constraint"],
        inputs={},
    )
    manifest = RunManifest(
        run_id="run-1",
        task_id="task",
        task_file="task.yaml",
        status="running",
        provider="openai",
        model="gpt-5.1",
        worktree_path=".worktrees/run-1",
    )
    result = RunResult(
        plan_summary="planner text should stay out of the review packet",
        implementation_summary="implementation summary",
        tool_results=[],
    )
    packet = build_review_packet(task, manifest, result, "# handoff")
    assert "plan_summary" not in packet
    assert packet["implementation_summary"] == "implementation summary"
