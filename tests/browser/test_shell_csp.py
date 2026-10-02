"""The production shell's CSP must let the Studio work: CSSOM styles and the sandboxed frame."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from tests.browser.helpers import expect

from oryxenai.agents.code_generator.serving import preview_headers
from oryxenai.auth.web import auth_csp

ORIGIN = "http://shell.test"
PAGE = (
    "<!doctype html><title>shell</title><div id=box>x</div>"
    "<iframe id=frame title=preview src='/frame.html' "
    "sandbox='allow-popups allow-popups-to-escape-sandbox'></iframe>"
    "<script src='/t.js'></script>"
)
SCRIPT = (
    "const box = document.getElementById('box');"
    "box.style.width = '123px'; box.style.transform = 'scale(0.5)';"  # what Preact does
    "document.body.dataset.cssom = getComputedStyle(box).width;"
    "box.setAttribute('style', 'width: 99px');"  # an inline style attribute: forbidden
    "document.body.dataset.attribute = getComputedStyle(box).width;"
)


def test_preact_style_updates_work_and_the_same_origin_sandboxed_preview_frame_loads(
    browser_page: Any,
) -> None:
    page = browser_page
    page.unroute_all()
    shell_headers = {"content-security-policy": auth_csp("https://project.supabase.co")}

    def handle(route: Any) -> None:
        path = urlparse(route.request.url).path
        if path == "/":
            route.fulfill(
                status=200, body=PAGE, headers={**shell_headers, "content-type": "text/html"}
            )
        elif path == "/t.js":
            route.fulfill(status=200, body=SCRIPT, headers={"content-type": "text/javascript"})
        elif path == "/frame.html":
            route.fulfill(
                status=200,
                body="<!doctype html><title>p</title><p>hello from the preview</p>",
                headers={**preview_headers(html=True), "content-type": "text/html; charset=utf-8"},
            )
        else:
            route.fulfill(status=404, body="")

    page.route(f"{ORIGIN}/**", handle)
    page.goto(f"{ORIGIN}/", wait_until="load")
    expect(page.frame_locator("#frame").locator("p")).to_have_text("hello from the preview")
    assert page.evaluate("document.body.dataset.cssom") == "123px"
    # The production CSP blocks inline style *attributes*; the CSSOM route above is what the app uses.
    assert page.evaluate("document.body.dataset.attribute") == "123px"
