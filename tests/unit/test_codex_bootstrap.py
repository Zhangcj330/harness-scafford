from __future__ import annotations

import tomllib

from harness.codex.bootstrap import CodexBootstrapService


def test_codex_bootstrap_apply_preserves_existing_settings(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    config_path = codex_home / "config.toml"
    config_path.write_text(
        """
personality = "pragmatic"
model = "gpt-5.4"
[projects."/Users/user"]
trust_level = "untrusted"
"""
    )

    service = CodexBootstrapService(repo_root=repo, codex_home=codex_home)
    check = service.check()
    assert check.ok is False

    result = service.apply()
    assert result.ok is True
    assert result.changed is True
    assert result.backup_path is not None
    assert result.backup_path.exists()

    payload = tomllib.loads(config_path.read_text())
    assert payload["model"] == "gpt-5.4"
    assert payload["projects"]["/Users/user"]["trust_level"] == "untrusted"
    assert payload["projects"][str(repo)]["trust_level"] == "trusted"

    second = service.apply()
    assert second.ok is True
    assert second.changed is False


def test_codex_bootstrap_check_fails_when_config_missing(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()

    service = CodexBootstrapService(repo_root=repo, codex_home=codex_home)
    try:
        service.check()
    except RuntimeError as exc:
        assert "Missing Codex config" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected bootstrap check to fail without config")
