from __future__ import annotations

import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright.sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = REPO_ROOT / "frontend"
BASE_URL = "http://127.0.0.1:4178"
VIEWPORTS = [(1536, 695), (1366, 768), (768, 1024), (390, 844)]


@pytest.fixture(scope="module")
def browser_page() -> Iterator[object]:
    server = subprocess.Popen(
        ["node", "node_modules/vite/bin/vite.js", "--config", "vite.browser-test.config.ts"],
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
def test_required_viewports_keep_stage_actions_visible(browser_page: object, width: int, height: int) -> None:
    page = browser_page
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{BASE_URL}/?fixture=content-review", wait_until="networkidle")
    assert page.get_by_role("heading", name="Content Strategy & Route Architecture").is_visible()
    assert page.get_by_role("button", name="Approve content plan").is_visible()
    assert_no_horizontal_overflow(page)


def test_mobile_uses_compact_selector_and_locked_options(browser_page: object) -> None:
    page = browser_page
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{BASE_URL}/?fixture=content-review", wait_until="networkidle")
    selector = page.get_by_label("Current portfolio stage")
    assert selector.is_visible()
    assert selector.locator("option", has_text="Design").is_disabled()
    assert page.locator(".journey-rail").is_hidden()
    assert_no_horizontal_overflow(page)


def test_approved_artifact_exposes_a_separate_destination_start(browser_page: object) -> None:
    page = browser_page
    page.set_viewport_size({"width": 1366, "height": 768})
    page.goto(f"{BASE_URL}/?fixture=content-approved", wait_until="networkidle")
    assert page.get_by_role("button", name="Start Visual Design Director").is_visible()
    assert page.get_by_text("Approval is saved. Start the next stage when you are ready.").is_visible()
    assert page.get_by_role("button", name="Approve content plan").count() == 0


def test_preparation_is_metadata_only_and_inspector_is_closed(browser_page: object) -> None:
    page = browser_page
    page.set_viewport_size({"width": 1366, "height": 768})
    page.goto(f"{BASE_URL}/?fixture=preparation-ready", wait_until="networkidle")
    assert page.get_by_role("heading", name="References prepared for generation").is_visible()
    assert page.locator(".resource-evidence-card").count() == 1
    assert page.locator(".preparation-stage-view img").count() == 0
    assert page.locator("#output-inspector-drawer").count() == 0


def test_generation_working_uses_human_milestones_and_attention_preserves_preview(browser_page: object) -> None:
    page = browser_page
    page.set_viewport_size({"width": 1366, "height": 768})
    page.goto(f"{BASE_URL}/?fixture=generation-working", wait_until="networkidle")
    for label in ("Planning", "Acquiring resources", "Building pages", "Testing viewports", "Promoting preview"):
        assert page.locator(".progress-milestone-label", has_text=label).is_visible()
    page.goto(f"{BASE_URL}/?fixture=generation-attention", wait_until="networkidle")
    assert page.get_by_text("Your verified preview remains preserved.").is_visible()
    assert page.get_by_role("button", name="Retry generation").is_visible()
    assert_no_horizontal_overflow(page)


def test_developer_inspector_is_opt_in_and_drawer_is_accessible(browser_page: object) -> None:
    page = browser_page
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{BASE_URL}/?fixture=content-review", wait_until="networkidle")
    assert page.get_by_role("button", name="Inspector").count() == 0
    page.goto(f"{BASE_URL}/?fixture=content-review&inspector=1", wait_until="networkidle")
    page.get_by_role("button", name="Inspector").click()
    drawer = page.get_by_role("dialog", name="Output Inspector")
    assert drawer.is_visible()
    page.keyboard.press("Escape")
    assert drawer.is_hidden()
