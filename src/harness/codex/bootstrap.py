from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from tomlkit import dumps, item, parse, table
from tomlkit.exceptions import ParseError


@dataclass
class CodexBootstrapResult:
    ok: bool
    changed: bool
    message: str
    config_path: Path
    backup_path: Path | None = None


class CodexBootstrapService:
    def __init__(self, repo_root: Path, codex_home: Path | None = None) -> None:
        self.repo_root = repo_root.resolve()
        base = codex_home or Path(os.getenv("CODEX_HOME", Path.home() / ".codex"))
        self.codex_home = Path(base).expanduser()
        self.config_path = self.codex_home / "config.toml"

    def check(self) -> CodexBootstrapResult:
        document = self._load_document()
        message = self._status_message(document)
        return CodexBootstrapResult(
            ok=self._repo_entry_is_trusted(document),
            changed=False,
            message=message,
            config_path=self.config_path,
        )

    def apply(self) -> CodexBootstrapResult:
        document = self._load_document()
        backup_path = self._backup()
        changed = self._ensure_repo_entry(document)
        self.config_path.write_text(dumps(document))
        message = (
            "Codex project entry already configured for this repo."
            if not changed
            else "Configured Codex project trust for this repo."
        )
        return CodexBootstrapResult(
            ok=True,
            changed=changed,
            message=message,
            config_path=self.config_path,
            backup_path=backup_path,
        )

    def _load_document(self):
        if not self.config_path.exists():
            raise RuntimeError(
                f"Missing Codex config at {self.config_path}. Create it first and re-run bootstrap."
            )
        try:
            return parse(self.config_path.read_text())
        except ParseError as exc:
            raise RuntimeError(
                f"Could not parse {self.config_path}; refusing to modify it."
            ) from exc

    def _backup(self) -> Path:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_path = self.config_path.with_suffix(f".toml.bak.{timestamp}")
        shutil.copy2(self.config_path, backup_path)
        return backup_path

    def _status_message(self, document) -> str:
        if self._repo_entry_is_trusted(document):
            return "Codex project entry is present and trusted."
        return "Codex project entry is missing or not trusted."

    def _repo_entry_is_trusted(self, document) -> bool:
        projects = document.get("projects")
        if projects is None:
            return False
        repo_entry = projects.get(str(self.repo_root))
        if repo_entry is None:
            return False
        if not hasattr(repo_entry, "get"):
            raise RuntimeError("Unsupported Codex config schema: repo entry is not a table.")
        return repo_entry.get("trust_level") == "trusted"

    def _ensure_repo_entry(self, document) -> bool:
        projects = document.get("projects")
        if projects is None:
            projects = table()
            document["projects"] = projects
        if not hasattr(projects, "get"):
            raise RuntimeError("Unsupported Codex config schema: [projects] is not a table.")

        repo_key = str(self.repo_root)
        existing = projects.get(repo_key)
        if existing is None:
            projects[repo_key] = item({"trust_level": "trusted"})
            return True
        if not hasattr(existing, "get"):
            raise RuntimeError("Unsupported Codex config schema: repo entry is not a table.")
        if existing.get("trust_level") == "trusted":
            return False
        existing["trust_level"] = "trusted"
        return True
