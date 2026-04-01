from __future__ import annotations

import argparse
import os
from pathlib import Path

from harness.config import HarnessConfig
from harness.orchestrator.runner import RunService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a harness smoke test.")
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("harness.toml"))
    parser.add_argument("--resume-if-paused", action="store_true")
    parser.add_argument("--require-live-provider", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.require_live_provider and "OPENAI_API_KEY" not in os.environ:
        raise SystemExit("OPENAI_API_KEY is required for this smoke run.")
    config = HarnessConfig.load(path=args.config, repo_root=Path.cwd())
    service = RunService(config)
    manifest = service.run(args.task)
    if args.resume_if_paused and manifest.status == "paused":
        manifest = service.resume(manifest.run_id)
    if manifest.status not in {"completed", "reviewed"}:
        raise SystemExit(f"Smoke run ended in unexpected status: {manifest.status}")
    print(manifest.run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
