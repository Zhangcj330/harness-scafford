from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    name: str = "openai"
    model: str = "gpt-5.1"
    timeout_seconds: int = 120


class BudgetsConfig(BaseModel):
    max_steps: int = 6
    max_tool_calls: int = 12
    max_runtime_seconds: int = 900


class ToolPolicyConfig(BaseModel):
    allow_shell: bool = True
    allow_fs: bool = True
    allow_git: bool = True
    allow_tests: bool = True
    allow_web_fetch: bool = True
    allow_web_search: bool = True
    allow_browser: bool = True
    allow_code_exec: bool = True


class ObservabilityConfig(BaseModel):
    service_name: str = "harness-scaffold"
    otlp_endpoint: str | None = "http://localhost:4318/v1/traces"
    prometheus_port: int = 9108
    grafana_base_url: str = "http://localhost:3000"
    loki_base_url: str = "http://localhost:3100"
    tempo_base_url: str = "http://localhost:3200"
    prometheus_base_url: str = "http://localhost:9090"


class PathsConfig(BaseModel):
    runs_dir: Path = Path(".runs")
    worktrees_dir: Path = Path(".worktrees")
    db_path: Path = Path(".runs/index.db")
    tasks_dir: Path = Path("tasks")
    memory_dir: Path = Path("memory")


class RuntimeConfig(BaseModel):
    checkpoint_every_steps: int = 1


class HarnessConfig(BaseModel):
    repo_root: Path
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    budgets: BudgetsConfig = Field(default_factory=BudgetsConfig)
    tool_policy: ToolPolicyConfig = Field(default_factory=ToolPolicyConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)

    @property
    def runs_dir(self) -> Path:
        return self._resolve(self.paths.runs_dir)

    @property
    def worktrees_dir(self) -> Path:
        return self._resolve(self.paths.worktrees_dir)

    @property
    def db_path(self) -> Path:
        return self._resolve(self.paths.db_path)

    @property
    def tasks_dir(self) -> Path:
        return self._resolve(self.paths.tasks_dir)

    @property
    def memory_dir(self) -> Path:
        return self._resolve(self.paths.memory_dir)

    def _resolve(self, path: Path) -> Path:
        return path if path.is_absolute() else self.repo_root / path

    @classmethod
    def load(cls, path: Path | None = None, repo_root: Path | None = None) -> HarnessConfig:
        root = (repo_root or Path.cwd()).resolve()
        config_path = path or root / "harness.toml"
        raw: dict[str, object] = {}
        if config_path.exists():
            raw = tomllib.loads(config_path.read_text())
        raw["repo_root"] = root
        return cls.model_validate(raw)
