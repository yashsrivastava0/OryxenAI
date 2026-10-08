from __future__ import annotations

import re

import pytest
from tests.browser.helpers import (
    BASE_URL,
    assert_no_horizontal_overflow,
    expect,
    install_sample_page,
)
from tests.browser.helpers import (
    shot as _shot,
)

VIEWPORTS = [(1536, 695), (1366, 768), (768, 1024), (390, 844)]


@pytest.mark.parametrize("width,height", VIEWPORTS)
def test_workspace_header_has_room_for_brand_journey_and_actions(
    browser_page: object, width: int, height: int
) -> None:
    page = browser_page
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{BASE_URL}/?fixture=discovery-question-palette", wait_until="networkidle")
    visible_copy = page.inner_text("body")
    assert "EXPLORER" in visible_copy
    assert not re.search(r"\bdiscover(?:y)?\b", visible_copy, re.IGNORECASE)
    assert (
        page.locator('#journey-stage-select option[value="discover"]').inner_text() == "1. Explore"
    )
    brand = page.locator(".app-brand").bounding_box()
    journey = page.locator(".journey-nav").bounding_box()
    actions = page.locator(".app-topbar-actions").bounding_box()
    assert brand and journey and actions
    assert brand["x"] + brand["width"] <= actions["x"] + 1
    if width <= 600:
        assert brand["y"] + brand["height"] <= journey["y"] + 1
    else:
        assert brand["x"] + brand["width"] <= journey["x"] + 1
        assert journey["x"] + journey["width"] <= actions["x"] + 1
    assert_no_horizontal_overflow(page)


@pytest.mark.parametrize("width,height", VIEWPORTS)
def test_visual_palette_cards_fit_and_remain_keyboard_selectable(
    browser_page: object, width: int, height: int
) -> None:
    page = browser_page
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{BASE_URL}/?fixture=discovery-question-palette", wait_until="networkidle")
    cards = page.locator(".palette-choice")
    assert cards.count() == 5
    assert [card.locator("small").inner_text() for card in cards.all()] == [
        "Interactive editorial · layered and vivid",
        "Cinematic depth · warm and dramatic",
        "Editorial warmth · layered and considered",
        "Minimal clarity · bright and structured",
        "Bold modernity · high contrast and energetic",
    ]
    assert page.get_by_role("textbox", name="Optional note for your reference").is_visible()
    if width >= 1180:
        note = page.get_by_role("textbox", name="Optional note for your reference").bounding_box()
        gallery = page.locator(".theme-picker__gallery").bounding_box()
        dock = page.locator(".action-dock").bounding_box()
        assert note and gallery and dock
        assert note["y"] + note["height"] <= dock["y"] + 1
        assert gallery["y"] + gallery["height"] <= dock["y"] + 1
    assert_no_horizontal_overflow(page)

    first = cards.nth(0).locator('input[type="radio"]')
    second = cards.nth(1).locator('input[type="radio"]')
    first.focus()
    page.keyboard.press("Space")
    assert first.is_checked()
    page.keyboard.press("ArrowRight")
    assert second.is_checked()
    assert page.get_by_role("button", name="Continue to brief").is_enabled()
    _shot(page, f"discovery-palette-{width}")


def test_theme_catalog_search_filters_and_keeps_selection(browser_page: object) -> None:
    page = browser_page
    page.goto(f"{BASE_URL}/?fixture=discovery-question-palette", wait_until="networkidle")
    page.evaluate("sessionStorage.clear()")
    page.reload(wait_until="networkidle")
    page.get_by_text("Claret & amber", exact=True).click()
    page.get_by_role("button", name="Classic", exact=True).click()
    assert page.locator(".palette-choice").count() == 3
    assert "Claret & amber" in page.locator(".theme-picker__selection").inner_text()
    assert page.get_by_role("button", name="Continue to brief").is_enabled()
    page.get_by_role("button", name="Show selection").click()
    assert page.get_by_role("radio", name="Claret & amber", exact=True).is_checked()
    search = page.get_by_role("searchbox", name="Search portfolio looks")
    search.fill("Cinematic")
    assert page.locator(".palette-choice").count() == 1
    search.fill("no such look")
    assert page.get_by_text("No matching looks", exact=True).is_visible()
    page.get_by_role("button", name="Clear filters").click()
    assert page.locator(".palette-choice").count() == 5


