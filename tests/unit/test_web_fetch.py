from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

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
