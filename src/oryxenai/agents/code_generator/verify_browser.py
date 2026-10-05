"""Real-browser verification of a sealed page bundle.

The page is opened in headless Chromium at several screen widths. Every request
the browser makes is answered in process by the *production* preview router
(same grant check, headers, MIME types and CSP as a real preview), so what is
verified is exactly what a visitor's browser would get. Nothing listens on a
port and nothing reaches the network: any request to another host is blocked and
reported.

Policy (``[code_generator.verification] browser``):

* ``off``          no browser is ever started (the factory returns ``None``).
* ``best_effort``  verify when a browser can start. If it cannot, the receipt says
                   so and the page is still published; a defect it *does* find
                   always blocks.
* ``required``     a page is never published without a passing browser run.
"""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from fastapi import FastAPI

from oryxenai.agents.code_generator.bundle import SiteBundle
from oryxenai.agents.code_generator.grants import PreviewGrantSigner
from oryxenai.agents.code_generator.pipeline import PageVerifier, VerificationResult
from oryxenai.agents.code_generator.serving import (
    PREVIEW_PREFIX,
    ServedBundle,
    StaticBundleProvider,
    create_preview_router,
)
from oryxenai.core.logging import get_logger
from oryxenai.core.settings import CodeGeneratorVerificationConfig
from oryxenai.themes import ThemePackage
from oryxenai.themes.issues import Issue, bounded

logger = get_logger("oryxenai.code_generator.verify")

_ORIGIN = "http://preview.verify.test"
_MAX_FINDINGS_PER_KIND = 5

_METRICS_SCRIPT = """
async () => {
  await document.fonts.ready;
  const faces = Array.from(document.fonts).map((face) => ({
    family: face.family, weight: face.weight, status: face.status,
  }));
  const images = Array.from(document.images).map((image) => ({
    src: image.currentSrc || image.src, ok: image.complete && image.naturalWidth > 0,
  }));
  return {
    faces,
    images,
    overflow: document.documentElement.scrollWidth - window.innerWidth,
    background: getComputedStyle(document.body).backgroundColor,
    headings: document.querySelectorAll('h1').length,
  };
}
"""

# The browser renders model-written markup: give it only what it needs to start,
# never the application's secrets.
_BROWSER_ENV_KEYS = (
    "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL", "DISPLAY",
    "LD_LIBRARY_PATH", "FONTCONFIG_PATH", "FONTCONFIG_FILE", "XDG_RUNTIME_DIR", "LOCALAPPDATA",
    "PROGRAMFILES", "PROGRAMDATA",
)  # fmt: skip

_gates: dict[int, asyncio.Semaphore] = {}


def _gate(limit: int) -> asyncio.Semaphore:
    """One browser at a time per process by default (they are heavy on small hosts)."""
    loop_id = id(asyncio.get_running_loop())
    if loop_id not in _gates:
        _gates.clear()
        _gates[loop_id] = asyncio.Semaphore(max(1, limit))
    return _gates[loop_id]


def _font_load_failed(face: dict[str, str], faces: list[dict[str, str]]) -> bool:
    if face["status"] != "error":
        return False
    family = face["family"]
    if family.endswith(" Fallback"):
        primary = family.removesuffix(" Fallback")
        # A metric-matched local fallback may be absent on CI/Linux. The
        # bundled primary face already loaded, so this is not a broken page.
        if any(item["family"] == primary and item["status"] == "loaded" for item in faces):
            return False
    return True


@dataclass(slots=True)
class _Findings:
    issues: list[Issue] = field(default_factory=list)
    seen: set[tuple[str, str]] = field(default_factory=set)

    def add(self, issue: Issue) -> None:
        key = (issue.code, issue.found or issue.message)
        if key in self.seen:
            return
        self.seen.add(key)
        self.issues.append(issue)


def _short_path(url: str) -> str:
    parsed = urlparse(url)
    path = re.sub(rf"^{re.escape(PREVIEW_PREFIX)}/[^/]+", "", parsed.path)
    return (path or "/") + (f"?{parsed.query}" if parsed.query else "")


def _reason(exc: BaseException) -> str:
    text = " ".join(str(exc).split())
    return f"{type(exc).__name__}: {text[:160]}"


