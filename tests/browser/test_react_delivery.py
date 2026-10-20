"""Real React rendering, theme visual parity and MCP Apps bridge interactions."""

from __future__ import annotations

import base64
import io
import json
import mimetypes
import re
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from PIL import Image, ImageChops
from tests.browser.helpers import assert_no_horizontal_overflow, expect, sync_playwright
from tests.unit.agents.code_generator.helpers import minimal_content
from tests.unit.test_react_delivery import long_content
from tests.unit.themes.atlas_fixtures import designer

from oryxenai.agents.code_generator.bundle import build_bundle
from oryxenai.delivery.contracts import sha256
from oryxenai.delivery.project import SUPPORTED_THEMES, TEMPLATES, assemble_project
from oryxenai.themes import get_theme

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def react_browser():
    state = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, data, content_type="text/html"):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            route = urlsplit(self.path).path
            if route == "/":
                self.send(
                    b'<!doctype html><html><head><base href="/fixture/"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/browser.css"></head><body><div id="root"></div><script type="module" src="/browser.js"></script></body></html>'
                )
            elif route == "/app":
                self.send(
                    b'<!doctype html><html><body><iframe title="React portfolio" style="width:100%;height:800px;border:0"></iframe><script type="module" src="/app-host.js"></script></body></html>'
                )
            elif route == "/viewer":
                self.send((TEMPLATES / "viewer.html").read_bytes())
            elif route == "/app-manifest":
                self.send(json.dumps(state["manifest"]).encode(), "application/json")
            elif route in {"/browser.js", "/browser.css", "/app-host.js"}:
                self.send(
                    (ROOT / ".workspace/react-tests" / route[1:]).read_bytes(),
                    "text/css" if route.endswith("css") else "application/javascript",
                )
            elif route.startswith("/original/"):
                relative = route.removeprefix("/original/")
                if not relative:
                    self.send(state["original"].encode())
                else:
                    asset = state["theme"].files.get(relative)
                    if asset:
                        self.send(asset.data, asset.media_type)
                    else:
                        self.send_error(404)
            elif route.startswith("/fixture/"):
                relative = route.removeprefix("/fixture/")
                key = "public/" + relative if relative.startswith("theme/") else relative
                data = state["project"].files.get(key)
                if data is not None:
                    self.send(data, mimetypes.guess_type(key)[0] or "application/octet-stream")
                else:
                    self.send_error(404)
            else:
                self.send_error(404)

        def do_POST(self):
            args = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert args["name"] == "read_preview_asset"
            values = args["arguments"]
            assert values["path"] == "portfolio.json" or values["path"].startswith("public/theme/")
            data = state["project"].files[values["path"]]
            offset = values["cursor"]
            chunk = data[offset : offset + 32768]
            result = {
                "content": [],
                "structuredContent": {
                    "data": base64.b64encode(chunk).decode(),
                    "offset": offset,
                    "chunk_sha256": sha256(chunk),
                    "next_cursor": offset + len(chunk) if offset + len(chunk) < len(data) else None,
                },
            }
            self.send(json.dumps(result).encode(), "application/json")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception:
            browser = playwright.chromium.launch(headless=True, channel="chrome")
        page = browser.new_page(color_scheme="light", reduced_motion="reduce")

        def load(theme_id, content):
            theme = get_theme(theme_id)
            state["theme"] = theme
            state["project"] = assemble_project(
                content, theme_id, theme.css_sha256, "a" * 64, max_bytes=10485760
            )
            c = state["project"].portfolio["c"]
            derived = theme.contract.derive(c)
            state["original"] = build_bundle(
                c, derived, theme.contract.render_body(c, derived), "en", theme
            ).index_html
            state["manifest"] = {
                "files": [
                    {"path": name, "bytes": len(data), "sha256": sha256(data)}
                    for name, data in state["project"].files.items()
                ],
                "expires_at": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
            }

        yield page, f"http://127.0.0.1:{server.server_port}", load
        browser.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


