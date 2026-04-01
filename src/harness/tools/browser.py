from __future__ import annotations

from pathlib import Path

from harness.tools.base import ToolResult

try:  # pragma: no cover - depends on optional runtime state
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - import path depends on environment
    sync_playwright = None


class BrowserTool:
    def capture(self, url: str, artifact_dir: Path) -> ToolResult:
        if sync_playwright is None:
            return ToolResult(
                tool="browser",
                ok=False,
                summary="Playwright is not available",
                data={"url": url, "error": "playwright import failed"},
            )

        artifact_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = artifact_dir / "browser.png"
        dom_path = artifact_dir / "dom.txt"
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.screenshot(path=str(screenshot_path), full_page=True)
                dom_excerpt = page.locator("body").inner_text(timeout=5000)[:1200]
                dom_path.write_text(dom_excerpt)
                browser.close()
        except Exception as exc:
            return ToolResult(
                tool="browser",
                ok=False,
                summary="Browser capture failed",
                data={"url": url, "error": str(exc)},
            )
        return ToolResult(
            tool="browser",
            ok=True,
            summary=f"Captured browser state for {url}",
            data={"url": url, "dom_excerpt": dom_path.read_text()},
            artifact_paths=[str(screenshot_path), str(dom_path)],
        )
