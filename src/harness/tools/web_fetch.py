from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from readability import Document

from harness.tools.base import ToolResult


class WebFetchTool:
    def fetch(self, url: str, artifact_dir: Path, timeout_seconds: int = 30) -> ToolResult:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        try:
            response = httpx.get(url, follow_redirects=True, timeout=timeout_seconds)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return ToolResult(
                tool="web_fetch",
                ok=False,
                summary=f"Failed to fetch {url}",
                data={"url": url, "error": str(exc)},
            )
        content_type = response.headers.get("content-type", "")
        text = response.text
        title = url
        excerpt = text[:280]

        if "html" in content_type:
            doc = Document(text)
            title = doc.short_title() or url
            summary_html = doc.summary()
            excerpt = BeautifulSoup(summary_html, "html.parser").get_text(" ", strip=True)
            excerpt = re.sub(r"\s+", " ", excerpt)[:280]

        artifact_path = artifact_dir / "response.txt"
        artifact_path.write_text(text)
        metadata_path = artifact_dir / "web_fetch.meta.json"
        metadata_path.write_text(
            json.dumps({"url": url, "title": title, "excerpt": excerpt}, indent=2, sort_keys=True)
        )
        return ToolResult(
            tool="web_fetch",
            ok=True,
            summary=f"Fetched {title}",
            data={"url": url, "title": title, "excerpt": excerpt, "content_type": content_type},
            artifact_paths=[str(artifact_path), str(metadata_path)],
        )
