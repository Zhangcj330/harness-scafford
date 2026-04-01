from pathlib import Path

import harness.tools.browser as browser_module
from harness.tools.browser import BrowserTool


class _FakeBody:
    def inner_text(self, timeout: int = 5000) -> str:
        return "browser body"


class _FakePage:
    def goto(self, url: str, wait_until: str, timeout: int) -> None:
        return

    def screenshot(self, path: str, full_page: bool) -> None:
        Path(path).write_bytes(b"png")

    def locator(self, selector: str) -> _FakeBody:
        return _FakeBody()


class _FakeBrowser:
    def new_page(self, viewport: dict[str, int]) -> _FakePage:
        return _FakePage()

    def close(self) -> None:
        return


class _FakeChromium:
    def launch(self, headless: bool) -> _FakeBrowser:
        return _FakeBrowser()


class _PlaywrightContext:
    chromium = _FakeChromium()

    def __enter__(self) -> "_PlaywrightContext":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return


def test_browser_capture_writes_artifacts(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        browser_module,
        "sync_playwright",
        lambda: _PlaywrightContext(),
        raising=False,
    )
    result = BrowserTool().capture("https://example.com", artifact_dir=tmp_path)
    assert result.ok is True
    assert (tmp_path / "browser.png").exists()
    assert (tmp_path / "dom.txt").read_text() == "browser body"
