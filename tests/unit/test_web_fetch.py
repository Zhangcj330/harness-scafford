from __future__ import annotations

import ssl
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

import certifi
import httpx

from harness.tools.web_fetch import WebFetchTool


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        body = (
            b"<html><head><title>Fixture Page</title></head>"
            b"<body><main>Hello harness</main></body></html>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def test_web_fetch_extracts_title_and_excerpt(tmp_path) -> None:
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        tool = WebFetchTool()
        result = tool.fetch(f"http://127.0.0.1:{server.server_port}", artifact_dir=tmp_path)
        assert result.ok is True
        assert result.data["title"] == "Fixture Page"
        assert "Hello harness" in result.data["excerpt"]
    finally:
        server.shutdown()
        thread.join()


def test_web_fetch_uses_certifi_bundle(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    class _Response:
        headers = {"content-type": "text/html"}
        text = "<html><head><title>Fixture Page</title></head><body>hi</body></html>"

        def raise_for_status(self) -> None:
            return

    class _Context:
        pass

    def fake_context(
        *,
        cafile: str | None = None,
        capath: str | None = None,
        cadata=None,
    ) -> _Context:
        captured["cafile"] = cafile
        return _Context()

    def fake_get(url: str, **kwargs: object) -> _Response:
        captured["url"] = url
        captured["verify"] = kwargs.get("verify")
        return _Response()

    monkeypatch.setattr(ssl, "create_default_context", fake_context)
    monkeypatch.setattr(httpx, "get", fake_get)

    result = WebFetchTool().fetch("https://example.com", artifact_dir=tmp_path)

    assert result.ok is True
    assert captured["cafile"] == certifi.where()
    assert isinstance(captured["verify"], _Context)


def test_web_fetch_falls_back_to_curl(monkeypatch, tmp_path) -> None:
    def fake_get(url: str, **kwargs: object):
        raise httpx.ConnectError("ssl failed")

    def fake_which(name: str) -> str | None:
        return "/usr/bin/curl" if name == "curl" else None

    def fake_run(command, **kwargs):
        headers_path = Path(command[command.index("-D") + 1])
        output_path = Path(command[command.index("-o") + 1])
        headers_path.write_text("content-type: text/html; charset=utf-8\n")
        output_path.write_text(
            "<html><head><title>Fixture Page</title></head><body>Hello curl</body></html>"
        )
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr("harness.tools.web_fetch.shutil.which", fake_which)
    monkeypatch.setattr("harness.tools.web_fetch.subprocess.run", fake_run)

    result = WebFetchTool().fetch("https://example.com", artifact_dir=tmp_path)

    assert result.ok is True
    assert result.data["transport"] == "curl"
    assert result.data["title"] == "Fixture Page"
