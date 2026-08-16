"""Text/DOM/runtime verification without visual or image evidence."""

from __future__ import annotations

import hashlib
from typing import Any
from urllib.parse import urljoin, urlsplit

from oryxenai.agents.code_generator.core.development_schemas import (
    Diagnostic,
    RuntimeEvidence,
    VerificationJourney,
    VerificationPlan,
    VerificationProfile,
)


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
            if profile.browser_executable:
                launch_kwargs["executable_path"] = profile.browser_executable
            try:
                browser = await browser_type.launch(**launch_kwargs)
            except Exception as exc:
                return [], [_diagnostic("BROWSER_START_FAILED", str(exc), owner="infrastructure")]
            try:
                for journey in plan.runtime_journeys:
                    journey_evidence, journey_diagnostics = await self._run_journey(
                        browser,
                        base_url,
                        origin.netloc,
                        journey,
                        profile,
                        timeout_ms,
                        verification_token,
                    )
                    evidence.append(journey_evidence)
                    diagnostics.extend(journey_diagnostics)
            finally:
                await browser.close()
        return evidence, diagnostics

    async def _run_journey(
        self,
        browser: Any,
        base_url: str,
        expected_netloc: str,
        journey: VerificationJourney,
        profile: VerificationProfile,
        timeout_ms: int,
        verification_token: str,
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
                requests.append(
                    {
                        "url": str(response.url),
                        "status": status,
                        "failed": True,
                    }
                )

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
            await route.continue_()

        await context.route("**/*", protect_request)
        passed = True
        title = ""
        final_url = ""
        content_ids: list[str] = []
        focus_results: list[dict[str, str | bool]] = []
        overflow_results: list[dict[str, str | int | bool]] = []
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
        outbound = [item for item in requests if bool(item.get("outbound"))]
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
            item for item in requests if bool(item.get("failed")) and not bool(item.get("outbound"))
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
                passed=passed,
            ),
            diagnostics,
        )

    async def _step(
        self,
        page: Any,
        base_url: str,
        step: Any,
        journey: VerificationJourney,
        content_ids: list[str],
        focus_results: list[dict[str, str | bool]],
        overflow_results: list[dict[str, str | int | bool]],
    ) -> None:
        if step.action == "load":
            target = urljoin(
                base_url.rstrip("/") + "/", step.expected_url or journey.start_path.lstrip("/")
            )
            await page.goto(target, wait_until="networkidle")
            if step.expected_url and urlsplit(page.url).path != step.expected_url:
                raise AssertionError(f"Expected URL path {step.expected_url}, observed {page.url}")
            await self._assert_content(page, step, content_ids)
        elif step.action == "navigate":
            await page.locator(step.target).first.click()
            await page.wait_for_load_state("networkidle")
            if step.expected_url and urlsplit(page.url).path != step.expected_url:
                raise AssertionError(
                    f"Expected navigation to {step.expected_url}, observed {page.url}"
                )
        elif step.action == "back":
            await page.go_back(wait_until="networkidle")
        elif step.action == "forward":
            await page.go_forward(wait_until="networkidle")
        elif step.action in {"click", "focus", "press"}:
            locator = page.locator(step.target).first
            if step.action == "click":
                await locator.click()
            elif step.action == "focus":
                await locator.focus()
            else:
                await locator.press("Enter")
            if step.expected_url and urlsplit(page.url).path != step.expected_url:
                raise AssertionError(
                    f"Expected interaction URL {step.expected_url}, observed {page.url}"
                )
            if step.expected_accessible_name:
                observed = (
                    await locator.get_attribute("aria-label")
                    or (await locator.inner_text()).strip()
                )
                if observed != step.expected_accessible_name:
                    raise AssertionError(
                        f"Expected accessible name {step.expected_accessible_name}, observed {observed}"
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

    async def _assert_content(self, page: Any, step: Any, content_ids: list[str]) -> None:
        for content_id in step.expected_content_ids:
            locator = page.locator(f'[data-content-id="{content_id}"]')
            await locator.wait_for(state="attached")
            content_ids.append(content_id)
        body_text = await page.locator("body").inner_text()
        for expected in step.expected_text:
            if expected not in body_text:
                raise AssertionError(f"Expected public content is missing: {expected}")
