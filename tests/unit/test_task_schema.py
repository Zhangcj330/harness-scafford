from pathlib import Path

from harness.schemas.task import load_task


def test_example_task_is_valid() -> None:
    task = load_task(Path("examples/tasks/offline-smoke.yaml"))
    assert task.goal
    assert task.acceptance_criteria
    assert task.inputs["task_id"] == "offline-smoke"