class BrowserVerifier:
    """Verifies a bundle in Chromium; see the module docstring for the policy."""

    def __init__(self, config: CodeGeneratorVerificationConfig) -> None:
        self._config = config

    # ── public API (PageVerifier) ────────────────────────────────────────────

    async def verify(self, bundle: SiteBundle, theme: ThemePackage) -> VerificationResult:
        started = time.perf_counter()
        required = self._config.browser == "required"
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            return self._unavailable(
                required, f"Playwright is not installed ({type(exc).__name__})."
            )
        budget = self._config.page_timeout_seconds * (len(self._config.viewports) + 2)
        try:
            async with _gate(self._config.concurrency):
                async with asyncio.timeout(budget):
                    result = await self._run(async_playwright, bundle, theme)
        except TimeoutError:
            return self._unavailable(required, f"The browser did not finish within {budget:.0f}s.")
        except Exception as exc:
            logger.warning("browser verification could not run: %s", type(exc).__name__)
            return self._unavailable(required, _reason(exc))
        result.details["duration_ms"] = round((time.perf_counter() - started) * 1000, 1)
        return result

    # ── internals ────────────────────────────────────────────────────────────

    @staticmethod
    def _unavailable(required: bool, reason: str) -> VerificationResult:
        if required:
            issue = Issue(
                "BROWSER_UNAVAILABLE",
                "error",
                "Browser verification is required but no browser could be started.",
                found=reason,
            )
            return VerificationResult("failed", [issue], {"reason": reason})
        return VerificationResult("unavailable", [], {"reason": reason})

    def _launch_options(self, home: str) -> dict[str, Any]:
        options: dict[str, Any] = {
            "headless": True,
            "env": {
                **{key: os.environ[key] for key in _BROWSER_ENV_KEYS if key in os.environ},
                "HOME": home,
                "XDG_CONFIG_HOME": home,
                "XDG_CACHE_HOME": home,
            },
        }
        if self._config.browser_executable:
            options["executable_path"] = self._config.browser_executable
        elif self._config.browser_channel:
            options["channel"] = self._config.browser_channel
        # Containers usually run as root, where Chromium refuses to start its sandbox.
        if getattr(os, "geteuid", lambda: 1)() == 0:
            options["args"] = ["--no-sandbox"]
        return options

    async def _run(
        self, async_playwright: Any, bundle: SiteBundle, theme: ThemePackage
    ) -> VerificationResult:
        session_id, version_id = uuid4(), uuid4()
        signer = PreviewGrantSigner.random()
        app = FastAPI()
        app.state.preview_signer = signer
        app.state.preview_provider = StaticBundleProvider(
            {
                (session_id, version_id): ServedBundle(
                    bundle.index_html,
                    theme.theme_id,
                    theme.css_sha256,
                    bundle.index_sha256,
                    bundle.manifest,
                )
            }
        )
        app.include_router(create_preview_router())
        token, _ = signer.mint(session_id, version_id, int(self._config.page_timeout_seconds * 10))
        entry = f"{PREVIEW_PREFIX}/{token}/index.html"

        findings = _Findings()
        pages: list[dict[str, Any]] = []
        with tempfile.TemporaryDirectory(prefix="oryxenai-verify-") as home:
            async with async_playwright() as playwright:
                try:
                    browser = await playwright.chromium.launch(**self._launch_options(home))
                except Exception as exc:
                    return self._unavailable(self._config.browser == "required", _reason(exc))
                try:
                    transport = httpx.ASGITransport(app=app)
                    async with httpx.AsyncClient(transport=transport, base_url=_ORIGIN) as client:
                        for width in self._config.viewports:
                            pages.append(
                                await self._check_viewport(
                                    browser, client, entry, width, findings, theme
                                )
                            )
                    version = browser.version
                finally:
                    await browser.close()
        errors = [issue for issue in findings.issues if issue.is_error]
        details = {
            "engine": "chromium",
            "version": version,
            "viewports": list(self._config.viewports),
            "pages": pages,
            "error_count": len(errors),
            "warning_count": len(findings.issues) - len(errors),
        }
        return VerificationResult("failed" if errors else "passed", findings.issues, details)

    async def _check_viewport(
        self,
        browser: Any,
        client: httpx.AsyncClient,
        entry: str,
        width: int,
        findings: _Findings,
        theme: ThemePackage,
    ) -> dict[str, Any]:
        origin = f"viewport:{width}"
        context = await browser.new_context(
            viewport={"width": width, "height": 900}, device_scale_factor=1
        )
        page = await context.new_page()
        requests = 0
        console: list[str] = []
        failures: list[tuple[str, str]] = []
        external: list[str] = []

        async def handle(route: Any) -> None:
            nonlocal requests
            url = route.request.url
            if not url.startswith(_ORIGIN):
                external.append(url)
                await route.abort("blockedbyclient")
                return
            requests += 1
            response = await client.get(url.removeprefix(_ORIGIN))
            headers = {
                k: v
                for k, v in response.headers.items()
                if k.lower() not in {"content-length", "content-encoding"}
            }
            if response.status_code >= 400:
                failures.append((url, f"HTTP {response.status_code}"))
            await route.fulfill(status=response.status_code, headers=headers, body=response.content)

        await context.route("**/*", handle)
        page.on(
            "console",
            lambda message: console.append(message.text) if message.type == "error" else None,
        )
        page.on("pageerror", lambda error: console.append(f"page error: {error}"))
        page.on(
            "requestfailed",
            lambda request: failures.append((request.url, request.failure or "request failed")),
        )

        loaded = time.perf_counter()
        try:
            await page.goto(
                f"{_ORIGIN}{entry}",
                wait_until="load",
                timeout=self._config.page_timeout_seconds * 1000,
            )
            metrics = await page.evaluate(_METRICS_SCRIPT)
        except Exception as exc:
            findings.add(
                Issue(
                    "PAGE_LOAD_FAILED",
                    "error",
                    f"The page did not finish loading at {width}px.",
                    found=_reason(exc),
                    origin=origin,
                )
            )
            await context.close()
            return {"viewport": width, "loaded": False}
        load_ms = round((time.perf_counter() - loaded) * 1000, 1)
        if theme.allows_scripts:
            try:
                await page.wait_for_function(
                    "window.AtlasTheme && document.body.dataset.router === 'ready'",
                    timeout=self._config.page_timeout_seconds * 1000,
                )
                await page.evaluate("() => window.AtlasTheme.go('about')")
                await page.wait_for_function("!document.getElementById('about').hidden")
                await page.go_back()
                await page.wait_for_function("!document.getElementById('home').hidden")
                if await page.locator("#case-1").count():
                    await page.evaluate("() => window.AtlasTheme.go('case-1')")
                    await page.wait_for_function("!document.getElementById('case-1').hidden")
            except Exception as exc:
                findings.add(
                    Issue(
                        "SCRIPT_BEHAVIOR",
                        "error",
                        "The theme script did not complete routing.",
                        found=_reason(exc),
                        origin=origin,
                    )
                )
        await context.close()

        for url in external[:_MAX_FINDINGS_PER_KIND]:
            findings.add(
                Issue(
                    "EXTERNAL_REQUEST",
                    "error",
                    "The page requested a resource from another host.",
                    found=url,
                    origin=f"request:{url}",
                )
            )
        for url, why in failures[:_MAX_FINDINGS_PER_KIND]:
            if url.startswith(_ORIGIN):
                findings.add(
                    Issue(
                        "REQUEST_FAILED",
                        "error",
                        f"A page resource did not load ({why}).",
                        found=f"{_short_path(url)}: {why}",
                        origin=f"request:{_short_path(url)}",
                    )
                )
        for text in console[:_MAX_FINDINGS_PER_KIND]:
            policy = "Content Security Policy" in text or text.startswith("Refused to")
            findings.add(
                Issue(
                    "CSP_VIOLATION" if policy else "CONSOLE_ERROR",
                    "error",
                    "The page tried to load something its security policy forbids."
                    if policy
                    else "The browser logged an error while loading the page.",
                    found=bounded(text),
                    origin=origin,
                )
            )
        for face in metrics["faces"]:
            if _font_load_failed(face, metrics["faces"]):
                findings.add(
                    Issue(
                        "FONT_FAILED",
                        "error",
                        "A font used by the page could not be loaded.",
                        found=f"{face['family']} {face['weight']}",
                        origin=origin,
                    )
                )
        for image in metrics["images"]:
            if not image["ok"]:
                findings.add(
                    Issue(
                        "IMAGE_BROKEN",
                        "error",
                        "An image on the page did not load or decode.",
                        found=_short_path(image["src"])
                        if image["src"].startswith(_ORIGIN)
                        else image["src"][:200],
                        origin=origin,
                    )
                )
        if metrics["background"] in {"rgba(0, 0, 0, 0)", "transparent"}:
            findings.add(
                Issue(
                    "STYLESHEET_NOT_APPLIED",
                    "error",
                    "The theme stylesheet did not style the page (the body has no background).",
                    found=metrics["background"],
                    origin=origin,
                )
            )
        if metrics["overflow"] > 1:
            findings.add(
                Issue(
                    "HORIZONTAL_OVERFLOW",
                    "warning",
                    f"The page is {metrics['overflow']}px wider than a {width}px screen.",
                    found=f"{metrics['overflow']}px",
                    origin=origin,
                )
            )
        return {
            "viewport": width,
            "loaded": True,
            "load_ms": load_ms,
            "requests": requests,
            "console_errors": len(console),
            "fonts": sorted({f"{f['family']}:{f['status']}" for f in metrics["faces"]}),
            "images": len(metrics["images"]),
            "overflow_px": max(0, int(metrics["overflow"])),
        }


def build_verifier(config: CodeGeneratorVerificationConfig) -> PageVerifier | None:
    """The verifier for the configured policy, or ``None`` when it is off."""
    if config.browser == "off":
        return None
    return BrowserVerifier(config)