@pytest.mark.parametrize("theme_id", sorted(SUPPORTED_THEMES))
@pytest.mark.parametrize("fixture", [minimal_content, designer, long_content])
@pytest.mark.parametrize("width", [390, 1440])
def test_react_theme_responsive_render_and_visual_parity(react_browser, theme_id, fixture, width):
    page, base, load = react_browser
    load(theme_id, fixture())
    page.set_viewport_size({"width": width, "height": 900})
    errors = []

    def handler(error):
        errors.append(error)

    page.on("pageerror", handler)
    try:
        page.goto(base, wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        expect(page.locator("h1:visible").first).to_be_visible()
        assert_no_horizontal_overflow(page)
        hero = page.locator(".hero").first
        if not hero.count():
            hero = page.locator("main").first
        react_image = Image.open(io.BytesIO(hero.screenshot(animations="disabled"))).convert("RGB")
        page.goto(base + "/original/", wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        original_hero = page.locator(".hero").first
        if not original_hero.count():
            original_hero = page.locator("main").first
        original_image = Image.open(
            io.BytesIO(original_hero.screenshot(animations="disabled"))
        ).convert("RGB")
        assert react_image.size == original_image.size
        difference = ImageChops.difference(react_image, original_image)
        mean = sum(
            sum(
                channel * count
                for channel, count in enumerate(difference.histogram()[start : start + 256])
            )
            for start in (0, 256, 512)
        ) / (react_image.width * react_image.height * 3 * 255)
        if mean >= 0.015:
            react_image.save(ROOT / ".workspace/react-tests/react.png")
            original_image.save(ROOT / ".workspace/react-tests/original.png")
        assert mean < 0.015, f"Hero visual difference {mean:.4%}"
        assert not errors, errors
    finally:
        page.remove_listener("pageerror", handler)


def test_atlas_react_navigation_dialog_keyboard_and_mobile_menu(react_browser):
    page, base, load = react_browser
    load("cobalt-atlas/v2", designer())
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(base, wait_until="networkidle")
    page.locator(".site-nav a[href='#about']").click()
    expect(page.locator("#about")).to_be_visible()
    expect(page.locator("#home")).to_be_hidden()
    page.keyboard.press("Control+k")
    expect(page.get_by_role("dialog", name="Quick navigation")).to_be_visible()
    page.get_by_role("textbox", name="Search pages").fill("Home")
    page.keyboard.press("Enter")
    expect(page.locator("#home")).to_be_visible()
    expect(page.get_by_role("dialog")).to_be_hidden()
    page.locator("a.project-card").first.click()
    expect(page.locator("#case-1")).to_be_visible()
    page.go_back()
    expect(page.locator("#home")).to_be_visible()
    page.set_viewport_size({"width": 390, "height": 850})
    page.get_by_role("button", name="Toggle navigation").click()
    expect(page.locator(".site-nav")).to_be_visible()
    page.locator(".site-nav a[href='#about']").click()
    expect(page.locator("#about")).to_be_visible()
    expect(page.get_by_role("button", name="Toggle navigation")).to_have_attribute(
        "aria-expanded", "false"
    )


def test_mcp_app_renders_actual_react_components_via_app_only_assets(react_browser):
    page, base, load = react_browser
    page.set_viewport_size({"width": 1440, "height": 900})
    load("cobalt-atlas/v2", designer())
    page.goto(base + "/app", wait_until="networkidle")
    frame = page.frame_locator("iframe")
    expect(frame.locator(".react-portfolio h1:visible").first).to_be_visible(timeout=30000)
    frame.locator(".site-nav a[href='#about']").click()
    expect(frame.locator("#about")).to_be_visible()
    assert frame.locator("script[src$='theme.js']").count() == 0


@pytest.mark.parametrize(
    "theme_id,query", [("cobalt-atlas/v2", "atlas-motion=1"), ("claret-marquee/v1", "motion=1")]
)
def test_motion_reveals_routes_pause_and_live_reduced_motion(react_browser, theme_id, query):
    page, base, load = react_browser
    load(theme_id, designer())
    page.set_viewport_size({"width": 1440, "height": 900})
    page.emulate_media(reduced_motion="no-preference")
    errors = []

    def handler(error):
        errors.append(error)

    page.on("pageerror", handler)
    try:
        page.goto(base + "?" + query, wait_until="networkidle")
        expect(page.locator("[class*='react-intro-']")).to_have_count(0, timeout=10000)
        expect(page.locator("h1:visible").first).to_be_visible()
        card = page.locator("a.project-card,a.work-link").first
        if not card.count():
            card = page.locator("a[href='#case-1']").first
        card.scroll_into_view_if_needed()
        if theme_id == "cobalt-atlas/v2":
            expect(card).to_have_class(re.compile(".*is-in-view.*"))
        card.click()
        expect(page.locator("#case-1")).to_be_visible()
        if theme_id == "claret-marquee/v1":
            page.get_by_role("button", name="Pause motion").click()
            expect(page.get_by_role("button", name="Pause motion")).to_have_attribute(
                "aria-pressed", "true"
            )
        page.emulate_media(reduced_motion="reduce")
        expect(page.locator("html")).to_have_attribute(
            "data-motion", "reduced" if theme_id == "claret-marquee/v1" else "off"
        )
        expect(page.locator("#case-1 h1")).to_be_visible()
        assert not errors, errors
    finally:
        page.remove_listener("pageerror", handler)
        page.emulate_media(reduced_motion="reduce")
