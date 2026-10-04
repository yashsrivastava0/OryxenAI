"""Inspect the real sign-in template and local assets at desktop and phone sizes."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader
from tests.browser.helpers import BASE_URL, REPO_ROOT, assert_no_horizontal_overflow, expect, shot

AUTH_STATIC = REPO_ROOT / "src" / "oryxenai" / "auth" / "static"


def _sign_in_html() -> str:
    templates = REPO_ROOT / "src" / "oryxenai" / "auth" / "templates"
    env = Environment(loader=FileSystemLoader(templates), autoescape=True)
    return env.get_template("auth_shell.html").render(
        app_name="OryxenAI", page="sign-in", auth_config={}
    )


def test_sign_in_three_stage_showcase_is_legible_and_responsive(browser_page: object) -> None:
    page = browser_page
    html = _sign_in_html()

    def asset(route: object) -> None:
        name = Path(urlparse(route.request.url).path).name  # type: ignore[attr-defined]
        path = AUTH_STATIC / name
        if not path.is_file():
            route.fulfill(status=404, body="not found")  # type: ignore[attr-defined]
            return
        # Identity bootstrapping is outside this visual check; the showcase
        # controller remains live so its stage/card pairing is exercised.
        if name in {"auth-page.mjs", "auth-admin.mjs", "auth-client.js"}:
            route.fulfill(status=200, body="", content_type="text/javascript")  # type: ignore[attr-defined]
            return
        route.fulfill(  # type: ignore[attr-defined]
            status=200,
            body=path.read_bytes(),
            content_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        )

    page.route(f"{BASE_URL}/auth-static/**", asset)  # type: ignore[attr-defined]
    page.route(  # type: ignore[attr-defined]
        f"{BASE_URL}/sign-in",
        lambda route: route.fulfill(status=200, body=html, content_type="text/html"),
    )
    page.set_viewport_size({"width": 1366, "height": 768})  # type: ignore[attr-defined]
    page.goto(f"{BASE_URL}/sign-in", wait_until="networkidle")  # type: ignore[attr-defined]
    expect(page.get_by_text("THREE STEPS, EACH IN YOUR HANDS")).to_be_visible()
    assert page.locator(".stage-rail-node").count() == 3  # type: ignore[attr-defined]
    assert page.locator(".showcase-card").count() == 4  # type: ignore[attr-defined]
    page.get_by_role("tab", name="Studio preview card").click()
    expect(page.get_by_text("See the page. Make it yours.")).to_be_visible()
    assert "active" in (
        page.locator('.stage-rail-node[data-stage="studio"]').get_attribute("class") or ""
    )
    page.wait_for_timeout(650)  # Let the showcase's existing card transition finish.
    page.evaluate("window.scrollTo(0, 0)")
    assert_no_horizontal_overflow(page)
    shot(page, "sign-in-desktop")
    page.set_viewport_size({"width": 390, "height": 844})  # type: ignore[attr-defined]
    page.evaluate("window.scrollTo(0, 0)")
    assert_no_horizontal_overflow(page)
    shot(page, "sign-in-mobile")
