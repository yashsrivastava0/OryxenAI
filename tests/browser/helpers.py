"""Helpers shared by the browser tests."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

import pytest

playwright = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright.sync_playwright
expect = playwright.expect

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = REPO_ROOT / "frontend"
BASE_URL = "http://127.0.0.1:4178"


def assert_no_horizontal_overflow(page: object) -> None:
    details = page.evaluate(
        """() => ({
          ok: document.documentElement.scrollWidth <= window.innerWidth,
          width: window.innerWidth,
          scrollWidth: document.documentElement.scrollWidth,
          offenders: Array.from(document.querySelectorAll('*')).map((element) => {
            const rect = element.getBoundingClientRect();
            return { tag: element.tagName, className: element.className, right: rect.right, width: rect.width };
          }).filter((item) => typeof item.className === 'string' && item.right > window.innerWidth + 1).slice(0, 8),
        })""",
    )
    assert details["ok"], details


def _sample_bundle() -> tuple[object, object]:
    from tests.unit.agents.code_generator.helpers import sample_content

    from oryxenai.agents.code_generator.bundle import build_bundle
    from oryxenai.agents.code_generator.dev.reference_renderer import render_body
    from oryxenai.themes import get_theme

    theme = get_theme()
    content = sample_content("01_strong_profile")
    derived = theme.contract.derive(content)
    return build_bundle(content, derived, render_body(content, derived), "en", theme), theme


def install_sample_page(page: object) -> None:
    """Serve a real generated page at /studio-sample/ with the production preview headers."""
    from oryxenai.agents.code_generator.serving import preview_headers

    sealed, theme = _sample_bundle()

    def handle(route: object) -> None:
        path = urlparse(route.request.url).path.removeprefix("/studio-sample/") or "index.html"  # type: ignore[attr-defined]
        if path == "index.html":
            body = sealed.index_html.encode("utf-8")  # type: ignore[attr-defined]
            headers = {**preview_headers(html=True), "content-type": "text/html; charset=utf-8"}
        else:
            entry = theme.file(path)  # type: ignore[attr-defined]
            if entry is None:
                route.fulfill(status=404, body="not found")  # type: ignore[attr-defined]
                return
            body = entry.data
            headers = {
                **preview_headers(html=False, etag=entry.sha256),
                "content-type": entry.media_type,
            }
        route.fulfill(status=200, body=body, headers=headers)  # type: ignore[attr-defined]

    page.route("**/studio-sample/**", handle)  # type: ignore[attr-defined]


def shot(page: object, name: str) -> None:
    folder = os.environ.get("STUDIO_SCREENSHOT_DIR")
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(folder) / f"{name}.png"))  # type: ignore[attr-defined]
