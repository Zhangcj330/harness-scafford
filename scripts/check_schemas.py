from __future__ import annotations

from pathlib import Path

from harness.schemas.task import load_task


def main() -> int:
    examples_dir = Path("examples/tasks")
    failures = []
    for path in examples_dir.glob("*.yaml"):
        try:
            load_task(path)
        except Exception as exc:  # pragma: no cover - CLI path
            failures.append(f"{path}: {exc}")
    if failures:
        raise SystemExit("\n".join(failures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
