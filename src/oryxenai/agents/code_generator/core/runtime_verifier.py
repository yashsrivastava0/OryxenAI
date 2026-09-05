"""DOM/runtime verification, plus optional advisory screenshot capture.

Pass/fail verdicts remain purely structural (DOM order, computed-style
geometry, console/CSP/outbound-network checks) -- a screenshot, when
`screenshot_dir` is supplied, is captured for human/visual review only and
never affects a journey's `passed` outcome or diagnostics.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Any, cast
from urllib.parse import urljoin, urlsplit

from oryxenai.agents.code_generator.core.development_schemas import (
    DesignRealizationContract,
    Diagnostic,
    RuntimeEvidence,
    VerificationJourney,
    VerificationPlan,
    VerificationProfile,
)
from oryxenai.core.logging import get_logger

logger = get_logger("oryxenai.agents.code_generator.runtime_verifier")

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9_-]+")


def _safe_filename(value: str) -> str:
    """Collapse a journey_id (e.g. "direct:home", "interaction:hero-cta")
    into a filesystem-safe name -- ':' and other separators are not valid
    in Windows filenames."""

    return _UNSAFE_FILENAME_CHARS.sub("_", value).strip("_") or "journey"


def _diagnostic(
    code: str, message: str, *, journey_id: str = "", route_id: str = "", owner: str = "generator"
) -> Diagnostic:
    fingerprint = hashlib.sha256(f"{code}:{journey_id}:{route_id}:{message}".encode()).hexdigest()[
        :24
    ]
    return Diagnostic(
        diagnostic_id=f"diagnostic-{fingerprint}",
        group="dom_runtime",
        code=code,
        owner=owner,  # type: ignore[arg-type]
        phase="dom_runtime",
        route_id=route_id,
        interaction_id=journey_id.removeprefix("interaction:"),
        normalized_message=message[:4000],
        fingerprint=fingerprint,
    )


def _mounted_route_paths(base_url: str, route_paths: list[str]) -> list[str]:
    """Accept logical route paths and their nested preview mount paths.

    ``publicRouteUrl`` deliberately emits the browser-visible mounted path
    while the plan stores the portfolio's logical route path. Keeping both
    representations in the runtime allow-list preserves the route contract
    without mistaking the preview gateway prefix for an unapproved route.
    """

    base_path = urlsplit(base_url).path or "/"
    prefix = "/" + base_path.strip("/") + "/" if base_path.strip("/") else "/"
    mounted = {f"{prefix}{path.lstrip('/')}" if prefix != "/" else path for path in route_paths}
    return sorted({*route_paths, *mounted})


def _validate_interaction_state(
    state_before: dict[str, Any], state_after: dict[str, Any], outcome: str
) -> None:
    """Validate directional and bidirectional disclosure outcomes."""

    normalized = outcome.casefold()
    expands = any(token in normalized for token in ("open", "expand", "show"))
    collapses = any(token in normalized for token in ("close", "collapse", "hide"))
    if expands and collapses:
        # A toggle contract intentionally allows either final state. Verify
        # that the action changed the controlled state instead of imposing one
        # branch of the approved behavior.
        before_expanded = state_before.get("expanded")
        after_expanded = state_after.get("expanded")
        if (
            before_expanded is not None
            and after_expanded is not None
            and before_expanded == after_expanded
        ):
            raise AssertionError("The toggle interaction did not change its controlled state.")
    elif expands:
        if state_after.get("expanded") is not None and state_after.get("expanded") != "true":
            raise AssertionError("The interaction did not open or expand its controlled state.")
        if state_after.get("expanded") is None and any(
            token in normalized for token in ("menu", "disclosure", "expand")
        ):
            raise AssertionError("The declared expandable interaction has no aria-expanded state.")
    elif collapses and state_after.get("expanded") == "true":
        raise AssertionError("The interaction left its declared collapsed state open.")


def _browser_environment() -> dict[str, str]:
    """Give the browser an isolated writable profile root.

    The worker image runs as a non-root user with ``HOME=/app``.  The image
    owns the application files but not that directory itself, so Chromium's
    crashpad setup can terminate before Playwright connects.  Browser state
    is disposable verification state and belongs in the OS temp directory,
    never in the generated portfolio or the user's home directory.
    """

    root = Path(tempfile.gettempdir()) / "oryxenai-browser"
    directories = {
        "HOME": root / "home",
        "XDG_CONFIG_HOME": root / "config",
        "XDG_CACHE_HOME": root / "cache",
        "XDG_RUNTIME_DIR": root / "runtime",
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    environment = {key: str(value) for key, value in os.environ.items()}
    environment.update({key: str(value) for key, value in directories.items()})
    return environment


class RuntimeVerifier:
    """Runs deterministic journeys against a promoted-candidate gateway."""

    async def verify(
        self,
        base_url: str,
        *,
        plan: VerificationPlan,
        profile: VerificationProfile,
        timeout_ms: int = 15_000,
        verification_token: str = "",
        screenshot_dir: Path | None = None,
    ) -> tuple[list[RuntimeEvidence], list[Diagnostic]]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return [], [
                _diagnostic(
                    "BROWSER_UNAVAILABLE",
                    "Playwright is not installed in the verification runtime.",
                    owner="infrastructure",
                )
            ]
        origin = urlsplit(base_url)
        if not origin.scheme or not origin.netloc:
            return [], [
                _diagnostic(
                    "PREVIEW_URL_INVALID",
                    "The candidate gateway URL is invalid.",
                    owner="infrastructure",
                )
            ]
        evidence: list[RuntimeEvidence] = []
        diagnostics: list[Diagnostic] = []
        expected_runtime_paths = _mounted_route_paths(base_url, plan.expected_route_paths)
        if screenshot_dir is not None:
            screenshot_dir.mkdir(parents=True, exist_ok=True)
        async with async_playwright() as playwright:
            browser_type = getattr(playwright, profile.browser_name, None)
            if browser_type is None:
                return [], [
                    _diagnostic(
                        "BROWSER_UNSUPPORTED",
                        "The configured browser is unavailable.",
                        owner="infrastructure",
                    )
                ]
            launch_kwargs: dict[str, Any] = {"headless": True}
            launch_kwargs["env"] = _browser_environment()
            if profile.browser_executable:
                launch_kwargs["executable_path"] = profile.browser_executable
            browser: Any = None
            last_error: Exception | None = None
            # One retry: first launches on a cold Windows profile can lose a
            # race with browser-process setup without the browser being broken.
            for attempt in range(2):
                try:
                    browser = await browser_type.launch(**launch_kwargs)
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt == 0:
                        await asyncio.sleep(1.0)
            if browser is None:
                assert last_error is not None
                return [], [
                    _diagnostic("BROWSER_START_FAILED", str(last_error), owner="infrastructure")
                ]
            try:
                for journey in plan.runtime_journeys:
                    realization_contract = next(
                        (
                            item
                            for item in plan.realization_contracts
                            if item.route_id == journey.route_id
                        ),
                        None,
                    )
                    journey_evidence, journey_diagnostics = await self._run_journey(
                        browser,
                        base_url,
                        origin.netloc,
                        journey,
                        profile,
                        expected_runtime_paths,
                        timeout_ms,
                        verification_token,
                        realization_contract,
                        screenshot_dir,
                    )
                    evidence.append(journey_evidence)
                    diagnostics.extend(journey_diagnostics)
            finally:
                await browser.close()
            # The same rendered defect (e.g. one nav link with a small touch
            # target) is frequently caught by more than one journey/viewport
            # combination -- confirmed live: 6 identically-fingerprinted
            # RUNTIME_TOUCH_TARGET_TOO_SMALL entries for one real element,
            # inside an already-large diagnostic bundle. Repeating the exact
            # same fact adds no information for a repair attempt and only
            # makes an already-hard multi-issue bundle look larger; keep the
            # first occurrence of each fingerprint.
            seen_fingerprints: set[str] = set()
            deduplicated: list[Diagnostic] = []
            for diagnostic in diagnostics:
                if diagnostic.fingerprint in seen_fingerprints:
                    continue
                seen_fingerprints.add(diagnostic.fingerprint)
                deduplicated.append(diagnostic)
            diagnostics = deduplicated
        return evidence, diagnostics

    async def _run_journey(
        self,
        browser: Any,
        base_url: str,
        expected_netloc: str,
        journey: VerificationJourney,
        profile: VerificationProfile,
        expected_route_paths: list[str],
        timeout_ms: int,
        verification_token: str,
        realization_contract: DesignRealizationContract | None,
        screenshot_dir: Path | None = None,
    ) -> tuple[RuntimeEvidence, list[Diagnostic]]:
        viewport = profile.viewport_profiles.get(journey.viewport_profile) or {
            "width": 1440,
            "height": 900,
        }
        context = await browser.new_context(
            viewport={"width": int(viewport["width"]), "height": int(viewport["height"])},
            reduced_motion=journey.motion_profile,
            service_workers="block",
            extra_http_headers=(
                {"X-Preview-Verify-Token": verification_token} if verification_token else None
            ),
        )
        if verification_token:
            # Keep the auth header on the context as well as on construction.
            # Playwright can recreate the initial document request while a
            # route handler is installed; the context-level setter guarantees
            # that the protected candidate gateway sees the token on every
            # navigation and subresource request.
            await context.set_extra_http_headers({"X-Preview-Verify-Token": verification_token})
        page = await context.new_page()
        page.set_default_timeout(timeout_ms)
        requests: list[dict[str, str | int | bool]] = []
        console_errors: list[str] = []
        page_errors: list[str] = []
        csp_violations: list[str] = []
        diagnostics: list[Diagnostic] = []

        def record_request(request: Any) -> None:
            url = str(request.url)
            requests.append(
                {
                    "url": url,
                    "method": str(request.method),
                    "resource_type": str(request.resource_type),
                }
            )

        def record_console(message: Any) -> None:
            text = str(message.text)
            if str(message.type) in {"error", "warning"}:
                console_errors.append(text[:1000])
            if "content security policy" in text.casefold() or "csp" in text.casefold():
                csp_violations.append(text[:1000])

        def record_page_error(error: Any) -> None:
            page_errors.append(str(error)[:1000])

        def record_response(response: Any) -> None:
            status = int(response.status)
            if status >= 400:
                failure: dict[str, str | int | bool] = {
                    "url": str(response.url),
                    "status": status,
                    "failed": True,
                }
                gateway_reason = str(response.headers.get("x-oryxenai-candidate-404", ""))
                if gateway_reason:
                    failure["gateway_reason"] = gateway_reason
                requests.append(failure)

        def record_request_failed(request: Any) -> None:
            requests.append(
                {
                    "url": str(request.url),
                    "method": str(request.method),
                    "failed": True,
                }
            )

        page.on("request", record_request)
        page.on("console", record_console)
        page.on("pageerror", record_page_error)
        page.on("response", record_response)
        page.on("requestfailed", record_request_failed)

        async def protect_request(route: Any) -> None:
            request_url = urlsplit(str(route.request.url))
            if (
                request_url.netloc != expected_netloc
                or request_url.scheme != urlsplit(base_url).scheme
            ):
                requests.append(
                    {
                        "url": str(route.request.url),
                        "method": str(route.request.method),
                        "outbound": True,
                    }
                )
                await route.abort("blockedbyclient")
                return
            if verification_token:
                # Route interception can rebuild a request's headers. Inject
                # the ephemeral token at the final request boundary so a
                # protected candidate cannot intermittently become a 404
                # merely because the browser recreated a navigation request.
                headers = await route.request.all_headers()
                headers["x-preview-verify-token"] = verification_token
                await route.continue_(headers=headers)
                return
            await route.continue_()

        await context.route("**/*", protect_request)
        passed = True
        title = ""
        final_url = ""
        content_ids: list[str] = []
        focus_results: list[dict[str, str | bool]] = []
        overflow_results: list[dict[str, str | int | bool]] = []
        geometry_results: list[dict[str, Any]] = []
        realization_results: list[dict[str, Any]] = []
        screenshot_relative_path = ""
        try:
            for step in journey.steps:
                await self._step(
                    page,
                    base_url,
                    step,
                    journey,
                    content_ids,
                    focus_results,
                    overflow_results,
                    geometry_results,
                    profile.geometry_thresholds,
                )
            if screenshot_dir is not None:
                # Advisory only: a screenshot failure must never affect the
                # journey's pass/fail outcome or raise past this block. This
                # is the only place in the whole verification pipeline that
                # captures any visual evidence of a generated portfolio.
                try:
                    screenshot_name = f"{_safe_filename(journey.journey_id)}.png"
                    await page.screenshot(
                        path=str(screenshot_dir / screenshot_name), full_page=True
                    )
                    screenshot_relative_path = screenshot_name
                except Exception:
                    logger.warning(
                        "verification screenshot capture failed journey_id=%s",
                        journey.journey_id,
                        exc_info=True,
                    )
            for result in geometry_results:
                for violation in result.get("violations", []):
                    if not isinstance(violation, dict):
                        continue
                    passed = False
                    diagnostics.append(
                        _diagnostic(
                            str(violation.get("code", "RUNTIME_GEOMETRY_INVALID")),
                            str(violation.get("message", "The page failed a geometry check.")),
                            journey_id=journey.journey_id,
                            route_id=journey.route_id,
                        )
                    )
            if realization_contract is not None and journey.journey_id.startswith(
                ("direct:", "reduced-motion:")
            ):
                realization_result = await self._assert_design_realization(
                    page,
                    realization_contract,
                    viewport_name=journey.viewport_profile,
                    reduced_motion=journey.motion_profile == "reduce",
                )
                realization_results.append(realization_result)
                for violation in realization_result.get("violations", []):
                    if not isinstance(violation, dict):
                        continue
                    passed = False
                    diagnostics.append(
                        _diagnostic(
                            str(violation.get("code", "RUNTIME_REALIZATION_INVALID")),
                            str(
                                violation.get("message", "The design-realization contract failed.")
                            ),
                            journey_id=journey.journey_id,
                            route_id=journey.route_id,
                        )
                    )
            visual_state = await page.evaluate(
                """expectedPaths => ({
                  bodyText: document.body?.innerText?.trim().length ?? 0,
                  mainCount: document.querySelectorAll('main').length,
                  h1Count: document.querySelectorAll('main h1').length,
                  sectionIds: Array.from(document.querySelectorAll('main [data-content-id]'))
                    .map(element => element.getAttribute('data-content-id') || ''),
                  duplicateDomIds: Array.from(document.querySelectorAll('[id]'))
                    .map(element => element.id)
                    .filter((value, index, values) => values.indexOf(value) !== index),
                  duplicateInteractionIds: Array.from(document.querySelectorAll('[data-interaction-id]'))
                    .map(element => element.getAttribute('data-interaction-id') || '')
                    .filter((value, index, values) => values.indexOf(value) !== index),
                  unresolvedAnchors: Array.from(document.querySelectorAll('a[href^="#"]'))
                    .map(anchor => anchor.getAttribute('href') || '')
                    .filter(href => href.length > 1 && !document.getElementById(href.slice(1))),
                  unresolvedInternalRoutes: Array.from(document.querySelectorAll('a[href]'))
                    .map(anchor => anchor.getAttribute('href') || '')
                    .filter(href => href.startsWith('/') &&
                      !href.startsWith('//') &&
                      !new Set(expectedPaths).has((href.split('#')[0] || '/'))),
                  brokenImages: Array.from(document.images)
                    .filter(image => image.complete && image.naturalWidth === 0)
                    .map(image => image.currentSrc || image.src),
                })""",
                [str(item) for item in expected_route_paths],
            )
            if (
                int(visual_state.get("bodyText", 0)) == 0
                or int(visual_state.get("mainCount", 0)) == 0
            ):
                passed = False
                diagnostics.append(
                    _diagnostic(
                        "RUNTIME_EMPTY_SHELL",
                        "The route rendered without a visible body or main landmark.",
                        journey_id=journey.journey_id,
                        route_id=journey.route_id,
                    )
                )
            if int(visual_state.get("mainCount", 0)) != 1:
                passed = False
                diagnostics.append(
                    _diagnostic(
                        "RUNTIME_MAIN_COUNT_INVALID",
                        "The rendered route must contain exactly one main landmark.",
                        journey_id=journey.journey_id,
                        route_id=journey.route_id,
                    )
                )
            if journey.route_id and int(visual_state.get("h1Count", 0)) != 1:
                passed = False
                diagnostics.append(
                    _diagnostic(
                        "RUNTIME_H1_COUNT_INVALID",
                        "The rendered route must contain exactly one h1 heading.",
                        journey_id=journey.journey_id,
                        route_id=journey.route_id,
                    )
                )
            expected_content_ids = next(
                (
                    list(step.expected_content_ids)
                    for step in journey.steps
                    if step.expected_content_ids
                ),
                [],
            )
            observed_content_ids = [
                str(value) for value in visual_state.get("sectionIds", []) if str(value)
            ]
            if expected_content_ids and observed_content_ids != expected_content_ids:
                passed = False
                diagnostics.append(
                    _diagnostic(
                        "RUNTIME_SECTION_ORDER_INVALID",
                        "Rendered section anchors do not match the approved route order.",
                        journey_id=journey.journey_id,
                        route_id=journey.route_id,
                    )
                )
            duplicate_ids = sorted(
                {str(value) for value in visual_state.get("duplicateDomIds", []) if str(value)}
            )
            if duplicate_ids:
                passed = False
                diagnostics.append(
                    _diagnostic(
                        "RUNTIME_DOM_ID_DUPLICATE",
                        "The rendered route contains duplicate DOM identifiers: "
                        + ", ".join(duplicate_ids[:4]),
                        journey_id=journey.journey_id,
                        route_id=journey.route_id,
                    )
                )
            duplicate_interactions = sorted(
                {
                    str(value)
                    for value in visual_state.get("duplicateInteractionIds", [])
                    if str(value)
                }
            )
            if duplicate_interactions:
                passed = False
                diagnostics.append(
                    _diagnostic(
                        "RUNTIME_INTERACTION_ID_DUPLICATE",
                        "The rendered route contains duplicate interaction identifiers: "
                        + ", ".join(duplicate_interactions[:4]),
                        journey_id=journey.journey_id,
                        route_id=journey.route_id,
                    )
                )
            unresolved_anchors = [
                str(value) for value in visual_state.get("unresolvedAnchors", []) if str(value)
            ]
            if unresolved_anchors:
                passed = False
                diagnostics.append(
                    _diagnostic(
                        "RUNTIME_ANCHOR_TARGET_MISSING",
                        "The rendered route contains an anchor without a local target: "
                        + ", ".join(unresolved_anchors[:4]),
                        journey_id=journey.journey_id,
                        route_id=journey.route_id,
                    )
                )
            unresolved_routes = [
                str(value)
                for value in visual_state.get("unresolvedInternalRoutes", [])
                if str(value)
            ]
            if unresolved_routes:
                passed = False
                diagnostics.append(
                    _diagnostic(
                        "RUNTIME_INTERNAL_ROUTE_UNRESOLVED",
                        "The rendered route contains a link to an unapproved internal path: "
                        + ", ".join(unresolved_routes[:4]),
                        journey_id=journey.journey_id,
                        route_id=journey.route_id,
                    )
                )
            broken_images = [str(value) for value in visual_state.get("brokenImages", [])]
            if broken_images:
                passed = False
                diagnostics.append(
                    _diagnostic(
                        "RUNTIME_IMAGE_DECODE_FAILED",
                        "A local image element completed with no decoded pixels: "
                        + ", ".join(broken_images[:4]),
                        journey_id=journey.journey_id,
                        route_id=journey.route_id,
                    )
                )
            title = await page.title()
            final_url = page.url
        except Exception as exc:
            passed = False
            diagnostics.append(
                _diagnostic(
                    "RUNTIME_ASSERTION_FAILED",
                    str(exc),
                    journey_id=journey.journey_id,
                    route_id=journey.route_id,
                )
            )
        if console_errors:
            passed = False
            diagnostics.append(
                _diagnostic(
                    "RUNTIME_CONSOLE_ERROR",
                    "The candidate emitted a blocking console error.",
                    journey_id=journey.journey_id,
                    route_id=journey.route_id,
                )
            )
        if page_errors:
            passed = False
            diagnostics.append(
                _diagnostic(
                    "RUNTIME_PAGE_ERROR",
                    "The candidate raised an uncaught page error.",
                    journey_id=journey.journey_id,
                    route_id=journey.route_id,
                )
            )
        if csp_violations:
            passed = False
            diagnostics.append(
                _diagnostic(
                    "RUNTIME_CSP_VIOLATION",
                    "The candidate violated its content security policy.",
                    journey_id=journey.journey_id,
                    route_id=journey.route_id,
                )
            )
        outbound = [
            item
            for item in requests
            if bool(item.get("outbound"))
            or self._is_outbound_request(item, expected_netloc, base_url)
        ]
        if outbound:
            passed = False
            diagnostics.append(
                _diagnostic(
                    "RUNTIME_OUTBOUND_REQUEST",
                    "The candidate attempted an outbound runtime request.",
                    journey_id=journey.journey_id,
                    route_id=journey.route_id,
                )
            )
        local_failures = [
            item
            for item in requests
            if bool(item.get("failed"))
            and not bool(item.get("outbound"))
            and not self._is_outbound_request(item, expected_netloc, base_url)
        ]
        if local_failures:
            passed = False
            diagnostics.append(
                _diagnostic(
                    "RUNTIME_ASSET_FAILED",
                    "The candidate requested a local resource that failed to load.",
                    journey_id=journey.journey_id,
                    route_id=journey.route_id,
                )
            )
        await context.close()
        return (
            RuntimeEvidence(
                journey_id=journey.journey_id,
                route_id=journey.route_id,
                start_path=journey.start_path,
                final_url=final_url,
                title=title,
                content_ids=content_ids,
                requests=requests,
                console_errors=console_errors,
                page_errors=page_errors,
                csp_violations=csp_violations,
                focus_results=focus_results,
                overflow_results=overflow_results,
                geometry_results=geometry_results,
                realization_results=realization_results,
                passed=passed,
                screenshot_relative_path=screenshot_relative_path,
            ),
            diagnostics,
        )

    @staticmethod
    def _is_outbound_request(
        request: dict[str, str | int | bool], expected_netloc: str, base_url: str
    ) -> bool:
        url = urlsplit(str(request.get("url", "")))
        return url.netloc != expected_netloc or url.scheme != urlsplit(base_url).scheme

    async def _step(
        self,
        page: Any,
        base_url: str,
        step: Any,
        journey: VerificationJourney,
        content_ids: list[str],
        focus_results: list[dict[str, str | bool]],
        overflow_results: list[dict[str, str | int | bool]],
        geometry_results: list[dict[str, Any]],
        geometry_thresholds: dict[str, float],
    ) -> None:
        if step.action == "load":
            application_path = step.expected_url or journey.start_path
            target = urljoin(base_url.rstrip("/") + "/", application_path.lstrip("/"))
            await page.goto(target, wait_until="networkidle")
            if (
                step.expected_url
                and self._application_path(page.url, base_url) != step.expected_url
            ):
                raise AssertionError(f"Expected URL path {step.expected_url}, observed {page.url}")
            await self._assert_content(page, step, content_ids)
        elif step.action == "navigate":
            await page.locator(step.target).first.click()
            await page.wait_for_load_state("networkidle")
            if (
                step.expected_url
                and self._application_path(page.url, base_url) != step.expected_url
            ):
                raise AssertionError(
                    f"Expected navigation to {step.expected_url}, observed {page.url}"
                )
        elif step.action == "back":
            await page.go_back(wait_until="networkidle")
        elif step.action == "forward":
            await page.go_forward(wait_until="networkidle")
        elif step.action == "assert_link":
            locator = page.locator(step.target).first
            await self._ensure_interaction_visible(page, locator)
            await locator.wait_for(state="attached")
            observed_href = await locator.get_attribute("href")
            if step.expected_url and observed_href != step.expected_url:
                raise AssertionError(
                    f"Expected link href {step.expected_url}, observed {observed_href}"
                )
            if step.expected_accessible_name:
                observed = (
                    await locator.get_attribute("aria-label")
                    or (await locator.inner_text()).strip()
                )
                if step.expected_accessible_name.casefold() not in str(observed).casefold():
                    raise AssertionError(
                        f"Expected accessible name {step.expected_accessible_name}, observed {observed}"
                    )
        elif step.action in {"click", "focus", "press"}:
            locator = page.locator(step.target).first
            await self._ensure_interaction_visible(page, locator)
            state_before = await locator.evaluate(
                "element => ({expanded: element.getAttribute('aria-expanded'), "
                "pressed: element.getAttribute('aria-pressed')})"
            )
            if step.action == "click":
                if "download" in step.expected_outcome.casefold():
                    async with page.expect_download() as download_info:
                        await locator.click()
                    download = await download_info.value
                    if not str(download.suggested_filename or download.path):
                        raise AssertionError("The declared download interaction produced no file.")
                else:
                    await locator.click()
            elif step.action == "focus":
                await locator.focus()
            else:
                await locator.press("Enter")
            if (
                step.expected_url
                and self._application_path(page.url, base_url) != step.expected_url
            ):
                raise AssertionError(
                    f"Expected interaction URL {step.expected_url}, observed {page.url}"
                )
            if step.expected_accessible_name:
                observed = (
                    await locator.get_attribute("aria-label")
                    or (await locator.inner_text()).strip()
                )
                # Containment, not equality: the plan carries a human label,
                # the rendered control carries the approved copy.
                if step.expected_accessible_name.casefold() not in str(observed).casefold():
                    raise AssertionError(
                        f"Expected accessible name {step.expected_accessible_name}, observed {observed}"
                    )
            state = await locator.evaluate(
                "element => ({expanded: element.getAttribute('aria-expanded'), "
                "pressed: element.getAttribute('aria-pressed')})"
            )
            _validate_interaction_state(state_before, state, step.expected_outcome)
            if (
                bool(step.expected_accessible_state.get("escape_closes"))
                and state.get("expanded") == "true"
            ):
                await page.keyboard.press("Escape")
                await page.wait_for_function(
                    "selector => document.querySelector(selector)?.getAttribute('aria-expanded') !== 'true'",
                    arg=step.target,
                )
                if bool(step.expected_accessible_state.get("focus_return")):
                    focused = await locator.evaluate(
                        "element => document.activeElement === element"
                    )
                    if not focused:
                        raise AssertionError(
                            "Escape did not return focus to the interaction trigger."
                        )
            focus_results.append(
                {
                    "step_id": step.step_id,
                    "focused": await locator.evaluate(
                        "element => document.activeElement === element"
                    ),
                }
            )
        elif step.action == "assert_content":
            await self._assert_content(page, step, content_ids)
        elif step.action == "assert_accessible":
            locator = page.locator(step.target).first
            await locator.wait_for(state="visible")
        elif step.action == "assert_overflow":
            result = await page.evaluate(
                """() => ({scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth})"""
            )
            overflow_results.append(
                {
                    "step_id": step.step_id,
                    **result,
                    "passed": result["scrollWidth"] <= result["innerWidth"],
                }
            )
            if result["scrollWidth"] > result["innerWidth"]:
                raise AssertionError("The page has horizontal overflow.")
        elif step.action == "assert_geometry":
            thresholds = {
                "minTextPx": float(geometry_thresholds.get("min_text_px", 12.0)),
                "minTouchTargetPx": float(geometry_thresholds.get("min_touch_target_px", 36.0)),
                "maxSectionGapVh": float(geometry_thresholds.get("max_section_gap_vh", 0.9)),
                "maxSectionOverlapRatio": float(
                    geometry_thresholds.get("max_section_overlap_ratio", 0.2)
                ),
            }
            result = await page.evaluate(
                """thresholds => {
                  const visible = element => {
                    const style = getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    // Contract/skip-link markers may be deliberately kept in
                    // the DOM for accessibility or source acceptance while
                    // remaining non-rendered. They must not be treated as
                    // user-facing controls in geometry checks.
                    if (element.closest('[aria-hidden="true"], [hidden], [inert]')) return false;
                    const visuallyHidden = rect.width <= 2 && rect.height <= 2 &&
                      style.overflow === 'hidden' && style.clip !== 'auto' &&
                      style.clip !== 'rect(auto, auto, auto, auto)';
                    if (visuallyHidden && !element.matches(':focus')) return false;
                    // Skip links are intentionally translated just outside
                    // the viewport until focus. They remain in document flow
                    // for keyboard users but are not actionable touch
                    // targets in the resting state.
                    if (rect.right <= 0 || rect.left >= innerWidth || rect.bottom <= 0) return false;
                    return style.display !== 'none' && style.visibility !== 'hidden' &&
                      Number(style.opacity) > 0 && rect.width > 0 && rect.height > 0;
                  };
                  const label = element => element.getAttribute('data-content-id') ||
                    element.id || element.getAttribute('aria-label') ||
                    element.tagName.toLowerCase();
                  const violations = [];
                  const main = document.querySelector('main');
                  const mainRect = main?.getBoundingClientRect();
                  if (!mainRect || mainRect.width < Math.min(280, innerWidth * 0.7) || mainRect.height < 80) {
                    violations.push({code: 'RUNTIME_MAIN_GEOMETRY_INVALID', message: 'The main composition has implausibly small rendered geometry.'});
                  }
                  const sections = Array.from(document.querySelectorAll('main [data-content-id], main > section'))
                    .filter(visible)
                    .map(element => ({element, rect: element.getBoundingClientRect(), style: getComputedStyle(element)}))
                    .sort((a, b) => a.rect.top - b.rect.top);
                  for (const item of sections) {
                    if (item.rect.left < -2 || item.rect.right > innerWidth + 2) {
                      violations.push({code: 'RUNTIME_CONTENT_OUT_OF_VIEWPORT', message: `Content ${label(item.element)} escapes the viewport.`});
                    }
                    if (item.rect.height < 24) {
                      violations.push({code: 'RUNTIME_SECTION_COLLAPSED', message: `Content ${label(item.element)} collapsed below a usable height.`});
                    }
                  }
                  for (let index = 1; index < sections.length; index += 1) {
                    const previous = sections[index - 1];
                    const current = sections[index];
                    const gap = current.rect.top - previous.rect.bottom;
                    if (gap > innerHeight * thresholds.maxSectionGapVh) {
                      violations.push({code: 'RUNTIME_SECTION_GAP_EXCESSIVE', message: `Adjacent content blocks have an excessive ${Math.round(gap)}px gap.`});
                    }
                    const overlap = Math.max(0, previous.rect.bottom - current.rect.top);
                    const overlapRatio = overlap / Math.max(1, Math.min(previous.rect.height, current.rect.height));
                    const positioned = ['absolute', 'fixed'].includes(previous.style.position) || ['absolute', 'fixed'].includes(current.style.position);
                    if (!positioned && overlapRatio > thresholds.maxSectionOverlapRatio) {
                      violations.push({code: 'RUNTIME_SECTION_COLLISION', message: `Adjacent content blocks collide by ${Math.round(overlapRatio * 100)}%.`});
                    }
                  }
                  const controls = Array.from(document.querySelectorAll('a[href], button, input, select, textarea, [role="button"]'))
                    .filter(visible)
                    .filter(element => element.tagName !== 'A' || getComputedStyle(element).display !== 'inline' || Boolean(element.closest('nav')));
                  for (const control of controls) {
                    const rect = control.getBoundingClientRect();
                    if (innerWidth <= 768 && (rect.width < thresholds.minTouchTargetPx || rect.height < thresholds.minTouchTargetPx)) {
                      violations.push({code: 'RUNTIME_TOUCH_TARGET_TOO_SMALL', message: `Interactive control ${label(control)} is smaller than the configured touch target.`});
                    }
                  }
                  const textNodes = Array.from(document.querySelectorAll('main h1, main h2, main h3, main p, main li, main a, main button')).filter(visible);
                  for (const element of textNodes) {
                    const style = getComputedStyle(element);
                    const fontSize = Number.parseFloat(style.fontSize);
                    const lineHeight = Number.parseFloat(style.lineHeight);
                    if (fontSize < thresholds.minTextPx) {
                      violations.push({code: 'RUNTIME_TEXT_TOO_SMALL', message: `Text in ${label(element)} is ${fontSize}px.`});
                    }
                    // Tight display typography is valid for headings; prose
                    // still requires a readable 1.2 ratio.
                    const minimumLineRatio = element.matches('p, li') ? 1.2 :
                      (element.matches('h1, h2, h3') ? 0.9 : 1.0);
                    if (Number.isFinite(lineHeight) && lineHeight + 0.5 < fontSize * minimumLineRatio) {
                      violations.push({code: 'RUNTIME_LINE_HEIGHT_TOO_TIGHT', message: `Text in ${label(element)} has an unusably tight line height.`});
                    }
                    if (['hidden', 'clip'].includes(style.overflow) &&
                        (element.scrollWidth > element.clientWidth + 2 || element.scrollHeight > element.clientHeight + 2)) {
                      violations.push({code: 'RUNTIME_TEXT_CLIPPED', message: `Text in ${label(element)} is clipped by its container.`});
                    }
                  }
                  if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
                    const unsafeMotion = Array.from(document.querySelectorAll('main *'))
                      .filter(visible)
                      .filter(element => {
                        const style = getComputedStyle(element);
                        const durations = style.animationDuration.split(',').map(value => Number.parseFloat(value) * (value.includes('ms') ? 1 : 1000));
                        return style.animationName !== 'none' && durations.some(value => value > 20);
                      });
                    if (unsafeMotion.length) {
                      violations.push({code: 'RUNTIME_REDUCED_MOTION_UNSAFE', message: `${unsafeMotion.length} visible elements retain non-trivial animation under reduced motion.`});
                    }
                  }
                  return {
                    viewport: {width: innerWidth, height: innerHeight},
                    main: mainRect ? {width: Math.round(mainRect.width), height: Math.round(mainRect.height)} : null,
                    sectionCount: sections.length,
                    controlCount: controls.length,
                    checkedTextCount: textNodes.length,
                    violations: violations.slice(0, 24),
                  };
                }""",
                thresholds,
            )
            geometry_results.append({"step_id": step.step_id, **result})

    async def _assert_design_realization(
        self,
        page: Any,
        contract: DesignRealizationContract,
        *,
        viewport_name: str,
        reduced_motion: bool,
    ) -> dict[str, Any]:
        payload = {
            "contract": contract.model_dump(mode="json"),
            "viewport": viewport_name,
            "reducedMotion": reduced_motion,
        }
        result = cast(
            dict[str, Any],
            await page.evaluate(
                r"""async payload => {
              const contract = payload.contract;
              const viewport = payload.viewport;
              const violations = [];
              const checked = [];
              const visible = element => {
                if (!element) return false;
                const style = getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden' &&
                  Number(style.opacity) > 0 && rect.width > 0 && rect.height > 0;
              };
              const one = (selector, code, label) => {
                let values;
                try { values = document.querySelectorAll(selector); }
                catch (_error) {
                  violations.push({code, message: `${label} uses an invalid selector: ${selector}`});
                  return null;
                }
                if (values.length !== 1) {
                  violations.push({code, message: `${label} selector ${selector} matched ${values.length} elements.`});
                  return values[0] || null;
                }
                if (!visible(values[0])) {
                  violations.push({code, message: `${label} selector ${selector} has no visible geometry.`});
                }
                return values[0];
              };
              const propertyValue = (style, name) => style.getPropertyValue(name).trim() || style[name] || '';
              const expectedField = (prefix, item) => item[`${prefix}_${viewport}`];
              const main = document.querySelector('main');
              const mainRect = main?.getBoundingClientRect();
              const observedSectionOrder = [...document.querySelectorAll('[data-content-id]')]
                .map(element => element.getAttribute('data-content-id'))
                .filter(Boolean);
              if (JSON.stringify(observedSectionOrder) !== JSON.stringify(contract.section_order)) {
                violations.push({code: 'RUNTIME_SECTION_ORDER', message: `Observed section order ${observedSectionOrder.join(',')} does not match the approved order ${contract.section_order.join(',')}.`});
              }
              const lengthPixels = (token, style) => {
                if (!token || token.unit === 'fr' || token.unit === '%') return Number.NaN;
                const rootSize = Number.parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
                const localSize = Number.parseFloat(style.fontSize) || rootSize;
                const factors = {px: 1, rem: rootSize, em: localSize, ch: localSize * 0.5, ex: localSize * 0.5, vw: innerWidth / 100, vh: innerHeight / 100, vmin: Math.min(innerWidth, innerHeight) / 100, vmax: Math.max(innerWidth, innerHeight) / 100};
                return Number(token.value) * Number(factors[token.unit]);
              };
              const regionRecords = [];
              for (const item of contract.region_checks) {
                const section = one(item.section_selector, 'RUNTIME_REGION_SECTION_SELECTOR', `Region ${item.region_id}`);
                const region = one(item.region_selector, 'RUNTIME_REGION_SELECTOR', `Region ${item.region_id}`);
                if (!section || !region || !mainRect) continue;
                const rect = region.getBoundingClientRect();
                const style = getComputedStyle(region);
                regionRecords.push({item, section: item.section_id, rect});
                const widthRatio = rect.width / Math.max(1, mainRect.width);
                if (widthRatio + 0.01 < item.width_ratio_min || widthRatio - 0.01 > item.width_ratio_max) {
                  violations.push({code: 'RUNTIME_REGION_WIDTH_RATIO', message: `Region ${item.region_id} width ratio ${widthRatio.toFixed(3)} is outside ${item.width_ratio_min}-${item.width_ratio_max}.`});
                }
                const expectedColumns = Number(expectedField('columns', item));
                const computedColumns = style.gridTemplateColumns && style.gridTemplateColumns !== 'none'
                  ? style.gridTemplateColumns.split(/\s+/).filter(Boolean).length
                  : 1;
                if (computedColumns !== expectedColumns) {
                  violations.push({code: 'RUNTIME_REGION_COLUMN_COUNT', message: `Region ${item.region_id} rendered ${computedColumns} columns; expected ${expectedColumns}.`});
                }
                const expectedGap = lengthPixels(item.gap, style);
                const observedGap = Number.parseFloat(style.columnGap || style.gap || style.rowGap);
                if (Number.isFinite(expectedGap) && Number.isFinite(observedGap) && Math.abs(expectedGap - observedGap) > 1.5) {
                  violations.push({code: 'RUNTIME_REGION_GAP', message: `Region ${item.region_id} gap ${observedGap}px does not match the approved ${expectedGap}px.`});
                }
                if (!item.sticky_allowed && style.position === 'sticky') {
                  violations.push({code: 'RUNTIME_REGION_STICKY_UNAUTHORIZED', message: `Region ${item.region_id} is sticky without blueprint authority.`});
                }
                const fontSize = Number.parseFloat(style.fontSize) || 16;
                const estimatedMeasure = rect.width / Math.max(1, fontSize * 0.5);
                if (estimatedMeasure > item.max_measure_ch * 1.2) {
                  violations.push({code: 'RUNTIME_REGION_MEASURE', message: `Region ${item.region_id} exceeds its readable measure.`});
                }
                checked.push({kind: 'region', id: item.region_id, widthRatio, computedColumns});
              }
              for (let left = 0; left < regionRecords.length; left += 1) {
                for (let right = left + 1; right < regionRecords.length; right += 1) {
                  const first = regionRecords[left];
                  const second = regionRecords[right];
                  if (first.section !== second.section) continue;
                  const intersection = Math.max(0, Math.min(first.rect.right, second.rect.right) - Math.max(first.rect.left, second.rect.left)) * Math.max(0, Math.min(first.rect.bottom, second.rect.bottom) - Math.max(first.rect.top, second.rect.top));
                  const smaller = Math.max(1, Math.min(first.rect.width * first.rect.height, second.rect.width * second.rect.height));
                  const overlap = intersection / smaller;
                  const allowed = Math.max(first.item.overlap_ratio_max, second.item.overlap_ratio_max);
                  if (overlap > allowed + 0.02) {
                    violations.push({code: 'RUNTIME_REGION_OVERLAP', message: `Regions ${first.item.region_id} and ${second.item.region_id} overlap by ${overlap.toFixed(3)} beyond ${allowed}.`});
                  }
                }
              }
              const relationshipRatio = (kind, source, target) => {
                const a = source.getBoundingClientRect();
                const b = target.getBoundingClientRect();
                if (kind === 'width_ratio') return a.width / Math.max(1, b.width);
                if (kind === 'horizontal_offset') return (a.left - b.left) / Math.max(1, b.width);
                if (kind === 'vertical_overlap') return Math.max(0, a.bottom - b.top) / Math.max(1, Math.min(a.height, b.height));
                if (kind === 'shared_alignment_axis') return Math.abs(a.left - b.left) / Math.max(1, innerWidth);
                if (kind === 'sticky_within_section') return getComputedStyle(source).position === 'sticky' ? 1 : 0;
                if (kind === 'isolated_spacing') return Math.max(0, a.top - b.bottom) / Math.max(1, innerHeight);
                return Number.NaN;
              };
              for (const item of contract.distinctive_move_checks) {
                if (!item.viewports.includes(viewport)) continue;
                const source = one(item.source_selector, 'RUNTIME_DISTINCTIVE_SOURCE_SELECTOR', `Move ${item.move_id}`);
                const target = one(item.target_selector, 'RUNTIME_DISTINCTIVE_TARGET_SELECTOR', `Move ${item.move_id}`);
                if (!source || !target) continue;
                const ratio = relationshipRatio(item.relationship, source, target);
                if (!Number.isFinite(ratio) || ratio + 0.01 < item.minimum_ratio || ratio - 0.01 > item.maximum_ratio) {
                  violations.push({code: 'RUNTIME_DISTINCTIVE_RELATIONSHIP', message: `Move ${item.move_id} selector relationship measured ${ratio}; expected ${item.minimum_ratio}-${item.maximum_ratio}.`});
                }
                const sourceStyle = getComputedStyle(source);
                for (const property of item.required_css_properties) {
                  const value = propertyValue(sourceStyle, property);
                  if (!value || value === 'none' || value === 'normal' || value === 'auto') {
                    violations.push({code: 'RUNTIME_DISTINCTIVE_PROPERTY', message: `Move ${item.move_id} selector lacks required ${property} evidence.`});
                  }
                }
                checked.push({kind: 'distinctive_move', id: item.move_id, ratio});
              }
              for (const item of contract.resource_checks) {
                const element = one(item.element_selector, 'RUNTIME_RESOURCE_SELECTOR', `Resource ${item.resource_slot_id}`);
                if (!element) continue;
                const image = element instanceof HTMLImageElement ? element : element.querySelector('img');
                if (!image || !image.complete || image.naturalWidth <= 0 || image.naturalHeight <= 0) {
                  violations.push({code: 'RUNTIME_RESOURCE_DECODE', message: `Resource ${item.resource_slot_id} has no decoded local image.`});
                  continue;
                }
                const ratio = image.naturalWidth / image.naturalHeight;
                if (ratio < item.aspect_ratio_min || ratio > item.aspect_ratio_max) {
                  violations.push({code: 'RUNTIME_RESOURCE_ASPECT_RATIO', message: `Resource ${item.resource_slot_id} aspect ratio ${ratio.toFixed(3)} is outside contract.`});
                }
                if (item.require_srcset && !image.getAttribute('srcset')) {
                  violations.push({code: 'RUNTIME_RESOURCE_SRCSET_MISSING', message: `Resource ${item.resource_slot_id} has no responsive srcset.`});
                }
                if (item.require_dimensions && (!Number(image.getAttribute('width')) || !Number(image.getAttribute('height')))) {
                  violations.push({code: 'RUNTIME_RESOURCE_DIMENSIONS_MISSING', message: `Resource ${item.resource_slot_id} has no intrinsic dimensions.`});
                }
                const loading = image.getAttribute('loading') || 'eager';
                if (loading !== item.loading) {
                  violations.push({code: 'RUNTIME_RESOURCE_LOADING_POLICY', message: `Resource ${item.resource_slot_id} loading policy is ${loading}, expected ${item.loading}.`});
                }
                const rect = image.getBoundingClientRect();
                const section = image.closest('[data-content-id], section')?.getBoundingClientRect();
                const intersection = section ? Math.max(0, Math.min(rect.right, section.right) - Math.max(rect.left, section.left)) * Math.max(0, Math.min(rect.bottom, section.bottom) - Math.max(rect.top, section.top)) : rect.width * rect.height;
                const visibleRatio = intersection / Math.max(1, rect.width * rect.height);
                if (visibleRatio < item.minimum_visible_ratio) {
                  violations.push({code: 'RUNTIME_RESOURCE_VISIBLE_USE', message: `Resource ${item.resource_slot_id} visible ratio ${visibleRatio.toFixed(3)} is below contract.`});
                }
                checked.push({kind: 'resource', id: item.resource_slot_id, ratio, visibleRatio});
              }
              for (const item of contract.interaction_checks) {
                const target = one(item.target_selector, 'RUNTIME_INTERACTION_SELECTOR', `Interaction ${item.interaction_id}`);
                if (!target) continue;
                if (item.expected_state_attribute && !target.hasAttribute(item.expected_state_attribute)) {
                  violations.push({code: 'RUNTIME_INTERACTION_STATE_ATTRIBUTE', message: `Interaction ${item.interaction_id} lacks ${item.expected_state_attribute}.`});
                }
                checked.push({kind: 'interaction', id: item.interaction_id});
              }
              for (const item of contract.font_checks) {
                const element = document.querySelector(item.selector);
                if (!element || !visible(element)) {
                  violations.push({code: 'RUNTIME_FONT_SELECTOR', message: `Font role ${item.role} has no visible target.`});
                  continue;
                }
                const style = getComputedStyle(element);
                const family = style.fontFamily.toLowerCase();
                if (!family.includes(item.family.toLowerCase())) {
                  violations.push({code: 'RUNTIME_FONT_FAMILY', message: `Font role ${item.role} computed family does not match ${item.family}.`});
                }
                const computedWeight = style.fontWeight === 'normal' ? 400
                  : style.fontWeight === 'bold' ? 700 : Number(style.fontWeight);
                if (!item.weights.includes(computedWeight)) {
                  violations.push({code: 'RUNTIME_FONT_WEIGHT', message: `Font role ${item.role} computed weight ${style.fontWeight} is not one of ${item.weights.join(', ')}.`});
                }
                for (const weight of item.weights) {
                  if (!document.fonts.check(`${weight} 16px "${item.family}"`)) {
                    violations.push({code: 'RUNTIME_FONT_LOAD_FAILED', message: `Font role ${item.role} weight ${weight} failed document.fonts.check.`});
                  }
                }
                checked.push({kind: 'font', id: item.role, family: style.fontFamily, weight: style.fontWeight});
              }
              return {contractHash: contract.contract_hash, checked, violations};
            }""",
                payload,
            ),
        )
        motion_results: list[dict[str, Any]] = []
        for motion in contract.motion_checks:
            target = page.locator(motion.target_selector).first
            if await target.count() != 1 or not await target.is_visible():
                result["violations"].append(
                    {
                        "code": "RUNTIME_MOTION_SELECTOR",
                        "message": f"Motion {motion.motion_id} target selector is not uniquely visible.",
                    }
                )
                continue
            if reduced_motion:
                state = await target.evaluate(
                    """element => { const style = getComputedStyle(element); return {animationName: style.animationName, animationDuration: style.animationDuration, visibility: style.visibility, opacity: style.opacity}; }"""
                )
                if state["visibility"] == "hidden" or float(state["opacity"] or 0) <= 0:
                    result["violations"].append(
                        {
                            "code": "RUNTIME_MOTION_REDUCED_CONTENT_HIDDEN",
                            "message": f"Motion {motion.motion_id} hides content under reduced motion.",
                        }
                    )
                motion_results.append({"id": motion.motion_id, "reduced": True, **state})
                continue
            properties = [item.property_name for item in motion.changed_properties]
            before = await target.evaluate(
                "(element, properties) => Object.fromEntries(properties.map(name => [name, getComputedStyle(element).getPropertyValue(name).trim()]))",
                properties,
            )
            trigger = page.locator(motion.trigger_selector).first
            if motion.trigger == "hover":
                await trigger.hover()
            elif motion.trigger == "focus":
                await trigger.focus()
            elif motion.trigger == "activate":
                await trigger.click()
            elif motion.trigger == "viewport":
                await target.scroll_into_view_if_needed()
            await page.wait_for_timeout(min(max(motion.duration_max_ms, 30), 1000))
            after = await target.evaluate(
                "(element, properties) => Object.fromEntries(properties.map(name => [name, getComputedStyle(element).getPropertyValue(name).trim()]))",
                properties,
            )
            for expectation in motion.changed_properties:
                changed = before.get(expectation.property_name) != after.get(
                    expectation.property_name
                )
                expected_after = expectation.after_value.strip()
                matches_after = not expected_after or expected_after in str(
                    after.get(expectation.property_name, "")
                )
                if not changed and motion.trigger not in {"load", "viewport"}:
                    result["violations"].append(
                        {
                            "code": "RUNTIME_MOTION_STATE_UNCHANGED",
                            "message": f"Motion {motion.motion_id} did not change {expectation.property_name} on its declared selector.",
                        }
                    )
                if not matches_after:
                    result["violations"].append(
                        {
                            "code": "RUNTIME_MOTION_STATE_MISMATCH",
                            "message": f"Motion {motion.motion_id} did not reach the declared {expectation.property_name} state.",
                        }
                    )
            motion_results.append(
                {"id": motion.motion_id, "reduced": False, "before": before, "after": after}
            )
        result["motion"] = motion_results
        return result

    async def _ensure_interaction_visible(self, page: Any, locator: Any) -> None:
        """Open a collapsed navigation container before testing its child link."""

        if await locator.is_visible():
            return
        toggle = page.locator('[data-interaction-id$=":nav-toggle"]').first
        if (
            await toggle.count()
            and await toggle.is_visible()
            and await toggle.get_attribute("aria-expanded") != "true"
        ):
            await toggle.click()
        await locator.wait_for(state="visible")

    @staticmethod
    def _application_path(current_url: str, base_url: str) -> str:
        """Translate a nested preview URL back to the portfolio's route path."""

        observed = urlsplit(current_url).path or "/"
        base_path = urlsplit(base_url).path or "/"
        normalized_base = "/" + base_path.strip("/") + "/" if base_path.strip("/") else "/"
        if normalized_base != "/" and observed.startswith(normalized_base):
            suffix = observed[len(normalized_base) :]
            return "/" + suffix.lstrip("/") if suffix else "/"
        return observed

    async def _assert_content(self, page: Any, step: Any, content_ids: list[str]) -> None:
        for content_id in step.expected_content_ids:
            locator = page.locator(f'[data-content-id="{content_id}"]')
            await locator.wait_for(state="attached")
            content_ids.append(content_id)
        # SPAs render after network idle; wait until something is painted
        # before reading text so the unknown-route check cannot race React.
        await page.wait_for_function(
            "() => !!document.body && document.body.innerText.trim().length > 0"
        )
        body_text = " ".join((await page.locator("body").inner_text()).split()).casefold()
        for expected in step.expected_text:
            normalized_expected = " ".join(expected.split()).casefold()
            if normalized_expected not in body_text:
                raise AssertionError(f"Expected public content is missing: {expected}")