def test_large_theme_catalog_is_not_truncated_or_allowed_to_cover_actions(
    browser_page: object,
) -> None:
    page = browser_page
    page.set_viewport_size({"width": 1366, "height": 768})
    page.goto(f"{BASE_URL}/?fixture=discovery-question-palette-many", wait_until="networkidle")
    assert page.locator(".palette-choice").count() == 24
    gallery = page.locator(".theme-picker__gallery")
    assert gallery.evaluate("node => node.scrollHeight > node.clientHeight")
    page.get_by_role("searchbox", name="Search portfolio looks").fill("Portfolio look 24")
    page.get_by_text("Portfolio look 24", exact=True).click()
    assert page.get_by_role("button", name="Continue to brief").is_enabled()
    assert_no_horizontal_overflow(page)


def test_stale_palette_drafts_do_not_enable_submission(browser_page: object) -> None:
    page = browser_page
    page.goto(f"{BASE_URL}/?fixture=discovery-question-palette", wait_until="networkidle")
    page.evaluate("sessionStorage.setItem('oryxenai.draft.visual_palette.single', 'retired_theme')")
    page.reload(wait_until="networkidle")
    assert page.get_by_role("button", name="Continue to brief").is_disabled()
    page.evaluate("sessionStorage.clear()")


def test_context_question_accepts_custom_only_and_mixed_answers(browser_page: object) -> None:
    page = browser_page
    for selected, expected in (
        (False, "My own project story"),
        (True, "AlphaMesh-Core. My own project story"),
    ):
        page.goto(f"{BASE_URL}/?fixture=discovery-question-mcq", wait_until="networkidle")
        page.evaluate("sessionStorage.clear()")
        page.reload(wait_until="networkidle")
        if selected:
            page.get_by_text("AlphaMesh-Core", exact=True).click()
        page.get_by_role("textbox", name="Add context or write your own answer").fill(
            "My own project story"
        )
        page.get_by_role("button", name="Next question").click()
        answer = page.evaluate("window.__capturedDiscoveryAnswer")
        assert answer["mode"] == "answered"
        assert answer["value"] == expected


@pytest.mark.parametrize("width,height", VIEWPORTS)
def test_required_viewports_keep_stage_actions_visible(
    browser_page: object, width: int, height: int
) -> None:
    page = browser_page
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{BASE_URL}/?fixture=content-review", wait_until="networkidle")
    assert page.get_by_role("heading", name="Your portfolio page content").is_visible()
    assert page.get_by_role("button", name="Approve content plan").is_visible()
    assert_no_horizontal_overflow(page)
    _shot(page, f"content-review-{width}")


def test_mobile_uses_compact_selector_and_locked_options(browser_page: object) -> None:
    page = browser_page
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{BASE_URL}/?fixture=content-review", wait_until="networkidle")
    selector = page.get_by_label("Current portfolio stage")
    assert selector.is_visible()
    options = selector.locator("option")
    assert options.count() == 3
    assert options.nth(0).inner_text().startswith("1. Explore")
    assert options.nth(1).inner_text().startswith("2. Content")
    assert options.nth(2).inner_text().startswith("3. Studio")
    assert options.nth(0).is_enabled()
    assert options.nth(1).is_enabled()
    assert not options.nth(2).is_enabled()  # the Studio unlocks only after the plan is approved
    assert page.locator(".journey-rail").is_hidden()
    assert_no_horizontal_overflow(page)


def test_discovery_intake_keeps_prompts_above_reserved_actions(browser_page: object) -> None:
    page = browser_page
    page.set_viewport_size({"width": 1366, "height": 768})
    page.goto(f"{BASE_URL}/?fixture=discovery-input", wait_until="networkidle")
    assert page.get_by_text("0 words").is_visible()
    assert page.get_by_text(
        "Start with what you have. You can clarify gaps and review the evidence before approving the brief."
    ).is_visible()
    assert page.get_by_text("A deeper conversation for a more intentional future.").count() == 0
    prompt_box = page.locator(".starting-points-grid").bounding_box()
    dock_box = page.locator(".intake-dock").bounding_box()
    assert prompt_box and dock_box
    assert dock_box["y"] + dock_box["height"] <= 768
    page.locator(".starting-points-grid").scroll_into_view_if_needed()
    prompt_box = page.locator(".starting-points-grid").bounding_box()
    assert prompt_box and prompt_box["y"] + prompt_box["height"] <= dock_box["y"] + 1
    assert_no_horizontal_overflow(page)
    _shot(page, "discovery-intake-1366")


