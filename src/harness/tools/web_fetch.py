from __future__ import annotations

import json
import re
import shutil
import ssl
import subprocess
from pathlib import Path

import certifi
import httpx
from bs4 import BeautifulSoup
from readability import Document

from harness.tools.base import ToolResult


class WebFetchTool:
    def fetch(self, url: str, artifact_dir: Path, timeout_seconds: int = 30) -> ToolResult:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = artifact_dir / "response.txt"
        transport = "httpx"
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            response = httpx.get(
                url,
                follow_redirects=True,
                timeout=timeout_seconds,
                verify=ssl_context,
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            text = response.text
        except httpx.HTTPError as exc:
            curl_payload = self._fetch_with_curl(
                url=url,
                artifact_path=artifact_path,
                timeout_seconds=timeout_seconds,
            )
            if curl_payload is None:
                return ToolResult(
                    tool="web_fetch",
                    ok=False,
                    summary=f"Failed to fetch {url}",
                    data={"url": url, "error": str(exc)},
                )
            transport = "curl"
            content_type = curl_payload["content_type"]
            text = curl_payload["text"]
        title = url
        excerpt = text[:280]

        if "html" in content_type:
            doc = Document(text)
            title = doc.short_title() or url
            summary_html = doc.summary()
            excerpt = BeautifulSoup(summary_html, "html.parser").get_text(" ", strip=True)
            excerpt = re.sub(r"\s+", " ", excerpt)[:280]

        artifact_path.write_text(text)
        metadata_path = artifact_dir / "web_fetch.meta.json"
        metadata_path.write_text(
            json.dumps(
                {"url": url, "title": title, "excerpt": excerpt, "transport": transport},
                indent=2,
                sort_keys=True,
            )
        )
        return ToolResult(
            tool="web_fetch",
            ok=True,
            summary=f"Fetched {title}",
            data={
                "url": url,
                "title": title,
                "excerpt": excerpt,
                "content_type": content_type,
                "transport": transport,
            },
            artifact_paths=[str(artifact_path), str(metadata_path)],
        )

    def _fetch_with_curl(
        self,
        *,
        url: str,
        artifact_path: Path,
        timeout_seconds: int,
    ) -> dict[str, str] | None:
        curl_path = shutil.which("curl")
        if not curl_path:
            return None
        headers_path = artifact_path.with_suffix(".headers.txt")
        completed = subprocess.run(
            [
                curl_path,
                "-fsSL",
                "--compressed",
                "--max-time",
                str(timeout_seconds),
                "-D",
                str(headers_path),
                "-o",
                str(artifact_path),
                url,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0 or not artifact_path.exists():
            return None
        content_type = ""
        if headers_path.exists():
            for line in headers_path.read_text().splitlines():
                if line.lower().startswith("content-type:"):
                    content_type = line.split(":", 1)[1].strip()
        return {"text": artifact_path.read_text(), "content_type": content_type}
