from typer.testing import CliRunner

from harness.cli.main import app


def test_dashboard_command_prints_url_and_starts_server(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(app_object, *, host: str, port: int, log_level: str) -> None:
        captured["app"] = app_object
        captured["host"] = host
        captured["port"] = port
        captured["log_level"] = log_level

    monkeypatch.setattr("harness.cli.main.uvicorn.run", fake_run)

    result = CliRunner().invoke(app, ["dashboard", "--host", "0.0.0.0", "--port", "9000"])

    assert result.exit_code == 0
    assert "Harness dashboard listening at http://0.0.0.0:9000" in result.output
    assert "Press Ctrl+C to stop." in result.output
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9000
    assert captured["log_level"] == "warning"
