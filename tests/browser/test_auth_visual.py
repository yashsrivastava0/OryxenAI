"""Inspect sign-in layout, card containment and animation controls in Chromium."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader
from tests.browser.helpers import BASE_URL, REPO_ROOT, assert_no_horizontal_overflow, expect, shot

from oryxenai.agents.code_generator.serving import preview_headers
from oryxenai.auth.showcase import SHOWCASE_ROOT, showcase_manifest

AUTH_STATIC = REPO_ROOT / "src" / "oryxenai" / "auth" / "static"


def _sign_in_html(live_auth: bool = False, page_name: str = "sign-in") -> str:
    templates = REPO_ROOT / "src" / "oryxenai" / "auth" / "templates"
    env = Environment(loader=FileSystemLoader(templates), autoescape=True)
    return env.get_template("auth_shell.html").render(
        app_name="OryxenAI",
        page=page_name,
        showcase=showcase_manifest(),
        auth_config={"supabaseUrl": "https://auth.test", "publishableKey": "test-key"}
        if live_auth
        else {},
    )


def _install_sign_in(page: object, live_auth: bool = False) -> None:
    page.unroute_all()
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

    def demo_asset(route: object) -> None:
        relative = urlparse(route.request.url).path.split("/showcase-samples/")[1]
        path = SHOWCASE_ROOT / relative
        route.fulfill(
            status=200,
            body=path.read_bytes(),
            content_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            headers=preview_headers(html=path.suffix == ".html", etag="test", scripts=True),
        )

    page.route(f"{BASE_URL}/showcase-samples/**", demo_asset)
    page.route(  # type: ignore[attr-defined]
        f"{BASE_URL}/sign-in",
        lambda route: route.fulfill(status=200, body=html, content_type="text/html"),
    )


def test_samples_are_visible_and_responsive(browser_page: object) -> None:
    page = browser_page
    _install_sign_in(page, live_auth=True)
    page.emulate_media(reduced_motion="reduce")
    page.goto(f"{BASE_URL}/sign-in", wait_until="networkidle")
    expect(page.get_by_text("See what OryxenAI creates.")).to_be_visible()
    assert page.locator("iframe").count() == 0
    for width, height in [
        (1280, 720),
        (1366, 768),
        (1440, 900),
        (1920, 1080),
        (320, 740),
        (390, 844),
        (768, 1024),
        (1024, 768),
    ]:
        page.set_viewport_size({"width": width, "height": height})
        assert_no_horizontal_overflow(page)
        if width >= 1100:
            assert page.evaluate("document.documentElement.scrollHeight <= innerHeight + 1")
        for name in ("Nightshift", "Velvet", "Daybreak"):
            tab = page.get_by_role("tab", name=name, exact=True)
            tab.click()
            expect(tab).to_have_attribute("aria-selected", "true")
            expect(page.locator("#sample-browser-title")).to_contain_text(name)
        shot(page, f"sign-in-{width}")
    page.get_by_role("tab", name="Daybreak", exact=True).focus()
    page.keyboard.press("ArrowRight")
    expect(page.get_by_role("tab", name="Nightshift", exact=True)).to_be_focused()
    page.get_by_role("link", name="Explore this sample").click()
    expect(page.locator("#sample-dialog")).to_be_visible()
    expect(page.locator("iframe.is-ready")).to_be_visible()
    assert "sample=nightshift" in page.url
    page.keyboard.press("Escape")
    expect(page.locator("#sample-dialog")).to_be_hidden()
    assert page.locator("iframe").count() == 0
    expect(page.locator("#sample-open")).to_be_focused()
    page.go_forward()
    expect(page.locator("#sample-dialog")).to_be_visible()
    page.locator("#sample-close").click()


def test_google_sign_in_loading_and_inline_failure(browser_page: object) -> None:
    page = browser_page
    _install_sign_in(page, live_auth=True)
    page.emulate_media(reduced_motion="reduce")  # type: ignore[attr-defined]
    page.set_viewport_size({"width": 390, "height": 844})  # type: ignore[attr-defined]
    page.goto(f"{BASE_URL}/sign-in", wait_until="networkidle")  # type: ignore[attr-defined]
    button = page.locator("#google-sign-in")  # type: ignore[attr-defined]
    button.focus()
    page.keyboard.press("Enter")
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


def test_sample_timeout_retry_direct_link_and_stale_message(browser_page: object) -> None:
    page = browser_page
    _install_sign_in(page, live_auth=True)
    page.route(
        f"{BASE_URL}/sign-in?*",
        lambda route: route.fulfill(status=200, body=_sign_in_html(True), content_type="text/html"),
    )
    page.goto(f"{BASE_URL}/sign-in?sample=velvet&review=1#sign-in-panel")
    expect(page.locator("#sample-dialog")).to_be_visible()
    expect(page.locator("iframe.is-ready")).to_be_visible()
    page.locator("#sample-close").click()
    assert "sample=" not in page.url and "review=1" in page.url
    page.route(
        f"{BASE_URL}/showcase-samples/**/ready.mjs*",
        lambda route: route.fulfill(status=200, body="", content_type="text/javascript"),
    )
    page.evaluate(
        "document.querySelector('.sample-showcase').dataset.loadTimeout = '100'; document.querySelector('.sample-showcase').dataset.loadingDelay = '10'"
    )
    page.locator("#sample-open").click()
    page.evaluate("window.postMessage({type:'oryxenai-demo-ready',attempt:'stale'}, '*')")
    expect(page.locator("#sample-retry")).to_be_visible()
    assert page.locator("iframe").count() == 0
    page.unroute(f"{BASE_URL}/showcase-samples/**/ready.mjs*")
    page.evaluate("document.querySelector('.sample-showcase').dataset.loadTimeout = '10000'")
    page.locator("#sample-retry").click()
    expect(page.locator("iframe.is-ready")).to_be_visible()
    page.locator("#sample-close").click()


def test_escape_from_inside_each_demo_and_repeated_opening(browser_page: object) -> None:
    page = browser_page
    _install_sign_in(page, live_auth=True)
    page.goto(f"{BASE_URL}/sign-in")
    for name in ("Daybreak", "Nightshift", "Velvet"):
        page.get_by_role("tab", name=name, exact=True).click()
        page.locator("#sample-open").click()
        expect(page.locator("iframe.is-ready")).to_be_visible()
        page.frame_locator("iframe").locator(".demo-nav").get_by_role(
            "link", name="About", exact=True
        ).click()
        page.keyboard.press("Escape")
        expect(page.locator("#sample-dialog")).to_be_hidden()
        page.wait_for_function("!location.search.includes('sample=')")
        assert page.locator("iframe").count() == 0


def test_onboarding_preserves_handle_and_prevents_duplicate_submission(
    browser_page: object,
) -> None:
    page = browser_page
    _install_sign_in(page, live_auth=True)
    page.route(
        f"{BASE_URL}/onboarding",
        lambda route: route.fulfill(
            status=200, body=_sign_in_html(True, "onboarding"), content_type="text/html"
        ),
    )
    page.route(
        f"{BASE_URL}/auth-static/auth-client.js*",
        lambda route: route.fulfill(
            status=200,
            content_type="text/javascript",
            body="window.OryxenAISupabaseClient={createClient:()=>({auth:{getSession:async()=>({data:{session:{access_token:'fixture'}}})}})}",
        ),
    )
    page.route(
        f"{BASE_URL}/api/v1/me",
        lambda route: route.fulfill(status=200, json={"onboarding_required": True, "role": "user"}),
    )
    pending = []
    page.route(f"{BASE_URL}/api/v1/me/username", lambda route: pending.append(route))
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{BASE_URL}/onboarding")
    field = page.locator("#username")
    field.fill("bad-")
    expect(page.locator("#username-error")).to_be_visible()
    field.fill("maya-123")
    expect(page.locator("#username-error")).to_be_hidden()
    submit = page.locator("#username-form button")
    submit.click()
    expect(submit).to_be_disabled()
    expect(submit).to_have_text("Saving your handle…")
    page.evaluate("document.getElementById('username-form').requestSubmit()")
    page.wait_for_timeout(100)
    assert len(pending) == 1
    pending[0].fulfill(
        status=409,
        json={"error": {"code": "USERNAME_TAKEN", "message": "This handle is unavailable."}},
    )
    expect(submit).to_be_enabled()
    expect(field).to_have_value("maya-123")
    expect(page.locator("#username-error")).to_have_text("That username is already taken.")
    assert_no_horizontal_overflow(page)


def test_missing_poster_keeps_sign_in_and_other_samples_available(browser_page: object) -> None:
    page = browser_page
    _install_sign_in(page, live_auth=True)
    page.route(
        f"{BASE_URL}/showcase-samples/daybreak/poster.webp",
        lambda route: route.fulfill(status=404, body="missing"),
    )
    page.set_viewport_size({"width": 1280, "height": 720})
    page.goto(f"{BASE_URL}/sign-in")
    expect(page.locator("#sample-poster-fallback")).to_be_visible()
    expect(page.locator("#google-sign-in")).to_be_enabled()
    assert page.evaluate("document.documentElement.scrollHeight <= innerHeight + 1")
    page.get_by_role("tab", name="Nightshift", exact=True).click()
    expect(page.locator("#sample-poster")).to_be_visible()
    expect(page.locator("#sample-poster-fallback")).to_be_hidden()


def test_callback_notice_survives_redirect_once(browser_page: object) -> None:
    page = browser_page
    _install_sign_in(page, live_auth=True)
    page.evaluate("sessionStorage.setItem('oryxenai.auth_notice', 'callback_error')")
    page.goto(f"{BASE_URL}/sign-in")
    expect(page.locator("#sign-in-error")).to_have_text(
        "Google sign-in was canceled or could not be completed."
    )
    page.reload()
    expect(page.locator("#google-sign-in")).to_be_enabled()
    expect(page.locator("#sign-in-error")).to_be_hidden()