def test_discovery_can_start_with_an_attached_text_file_alone(browser_page: object) -> None:
    page = browser_page
    page.goto(f"{BASE_URL}/?fixture=discovery-input", wait_until="networkidle")
    start = page.get_by_role("button", name="Start Explorer")
    assert start.is_disabled()
    page.locator('input[type="file"]').set_input_files(
        {"name": "resume.md", "mimeType": "text/markdown", "buffer": b"# My resume"}
    )
    expect(page.get_by_text("resume.md", exact=False)).to_be_visible()
    assert (
        page.get_by_label(
            "Explorer will read this text. Correct anything the PDF reader missed."
        ).input_value()
        == "# My resume"
    )
    expect(start).to_be_enabled()


def test_discovery_reveals_next_question_while_answer_saves(browser_page: object) -> None:
    page = browser_page
    page.set_viewport_size({"width": 1366, "height": 768})
    page.evaluate("sessionStorage.clear()")
    page.goto(f"{BASE_URL}/?fixture=discovery-question-queued", wait_until="networkidle")
    page.get_by_text("AlphaMesh-Core", exact=True).click()
    page.get_by_role("button", name="Next question").click()
    expect(page.get_by_text("What primary audience should this portfolio address?")).to_be_visible(
        timeout=500
    )


def test_failed_answer_save_restores_question_and_selection(browser_page: object) -> None:
    page = browser_page
    page.evaluate("sessionStorage.clear()")
    page.goto(f"{BASE_URL}/?fixture=discovery-question-save-fails", wait_until="networkidle")
    page.get_by_text("AlphaMesh-Core", exact=True).click()
    page.get_by_role("button", name="Next question").click()
    expect(page.get_by_text("What primary audience should this portfolio address?")).to_be_visible(
        timeout=500
    )
    expect(page.get_by_text("Which project stories should lead your portfolio?")).to_be_visible()
    expect(page.get_by_text("Save failed").first).to_be_visible()
    assert page.locator('input[type="checkbox"]').first.is_checked()


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


# ── Studio: live preview + change chat ───────────────────────────────────────


def _open_studio(page: object, fixture: str, width: int = 1366, height: int = 768) -> list[str]:
    problems: list[str] = []
    page.on(  # type: ignore[attr-defined]
        "console",
        lambda message: (
            problems.append(f"console:{message.text}") if message.type == "error" else None
        ),
    )
    page.on("requestfailed", lambda request: problems.append(f"failed:{request.url}"))  # type: ignore[attr-defined]
    page.set_viewport_size({"width": width, "height": height})  # type: ignore[attr-defined]
    page.goto(f"{BASE_URL}/?fixture={fixture}", wait_until="networkidle")  # type: ignore[attr-defined]
    return problems


def test_studio_workspace_puts_chat_left_and_the_sandboxed_live_page_right(
    browser_page: object,
) -> None:
    page = browser_page
    install_sample_page(page)
    problems = _open_studio(page, "studio-workspace")
    chat = page.locator(".studio-chat")
    preview = page.locator(".studio-preview")
    expect(chat).to_be_visible()
    expect(preview).to_be_visible()
    chat_box, preview_box = chat.bounding_box(), preview.bounding_box()
    assert chat_box and preview_box and chat_box["x"] + chat_box["width"] <= preview_box["x"] + 1

    frame_element = page.locator("iframe.studio-frame.is-visible")
    expect(frame_element).to_have_count(1)
    assert frame_element.get_attribute("sandbox") == "allow-popups allow-popups-to-escape-sandbox"
    assert frame_element.get_attribute("referrerpolicy") == "no-referrer"
    frame = page.frame_locator("iframe.studio-frame.is-visible")
    expect(frame.locator("h1")).to_be_visible()
    # The page really rendered under the production CSP: the theme stylesheet applied.
    assert frame.locator("body").evaluate("el => getComputedStyle(el).fontFamily") != ""
    expect(frame.locator("nav.site-nav")).to_be_visible()
    _shot(page, "studio-workspace-1366")
    assert [item for item in problems if "favicon" not in item] == []
    assert_no_horizontal_overflow(page)


