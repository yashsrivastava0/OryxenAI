from __future__ import annotations

import shutil
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright.sync_playwright
expect = playwright.expect

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = REPO_ROOT / "frontend"
BASE_URL = "http://127.0.0.1:4178"
VIEWPORTS = [(1536, 695), (1366, 768), (768, 1024), (390, 844)]


@pytest.fixture(scope="module")
def browser_page() -> Iterator[object]:
    node_executable = shutil.which("node")
    if node_executable is None:
        pytest.skip("Node.js is required for the browser remediation fixture")
    # The executable is resolved from PATH and the script/config are checked-in
    # repository files owned by this test fixture.
    server = subprocess.Popen(  # noqa: S603
        [
            node_executable,
            "node_modules/vite/bin/vite.js",
            "--config",
            "vite.browser-test.config.ts",
        ],
        cwd=FRONTEND_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    try:
        with sync_playwright() as playwright_instance:
            browser = playwright_instance.chromium.launch(headless=True)
            page = browser.new_page()
            for _ in range(50):
                try:
                    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=500)
                    break
                except Exception:
                    time.sleep(0.1)
            else:
                pytest.fail("Vite browser fixture did not become ready")
            yield page
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=5)


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


@pytest.mark.parametrize("width,height", VIEWPORTS)
def test_required_viewports_keep_stage_actions_visible(
    browser_page: object, width: int, height: int
) -> None:
    page = browser_page
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{BASE_URL}/?fixture=content-review", wait_until="networkidle")
    assert page.get_by_role("heading", name="Three routes. A stronger story ahead.").is_visible()
    assert page.get_by_role("button", name="Approve & continue").is_visible()
    assert_no_horizontal_overflow(page)


def test_mobile_uses_compact_selector_and_locked_options(browser_page: object) -> None:
    page = browser_page
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{BASE_URL}/?fixture=content-review", wait_until="networkidle")
    selector = page.get_by_label("Current portfolio stage")
    assert selector.is_visible()
    options = selector.locator("option")
    assert options.count() == 2
    assert options.nth(0).inner_text().startswith("1. Discover")
    assert options.nth(1).inner_text().startswith("2. Content")
    assert options.nth(0).is_enabled()
    assert options.nth(1).is_enabled()
    assert page.locator(".journey-rail").is_hidden()
    assert_no_horizontal_overflow(page)


def test_discovery_intake_keeps_prompts_above_reserved_actions(browser_page: object) -> None:
    page = browser_page
    page.set_viewport_size({"width": 1366, "height": 768})
    page.goto(f"{BASE_URL}/?fixture=discovery-input", wait_until="networkidle")
    assert page.get_by_text("0 / 3,000 words").is_visible()
    assert page.get_by_text("Your input is private and secure.").is_visible()
    assert page.get_by_text("A deeper conversation for a more intentional future.").count() == 0
    prompt_box = page.locator(".starting-points-grid").bounding_box()
    dock_box = page.locator(".intake-dock").bounding_box()
    assert prompt_box and dock_box
    assert dock_box["y"] >= prompt_box["y"] + prompt_box["height"]
    assert_no_horizontal_overflow(page)


def test_developer_inspector_is_opt_in_and_drawer_is_accessible(browser_page: object) -> None:
    page = browser_page
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{BASE_URL}/?fixture=content-review", wait_until="networkidle")
    assert page.get_by_role("button", name="Inspector").count() == 0
    page.goto(f"{BASE_URL}/?fixture=content-review&inspector=1", wait_until="networkidle")
    page.get_by_role("button", name="Inspector").click()
    drawer = page.get_by_role("dialog", name="Output Inspector")
    expect(drawer).to_be_visible()
    page.keyboard.press("Escape")
    expect(drawer).to_be_hidden()
