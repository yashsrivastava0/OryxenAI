"""Inspect sign-in layout, card containment and animation controls in Chromium."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader
from tests.browser.helpers import BASE_URL, REPO_ROOT, assert_no_horizontal_overflow, expect, shot

AUTH_STATIC = REPO_ROOT / "src" / "oryxenai" / "auth" / "static"


def _sign_in_html(live_auth: bool = False) -> str:
    templates = REPO_ROOT / "src" / "oryxenai" / "auth" / "templates"
    env = Environment(loader=FileSystemLoader(templates), autoescape=True)
    return env.get_template("auth_shell.html").render(
        app_name="OryxenAI",
        page="sign-in",
        auth_config={"supabaseUrl": "https://auth.test", "publishableKey": "test-key"}
        if live_auth
        else {},
    )


def _install_sign_in(page: object, live_auth: bool = False) -> None:
    html = _sign_in_html(live_auth)

    def asset(route: object) -> None:
        name = Path(urlparse(route.request.url).path).name  # type: ignore[attr-defined]
        path = AUTH_STATIC / name
        if not path.is_file():
            route.fulfill(status=404, body="not found")  # type: ignore[attr-defined]
            return
        # Identity bootstrapping is outside this visual check; the showcase
        # controller remains live so its stage/card pairing is exercised.
        if name == "auth-client.js" and live_auth:
            route.fulfill(  # type: ignore[attr-defined]
                status=200,
                content_type="text/javascript",
                body="""window.OryxenAISupabaseClient = { createClient: () => ({ auth: {
                  getSession: async () => ({ data: { session: null } }),
                  signInWithOAuth: options => new Promise(resolve => {
                    window.oauthOptions = options;
                    window.resolveOauth = resolve;
                  })
                } }) };""",
            )
            return
        if name == "auth-admin.mjs" or (
            not live_auth and name in {"auth-page.mjs", "auth-client.js"}
        ):
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


def _assert_card_fits(page: object) -> None:
    details = page.locator(".showcase-card.card-active").evaluate(  # type: ignore[attr-defined]
        """(card) => {
          const bounds = card.getBoundingClientRect();
          const walker = document.createTreeWalker(card, NodeFilter.SHOW_TEXT);
          const outside = [];
          while (walker.nextNode()) {
            const text = walker.currentNode;
            if (!text.textContent.trim()) continue;
            const range = document.createRange();
            range.selectNodeContents(text);
            for (const rect of range.getClientRects()) {
              if (rect.width && (rect.left < bounds.left - 1 || rect.right > bounds.right + 1 || rect.bottom > bounds.bottom + 1)) {
                outside.push(text.textContent.trim());
              }
            }
          }
          const children = [...card.children].filter(child => child.getBoundingClientRect().height > 0);
          const overlap = children.slice(1).some((child, i) => children[i].getBoundingClientRect().bottom > child.getBoundingClientRect().top + 1);
          return { outside, overlap, height: card.clientHeight, content: card.scrollHeight };
        }"""
    )
    assert not details["outside"], details
    assert not details["overlap"], details
    assert details["content"] <= details["height"] + 1, details


def test_sign_in_three_stage_showcase_is_legible_and_responsive(browser_page: object) -> None:
    page = browser_page
    _install_sign_in(page)
    page.emulate_media(reduced_motion="reduce")  # type: ignore[attr-defined]
    page.goto(f"{BASE_URL}/sign-in", wait_until="networkidle")  # type: ignore[attr-defined]
    expect(page.get_by_text("THREE STEPS, EACH IN YOUR HANDS")).to_be_visible()
    assert page.locator(".stage-rail-node").count() == 3  # type: ignore[attr-defined]
    assert page.locator(".showcase-card").count() == 4  # type: ignore[attr-defined]
    page.get_by_role("tab", name="Studio preview card").click()
    expect(page.get_by_text("See the page. Make it yours.")).to_be_visible()
    assert "active" in (
        page.locator('.stage-rail-node[data-stage="studio"]').get_attribute("class") or ""
    )
    for width, height in [
        (320, 740),
        (390, 844),
        (768, 1024),
        (1024, 768),
        (1366, 768),
        (1920, 1080),
    ]:
        page.set_viewport_size({"width": width, "height": height})  # type: ignore[attr-defined]
        for index in range(4):
            page.locator(".showcase-dot").nth(index).click()  # type: ignore[attr-defined]
            assert page.locator('.showcase-card[aria-hidden="false"]').count() == 1  # type: ignore[attr-defined]
            assert page.locator(".showcase-card[inert]").count() == 3  # type: ignore[attr-defined]
            _assert_card_fits(page)
            assert_no_horizontal_overflow(page)
        # Save a representative brief with focus and scroll restored to the top.
        page.get_by_role("tab", name="Portfolio brief card").click()
        page.evaluate("document.activeElement.blur(); window.scrollTo(0, 0)")
        shot(page, f"sign-in-{width}")

    page.set_viewport_size({"width": 1366, "height": 768})  # type: ignore[attr-defined]
    page.evaluate("document.documentElement.style.zoom = '2'")
    for index in range(4):
        page.locator(".showcase-dot").nth(index).click()  # type: ignore[attr-defined]
        _assert_card_fits(page)
        assert_no_horizontal_overflow(page)
    page.evaluate("document.documentElement.style.zoom = ''")


def test_showcase_pause_keyboard_and_reduced_motion(browser_page: object) -> None:
    page = browser_page
    _install_sign_in(page)
    page.emulate_media(reduced_motion="no-preference")  # type: ignore[attr-defined]
    page.set_viewport_size({"width": 1366, "height": 768})  # type: ignore[attr-defined]
    page.goto(f"{BASE_URL}/sign-in", wait_until="networkidle")  # type: ignore[attr-defined]
    page.get_by_role("button", name="Pause slideshow").click()
    expect(page.get_by_role("button", name="Play slideshow")).to_have_attribute(
        "aria-pressed", "true"
    )
    assert page.locator(".icon-pause").get_attribute("hidden") is not None  # type: ignore[attr-defined]
    assert page.locator(".icon-play").get_attribute("hidden") is None  # type: ignore[attr-defined]
    page.get_by_role("tab", name="Portfolio brief card").focus()
    page.keyboard.press("ArrowRight")  # type: ignore[attr-defined]
    expect(page.get_by_role("tab", name="Content structure card")).to_be_focused()
    expect(page.get_by_role("tab", name="Content structure card")).to_have_attribute(
        "aria-selected", "true"
    )
    page.keyboard.press("End")  # type: ignore[attr-defined]
    expect(page.get_by_role("tab", name="Studio preview card")).to_be_focused()
    page.keyboard.press("Home")  # type: ignore[attr-defined]
    expect(page.get_by_role("tab", name="Explorer card")).to_be_focused()
    page.get_by_role("button", name="Continue with Google").focus()
    page.mouse.move(0, 0)  # type: ignore[attr-defined]
    page.wait_for_timeout(6300)  # A paused showcase must stay on the selected card.
    expect(page.get_by_role("tab", name="Explorer card")).to_have_attribute("aria-selected", "true")
    page.get_by_role("button", name="Play slideshow").click()
    page.get_by_role("button", name="Continue with Google").focus()
    page.mouse.move(0, 0)  # type: ignore[attr-defined]
    expect(page.get_by_role("tab", name="Portfolio brief card")).to_have_attribute(
        "aria-selected", "true", timeout=7500
    )
    page.emulate_media(reduced_motion="reduce")  # type: ignore[attr-defined]
    expect(page.get_by_role("button", name="Pause slideshow")).to_be_hidden()
    page.wait_for_timeout(6300)
    expect(page.get_by_role("tab", name="Portfolio brief card")).to_have_attribute(
        "aria-selected", "true"
    )
    assert (
        page.locator(".card-active").evaluate("card => getComputedStyle(card).animationName")
        == "none"
    )  # type: ignore[attr-defined]


def test_google_sign_in_loading_and_inline_failure(browser_page: object) -> None:
    page = browser_page
    _install_sign_in(page, live_auth=True)
    page.emulate_media(reduced_motion="reduce")  # type: ignore[attr-defined]
    page.set_viewport_size({"width": 390, "height": 844})  # type: ignore[attr-defined]
    page.goto(f"{BASE_URL}/sign-in", wait_until="networkidle")  # type: ignore[attr-defined]
    button = page.locator("#google-sign-in")  # type: ignore[attr-defined]
    button.click()
    expect(button).to_be_disabled()
    expect(button).to_have_attribute("aria-busy", "true")
    expect(page.locator("#google-sign-in .cta-label")).to_have_text("Opening Google…")  # type: ignore[attr-defined]
    page.wait_for_function("window.oauthOptions?.provider === 'google'")  # type: ignore[attr-defined]
    assert page.evaluate("window.oauthOptions.options.queryParams.prompt") == "select_account"
    # The presentation must not re-enable a pending OAuth request on an arbitrary timer.
    page.wait_for_timeout(8500)
    expect(button).to_be_disabled()
    page.evaluate("window.resolveOauth({ error: { message: 'fixture failure' } })")
    expect(button).to_be_enabled()
    expect(button).to_have_attribute("aria-busy", "false")
    expect(page.locator("#google-sign-in .cta-label")).to_have_text("Continue with Google")  # type: ignore[attr-defined]
    expect(page.locator("#sign-in-error")).to_have_text(  # type: ignore[attr-defined]
        "Google sign-in could not start. Please try again shortly."
    )
    expect(page.locator("#sign-in-error")).to_be_visible()  # type: ignore[attr-defined]
    expect(page.locator("#global-error")).to_be_hidden()  # type: ignore[attr-defined]
    assert_no_horizontal_overflow(page)
    page.evaluate("document.activeElement.blur(); window.scrollTo(0, 0)")
    shot(page, "sign-in-error-mobile")