def test_studio_device_toggle_resizes_the_frame(browser_page: object) -> None:
    page = browser_page
    install_sample_page(page)
    _open_studio(page, "studio-workspace")
    frame = page.locator("iframe.studio-frame.is-visible")
    expect(frame).to_have_count(1)
    for label, width in (("Mobile", 390), ("Tablet", 768), ("Desktop", 1280)):
        page.get_by_role("button", name=label, exact=True).click()
        expect(frame).to_have_attribute("style", __import__("re").compile(f"width: {width}px"))
    _shot(page, "studio-desktop-fit")
    page.get_by_role("button", name="100%", exact=True).click()
    assert_no_horizontal_overflow(page)


def test_studio_change_flow_shows_progress_then_the_new_version(browser_page: object) -> None:
    page = browser_page
    install_sample_page(page)
    _open_studio(page, "studio-interactive")
    composer = page.get_by_label("Describe the change you want")
    composer.fill("Make my introduction a bit shorter")
    page.get_by_role("button", name="Send", exact=True).click()
    expect(page.get_by_text("Understanding your request…")).to_be_visible(timeout=1500)
    expect(composer).to_be_disabled()
    expect(page.get_by_text("Updating…")).to_be_visible()
    _shot(page, "studio-building-change")
    expect(page.get_by_text("Version 2", exact=True)).to_be_visible(timeout=5000)
    expect(page.get_by_text("Done. I updated that part of your page.")).to_be_visible()
    expect(composer).to_be_enabled()
    expect(page.locator("iframe.studio-frame")).to_have_count(1)  # the old frame was released
    expect(page.get_by_text("Versions (2)")).to_be_visible()
    _shot(page, "studio-after-change")


def test_studio_reports_a_failed_first_build_exactly(browser_page: object) -> None:
    page = browser_page
    _open_studio(page, "studio-attention", 1366, 900)
    expect(
        page.get_by_role("heading", name="Your portfolio could not be built yet")
    ).to_be_visible()
    for text in (
        "What happened",
        "hero.intro",
        "The model changed, dropped, added or misplaced approved wording",
        "Senior backend engineer at Northstar Systems",
        "cg-4f1a9c0b22",
    ):
        expect(page.get_by_text(text, exact=False).first).to_be_visible()
    expect(page.get_by_role("button", name="Try building again")).to_be_visible()
    expect(page.get_by_role("button", name="Copy diagnostics")).to_be_visible()
    _shot(page, "studio-attention-1366")
    assert_no_horizontal_overflow(page)


def test_studio_failed_edit_keeps_the_page_and_offers_details(browser_page: object) -> None:
    page = browser_page
    install_sample_page(page)
    _open_studio(page, "studio-failed-edit")
    expect(page.locator("iframe.studio-frame.is-visible")).to_have_count(1)
    expect(page.get_by_text("last verified page is unchanged").first).to_be_visible()
    page.get_by_role("button", name="See exactly what went wrong").click()
    expect(page.get_by_text("That change did not go through")).to_be_visible()
    _shot(page, "studio-failed-edit")


@pytest.mark.parametrize("fixture", ["studio-available", "studio-working", "studio-attention"])
@pytest.mark.parametrize("width,height", [(768, 1024), (390, 844)])
def test_studio_states_fit_narrow_screens(
    browser_page: object, fixture: str, width: int, height: int
) -> None:
    page = browser_page
    _open_studio(page, fixture, width, height)
    assert_no_horizontal_overflow(page)
    _shot(page, f"{fixture}-{width}")


def test_studio_mobile_shows_one_pane_at_a_time(browser_page: object) -> None:
    page = browser_page
    install_sample_page(page)
    _open_studio(page, "studio-workspace", 390, 844)
    tabs = page.get_by_role("tablist", name="Studio panels")
    expect(tabs).to_be_visible()
    expect(page.locator(".studio-pane--preview")).to_be_visible()
    expect(page.locator(".studio-pane--chat")).to_be_hidden()
    _shot(page, "studio-mobile-preview")
    page.get_by_role("tab", name="Chat").click()
    expect(page.locator(".studio-pane--chat")).to_be_visible()
    expect(page.locator(".studio-pane--preview")).to_be_hidden()
    _shot(page, "studio-mobile-chat")
    assert_no_horizontal_overflow(page)
