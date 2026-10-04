"""The real AppShell (polling, handlers, URL state) against a stateful fake backend.

Drives the exact production bundle code path: content review -> one click to
approve and generate -> progress -> live preview -> chat change -> restore, and
the failure and returning-user paths. The fake mirrors the /code-generator API
contract, so these also pin the envelope the frontend depends on.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from tests.browser.helpers import (
    BASE_URL,
    assert_no_horizontal_overflow,
    expect,
    install_sample_page,
    shot,
)

SESSION = "session-e2e"


class FakeBackend:
    """Stateful stand-in for the sessions API (discovery approved, content, Studio)."""

    def __init__(
        self, fixtures: dict[str, Any], *, content: str = "review", studio: str = "not_started"
    ) -> None:
        self.fx = fixtures
        self.content_approved = content == "approved"
        self.status = studio  # not_started | ready
        self.versions: list[dict[str, Any]] = []
        self.chat: list[dict[str, Any]] = []
        self.in_flight: dict[str, Any] | None = None
        self.last_error: dict[str, Any] | None = None
        self.active = 0
        self.fail_next_build = False
        self.next_instruction = ""
        self.ticks = 0
        self.log: list[str] = []
        if studio == "ready":
            self._finish_build("initial", "")

    # ── state machine ────────────────────────────────────────────────────────

    def _finish_build(self, origin: str, instruction: str) -> None:
        number = len(self.versions) + 1
        self.versions.insert(
            0,
            {
                "id": f"v{number}",
                "seq": number,
                "version_number": number,
                "origin": origin,
                "status": "ready",
                "instruction": instruction,
                "restricted": False,
                "created_at": "2026-10-02T09:00:00+00:00",
                "completed_at": "2026-10-02T09:00:20+00:00",
                "summary": {"warning_count": 0, "browser": "not_run"},
            },
        )
        self.active = number
        self.status = "ready"
        self.in_flight = None
        self.last_error = None
        text = (
            "Your portfolio is ready (version 1)."
            if origin == "initial"
            else "Done. I updated that part of your page."
        )
        self.chat.append(
            {
                "id": f"a{number}",
                "seq": len(self.chat) + 1,
                "role": "assistant",
                "kind": "build" if origin == "initial" else "message",
                "body": text,
                "version_id": f"v{number}",
                "created_at": "2026-10-02T09:00:20+00:00",
            }
        )

    def _begin(self, origin: str, instruction: str) -> None:
        self.status = "build_running"
        self.ticks = 0
        self.next_instruction = instruction
        self.in_flight = {
            "run_id": "r",
            "job_id": "j",
            "version_id": f"v{len(self.versions) + 1}",
            "origin": origin,
            "instruction": instruction,
            "stage": "queued",
            "elapsed_seconds": 1.0,
            "started_at": "2026-10-02T09:00:00+00:00",
        }

    def _advance(self) -> None:
        if self.status != "build_running" or self.in_flight is None:
            return
        stages = (
            ["generating", "validating"]
            if self.in_flight["origin"] != "change"
            else ["planning", "generating"]
        )
        if self.ticks < len(stages):
            self.in_flight["stage"] = stages[self.ticks]
            self.ticks += 1
            return
        if self.fail_next_build:
            self.fail_next_build = False
            self.status = "ready" if self.active else "needs_attention"
            self.in_flight = None
            self.last_error = {
                "code": "PAGE_COPY_MISMATCH",
                "stage": "validate",
                "summary": "The generated page failed 1 check; first: The text for hero.intro differs.",
                "cause": "The model changed approved wording.",
                "where": [{"kind": "field", "ref": "hero.intro", "detail": "differs"}],
                "owner": "model_output",
                "retryable": True,
                "action": "Try again.",
                "issue_count": 1,
                "reference": "cg-e2e0001",
                "issues": [],
            }
            return
        origin = str(self.in_flight["origin"])
        self._finish_build("change" if origin == "change" else "initial", self.next_instruction)

    def studio_envelope(self) -> dict[str, Any]:
        return {
            "session_id": SESSION,
            "session_revision": 5,
            "code_generator": {
                "status": self.status,
                "theme_id": "editorial-forest/v1",
                "active_version_id": f"v{self.active}" if self.active else "",
                "active_version_number": self.active,
                "in_flight": self.in_flight,
                "last_error": self.last_error,
                "builds_started": 1,
            },
            "versions": self.versions,
            "chat": self.chat,
            "jobs": [],
        }

    # ── HTTP ─────────────────────────────────────────────────────────────────

    def handle(self, route: Any) -> None:
        request = route.request
        parsed = urlparse(request.url)
        path = parsed.path.removeprefix(f"/api/v1/sessions/{SESSION}")
        method = request.method
        self.log.append(f"{method} {path or '/'}")

        def ok(body: Any, status: int = 200) -> None:
            route.fulfill(status=status, content_type="application/json", body=json.dumps(body))

        def fail(status: int, code: str, message: str) -> None:
            ok({"error": {"code": code, "message": message}}, status)

        if path == "":
            ok(
                {
                    "id": SESSION,
                    "name": "Portfolio",
                    "status": "active",
                    "current_state": {},
                    "revision": 5,
                }
            )
        elif path == "/reset" and method == "POST":
            ok(
                {
                    "id": SESSION,
                    "name": "Portfolio",
                    "status": "active",
                    "current_state": {},
                    "revision": 6,
                }
            )
        elif path == "/discovery":
            ok(
                {
                    "session_id": SESSION,
                    "session_revision": 5,
                    "discovery": self.fx["discoveryApproved"],
                    "jobs": [],
                }
            )
        elif path == "/content-architect" and method == "GET":
            ok(self._content())
        elif path == "/content-architect/approve":
            self.content_approved = True
            ok(self._content())
        elif path == "/code-generator" and method == "GET":
            self._advance()
            ok(self.studio_envelope())
        elif path == "/code-generator/start":
            if self.status == "not_started" or self.status == "needs_attention":
                self._begin("initial", "")
            ok(self.studio_envelope(), 202)
        elif path == "/code-generator/stop":
            self.status = "ready" if self.active else "needs_attention"
            self.in_flight = None
            ok(self.studio_envelope())
        elif path == "/code-generator/messages":
            body = json.loads(request.post_data or "{}")
            if self.status == "build_running":
                fail(409, "CODE_GENERATOR_BUILD_IN_PROGRESS", "Your page is being built.")
                return
            self.chat.append(
                {
                    "id": f"u{len(self.chat)}",
                    "seq": len(self.chat) + 1,
                    "role": "user",
                    "kind": "message",
                    "body": body["message"],
                    "version_id": None,
                    "created_at": "2026-10-02T09:10:00+00:00",
                }
            )
            self.messages = [*getattr(self, "messages", []), body]
            self._begin("change", body["message"])
            ok(self.studio_envelope(), 202)
        elif path.startswith("/code-generator/versions/") and path.endswith("/restore"):
            self.status = "ready"
            self._finish_build("restore", "")
            ok(self.studio_envelope())
        elif path == "/code-generator/preview-grant":
            version = parse_qs(parsed.query).get("version_id", [f"v{self.active}"])[0]
            ok(
                {
                    "url": f"/studio-sample/index.html?v={version}",
                    "expires_at": "2099-01-01T00:00:00+00:00",
                    "expires_in_seconds": 1800,
                    "version_id": version,
                    "version_number": self.active,
                }
            )
        else:
            fail(404, "NOT_FOUND", f"unexpected request {method} {path}")

    def _content(self) -> dict[str, Any]:
        state = self.fx["contentApproved"] if self.content_approved else self.fx["contentReview"]
        return {
            "session_id": SESSION,
            "session_revision": 5,
            "content_architect": state,
            "jobs": [],
        }

    def install(self, page: Any) -> None:
        page.route(re.compile(rf".*/api/v1/sessions/{SESSION}.*"), self.handle)
        # Everything else the shell may call (client diagnostics) is acknowledged and ignored.
        page.route(
            re.compile(r".*/api/v1/(?!sessions/).*"),
            lambda route: route.fulfill(status=204, body=""),
        )


def _open_app(page: Any, backend_kwargs: dict[str, Any]) -> FakeBackend:
    page.unroute_all()
    install_sample_page(page)
    page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
    fixtures = page.evaluate("window.__fixtures")
    backend = FakeBackend(fixtures, **backend_kwargs)
    backend.install(page)
    page.evaluate("sessionStorage.clear()")
    page.set_viewport_size({"width": 1366, "height": 800})
    page.goto(f"{BASE_URL}/?app=1", wait_until="domcontentloaded")
    return backend


def _release_first_build_scene(page: Any, backend: FakeBackend) -> None:
    """Age the presentation marker after the fake worker reports a ready page."""
    for _ in range(15):
        if backend.status == "ready":
            break
        page.wait_for_timeout(1000)
    assert backend.status == "ready"
    page.evaluate("""() => {
      const key = 'oryxenai.studio_presentation:session-e2e';
      const marker = JSON.parse(sessionStorage.getItem(key));
      marker.startedAt = Date.now() - 31000;
      sessionStorage.setItem(key, JSON.stringify(marker));
    }""")
    # The fixture uses ?app=1 to select the production AppShell; its normal
    # history update intentionally strips that fixture-only switch.
    page.goto(f"{BASE_URL}/?app=1&stage=studio", wait_until="domcontentloaded")


def test_one_click_approves_the_plan_then_builds_and_opens_the_live_studio(
    browser_page: Any,
) -> None:
    page = browser_page
    backend = _open_app(page, {"content": "review"})
    reset = page.get_by_role("button", name="Reset pipeline")
    expect(reset).to_be_visible()
    reset_position = reset.bounding_box()
    button = page.get_by_role("button", name="Approve & generate my portfolio")
    expect(button).to_be_visible(timeout=8000)
    button.click()

    expect(page.get_by_role("heading", name="Your page is taking shape.")).to_be_visible(
        timeout=8000
    )
    expect(page).to_have_url(re.compile(r"stage=studio"))
    expect(page.get_by_text("Illustrative view")).to_be_visible()
    for _ in range(15):
        if backend.status == "ready":
            break
        page.wait_for_timeout(1000)
    assert backend.status == "ready"
    expect(page.get_by_role("heading", name="Your page is taking shape.")).to_be_visible()
    assert page.locator(".studio-workspace.is-preloading").count() == 1
    shot(page, "studio-build-scene-desktop")
    _release_first_build_scene(page, backend)
    # The build finishes through polling and the live page appears in the preview.
    frame = page.frame_locator("iframe.studio-frame.is-visible")
    expect(frame.locator("h1")).to_be_visible(timeout=20000)
    expect(page.get_by_text("Version 1", exact=True)).to_be_visible()
    expect(page.get_by_text("Your portfolio is ready (version 1).")).to_be_visible()
    expect(reset).to_be_visible()
    studio_reset_position = reset.bounding_box()
    assert reset_position and studio_reset_position
    assert (reset_position["x"], reset_position["y"]) == (
        studio_reset_position["x"],
        studio_reset_position["y"],
    )

    calls = backend.log
    approve = calls.index("POST /content-architect/approve")
    start = calls.index("POST /code-generator/start")
    assert approve < start, calls
    assert calls.count("POST /code-generator/start") == 1


def test_a_chat_change_builds_a_new_version_and_restore_goes_back(browser_page: Any) -> None:
    page = browser_page
    backend = _open_app(page, {"content": "approved", "studio": "ready"})
    expect(page).to_have_url(
        re.compile(r"stage=studio"), timeout=8000
    )  # a returning user lands in the Studio
    expect(page.get_by_text("Version 1", exact=True)).to_be_visible(timeout=8000)

    composer = page.get_by_label("Describe the change you want")
    composer.fill("Make my introduction a bit shorter")
    page.get_by_role("button", name="Send", exact=True).click()
    expect(page.get_by_text("Updating…")).to_be_visible(timeout=4000)
    expect(composer).to_be_disabled()
    expect(page.get_by_text("Version 2", exact=True)).to_be_visible(timeout=20000)
    expect(page.get_by_text("Done. I updated that part of your page.")).to_be_visible()
    expect(composer).to_be_enabled()
    assert backend.messages[0]["base_version_id"] == "v1"
    assert backend.messages[0]["client_message_id"]

    page.get_by_text("Versions (2)").click()
    page.get_by_role("button", name="Restore").click()
    expect(page.get_by_text("Version 3", exact=True)).to_be_visible(timeout=8000)
    assert "POST /code-generator/versions/v1/restore" in backend.log


def test_reset_from_studio_confirms_and_returns_to_discovery(browser_page: Any) -> None:
    page = browser_page
    backend = _open_app(page, {"content": "approved", "studio": "ready"})
    expect(page.get_by_text("Version 1", exact=True)).to_be_visible(timeout=8000)
    page.set_viewport_size({"width": 390, "height": 844})
    expect(page.get_by_role("button", name="Reset pipeline")).to_be_visible()
    assert_no_horizontal_overflow(page)
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Reset pipeline").click()
    expect(page).to_have_url(re.compile(r"stage=discover"), timeout=8000)
    assert "POST /reset" in backend.log


def test_a_failed_first_build_is_explained_and_retry_recovers(browser_page: Any) -> None:
    page = browser_page
    backend = _open_app(page, {"content": "approved", "studio": "not_started"})
    backend.fail_next_build = True
    page.get_by_role("button", name="Generate my portfolio").first.click()
    expect(page.get_by_role("heading", name="Your portfolio could not be built yet")).to_be_visible(
        timeout=20000
    )
    expect(page.get_by_text("cg-e2e0001")).to_be_visible()
    expect(page.get_by_text("hero.intro").first).to_be_visible()
    page.get_by_role("button", name="Try building again").click()
    _release_first_build_scene(page, backend)
    expect(page.locator("iframe.studio-frame.is-visible")).to_have_count(1, timeout=20000)
    expect(page.get_by_text("Version 1", exact=True)).to_be_visible()


def test_a_second_tab_started_build_is_shown_as_building_not_restarted(browser_page: Any) -> None:
    page = browser_page
    backend = _open_app(page, {"content": "approved", "studio": "not_started"})
    backend._begin("initial", "")  # another tab already started the build
    expect(page.get_by_role("heading", name="Your page is taking shape.")).to_be_visible(
        timeout=8000
    )
    expect(page.locator("iframe.studio-frame.is-visible")).to_have_count(1, timeout=20000)
    assert "POST /code-generator/start" not in backend.log


def test_private_home_guide_and_resume_routes(browser_page: Any) -> None:
    page = browser_page
    _open_app(page, {"content": "approved", "studio": "ready"})
    page.get_by_role("button", name="Home", exact=True).click()
    expect(page).to_have_url(re.compile(r"screen=home"))
    expect(page.get_by_role("heading", name="Your portfolio is ready to review.")).to_be_visible()
    expect(page.get_by_role("button", name="Open Studio preview")).to_be_visible()
    shot(page, "workspace-home-desktop")
    page.set_viewport_size({"width": 390, "height": 844})
    assert_no_horizontal_overflow(page)
    shot(page, "workspace-home-mobile")
    page.set_viewport_size({"width": 1366, "height": 800})
    page.get_by_role("button", name="Guide", exact=True).click()
    expect(page).to_have_url(re.compile(r"screen=guide"))
    expect(
        page.get_by_role("heading", name="From raw material to a page you can see.")
    ).to_be_visible()
    page.get_by_label("About private preview").click()
    expect(
        page.get_by_text("Only the signed-in owner can open this preview.", exact=False)
    ).to_be_visible()
    shot(page, "workspace-guide-desktop")
    page.set_viewport_size({"width": 390, "height": 844})
    assert_no_horizontal_overflow(page)
    shot(page, "workspace-guide-mobile")
    page.set_viewport_size({"width": 1366, "height": 800})
    page.go_back()
    expect(page.get_by_role("heading", name="Your portfolio is ready to review.")).to_be_visible()
    page.get_by_role("button", name="Open Studio preview").click()
    expect(page).to_have_url(re.compile(r"stage=studio"))
    page.set_viewport_size({"width": 1024, "height": 768})
    assert_no_horizontal_overflow(page)
    brand = page.locator(".app-brand").bounding_box()
    nav = page.locator(".workspace-topnav").bounding_box()
    journey = page.locator(".journey-nav").bounding_box()
    actions = page.locator(".app-topbar-actions").bounding_box()
    assert brand and nav and journey and actions
    assert brand["x"] + brand["width"] <= nav["x"] + 1
    assert nav["x"] + nav["width"] <= journey["x"] + 1
    assert journey["x"] + journey["width"] <= actions["x"] + 1
    page.goto(f"{BASE_URL}/?app=1&screen=guide", wait_until="domcontentloaded")
    expect(
        page.get_by_role("heading", name="From raw material to a page you can see.")
    ).to_be_visible()


def test_the_fake_backend_speaks_the_real_envelope() -> None:
    """No browser: the fake must carry the same keys the real API test pins."""
    from tests.browser.studio_contract import (
        ENVELOPE_KEYS,
        FRONTEND_CHAT_KEYS,
        FRONTEND_FAILURE_KEYS,
        FRONTEND_IN_FLIGHT_KEYS,
        FRONTEND_STATE_KEYS,
        FRONTEND_VERSION_KEYS,
    )

    backend = FakeBackend({}, content="approved", studio="ready")
    envelope = backend.studio_envelope()
    assert set(envelope) == ENVELOPE_KEYS
    assert set(envelope["code_generator"]) >= FRONTEND_STATE_KEYS
    assert set(envelope["versions"][0]) >= FRONTEND_VERSION_KEYS
    assert set(envelope["chat"][0]) >= FRONTEND_CHAT_KEYS
    backend._begin("change", "x")
    assert set(backend.studio_envelope()["code_generator"]["in_flight"]) >= FRONTEND_IN_FLIGHT_KEYS
    backend.fail_next_build = True
    for _ in range(4):
        backend._advance()
    assert set(backend.last_error or {}) >= FRONTEND_FAILURE_KEYS
