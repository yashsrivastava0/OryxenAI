from __future__ import annotations

import shutil
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
    assert selector.locator("option", has_text="Design").is_disabled()
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


def test_approved_artifact_exposes_a_separate_destination_start(browser_page: object) -> None:
    page = browser_page
    page.set_viewport_size({"width": 1366, "height": 768})
    page.goto(f"{BASE_URL}/?fixture=content-approved", wait_until="networkidle")
    assert page.get_by_role("button", name="Start Visual Design Director").is_visible()
    assert page.get_by_text(
        "Approval is saved. Start the next stage when you are ready."
    ).is_visible()
    assert page.get_by_role("button", name="Approve content plan").count() == 0


def test_preparation_is_metadata_only_and_inspector_is_closed(browser_page: object) -> None:
    page = browser_page
    page.set_viewport_size({"width": 1366, "height": 768})
    page.goto(f"{BASE_URL}/?fixture=preparation-ready", wait_until="networkidle")
    assert page.get_by_role("heading", name="Build handoff prepared").is_visible()
    assert page.locator(".evidence-card").count() == 1
    assert page.locator(".preparation-stage-view img").count() == 0
    assert page.locator("#output-inspector-drawer").count() == 0


def test_generation_working_uses_human_milestones_and_attention_preserves_preview(
    browser_page: object,
) -> None:
    page = browser_page
    page.set_viewport_size({"width": 1366, "height": 768})
    page.goto(f"{BASE_URL}/?fixture=generation-working", wait_until="networkidle")
    for label in ("Plan", "Acquire", "Build", "Verify", "Preview"):
        assert page.locator(".step-label", has_text=label).is_visible()
    assert page.get_by_text("62%", exact=True).count() == 0
    assert page.get_by_text("Publish", exact=False).count() == 0
    assert page.get_by_text("Deploy", exact=False).count() == 0
    page.goto(f"{BASE_URL}/?fixture=generation-attention", wait_until="networkidle")
    assert page.get_by_text("Your last verified preview is still available.").is_visible()
    assert page.get_by_role("button", name="Retry generation").is_visible()
    page.goto(f"{BASE_URL}/?fixture=generation-planning-failed", wait_until="networkidle")
    assert page.get_by_role("heading", name="Generation needs attention").is_visible()
    assert page.get_by_text("The background job handler failed.").is_visible()
    assert page.get_by_role("button", name="Refresh state").count() == 0
    assert page.get_by_role("button", name="Retry generation").is_visible()
    assert_no_horizontal_overflow(page)


@pytest.mark.parametrize("width,height", VIEWPORTS)
def test_generation_preview_is_truthful_and_contained(
    browser_page: object, width: int, height: int
) -> None:
    page = browser_page
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{BASE_URL}/?fixture=generation-ready", wait_until="networkidle")
    theater = page.locator(".codegen-preview-theater")
    frame = page.locator(".browser-content-viewport")
    assert theater.is_visible()
    assert frame.is_visible()
    assert page.get_by_role("link", name="Open verified preview").is_visible()
    assert page.get_by_role("button", name="Regenerate portfolio").is_visible()
    assert page.get_by_text("Publish", exact=False).count() == 0
    assert page.get_by_text("Deploy", exact=False).count() == 0
    theater_box = theater.bounding_box()
    frame_box = frame.bounding_box()
    assert theater_box and frame_box
    assert frame_box["x"] >= theater_box["x"]
    assert frame_box["x"] + frame_box["width"] <= theater_box["x"] + theater_box["width"] + 1
    if width == 768:
        left_panel = page.locator(".codegen-left-panel").bounding_box()
        assert left_panel is not None
        assert theater_box["y"] < left_panel["y"]
    assert_no_horizontal_overflow(page)


def test_generation_transition_respects_reduced_motion(browser_page: object) -> None:
    page = browser_page
    page.set_viewport_size({"width": 1366, "height": 768})
    page.goto(f"{BASE_URL}/?fixture=generation-ready", wait_until="networkidle")
    assert page.locator(".stage-transition-layer").count() == 1
    page.emulate_media(reduced_motion="reduce")
    duration = page.locator(".stage-transition-layer").evaluate(
        "element => getComputedStyle(element).animationDuration"
    )
    assert duration in {"0.01s", "1e-05s"}


def test_generation_candidate_is_never_presented_as_verified(browser_page: object) -> None:
    page = browser_page
    page.set_viewport_size({"width": 1366, "height": 768})
    page.goto(f"{BASE_URL}/?fixture=generation-candidate", wait_until="networkidle")
    assert page.get_by_text("Candidate preview (unverified)").is_visible()
    assert page.get_by_role("link", name="Open candidate preview").is_visible()
    assert page.get_by_text("Open verified preview", exact=True).count() == 0


def test_generation_direct_fixture_requires_an_explicit_standalone_run(
    browser_page: object,
) -> None:
    page = browser_page
    page.set_viewport_size({"width": 1366, "height": 768})
    page.goto(f"{BASE_URL}/?fixture=generation-direct", wait_until="networkidle")
    assert page.get_by_role("heading", name="Run ID required").is_visible()
    assert page.get_by_text("fixture=generation-direct&run_id=<RUN_ID>", exact=False).is_visible()


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
