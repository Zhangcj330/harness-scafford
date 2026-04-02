from __future__ import annotations

import subprocess

import pytest

from harness.agents.provider import OpenAIProvider, ProviderUnavailableError


def test_provider_falls_back_to_codex_cli_when_openai_key_missing(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        "harness.agents.provider.shutil.which", lambda name: "/opt/homebrew/bin/codex"
    )

    def fake_run(command, **kwargs):
        output_path = command[command.index("-o") + 1]
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write("codex reply\n")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("harness.agents.provider.subprocess.run", fake_run)
    provider = OpenAIProvider("gpt-5.1", repo_root=tmp_path, timeout_seconds=5)

    result = provider.complete("system", "user")

    assert result == "codex reply"


def test_provider_raises_when_no_provider_is_available(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("harness.agents.provider.shutil.which", lambda name: None)
    provider = OpenAIProvider("gpt-5.1", repo_root=tmp_path, timeout_seconds=5)

    with pytest.raises(ProviderUnavailableError):
        provider.complete("system", "user")
