from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "AGENTS.md"
REQUIRED_STRINGS = [
    "uv sync --extra dev",
    'uv run pytest -m "not live"',
    "docs/index.md",
    "docs/architecture.md",
    "docs/operations.md",
]


def main() -> int:
    agents_text = AGENTS.read_text()
    missing = [item for item in REQUIRED_STRINGS if item not in agents_text]
    if missing:
        raise SystemExit(f"AGENTS.md is missing required references: {missing}")

    markdown_files = [AGENTS, *ROOT.glob("docs/**/*.md"), ROOT / "README.md"]
    internal_targets: list[Path] = []
    for path in markdown_files:
        text = path.read_text()
        for target in re.findall(r"\(([^)]+)\)", text):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            internal_targets.append((path.parent / target).resolve())
    not_found = [str(path) for path in internal_targets if not path.exists()]
    if not_found:
        raise SystemExit(f"Broken internal markdown links: {not_found}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
