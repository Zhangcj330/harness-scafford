from __future__ import annotations

from pathlib import Path

from harness.tools.base import ToolResult


class FsTool:
    def read_text(self, path: Path) -> ToolResult:
        return ToolResult(
            tool="fs",
            ok=path.exists(),
            summary=f"Read {path}" if path.exists() else f"Missing file: {path}",
            data={"path": str(path), "content": path.read_text() if path.exists() else ""},
        )

    def list_dir(self, path: Path) -> ToolResult:
        if not path.exists():
            return ToolResult(tool="fs", ok=False, summary=f"Missing path: {path}", data={})
        return ToolResult(
            tool="fs",
            ok=True,
            summary=f"Listed {path}",
            data={"path": str(path), "entries": sorted(item.name for item in path.iterdir())},
        )
