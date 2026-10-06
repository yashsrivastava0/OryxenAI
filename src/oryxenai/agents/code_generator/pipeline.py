"""The page build: produce the body, validate, seal. One straight line.

The worker handler and the CLI both call :func:`build_page`, so what you debug
locally is exactly what runs in production. The body comes from the theme's
own renderer when it has one, otherwise from one model call. There is no retry, no
repair call and no fallback renderer: a stage either succeeds or raises
:class:`CodeGeneratorFailure` carrying the exact what / where / why envelope.
The caller owns ``trace`` so a failure still leaves the evidence collected so far.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from oryxenai.agents.code_generator.agent import CodeGeneratorAgent
from oryxenai.agents.code_generator.bundle import SiteBundle, build_bundle
from oryxenai.agents.code_generator.diagnostics import (
    failure_from_provider_error,
    failure_from_validation,
    failure_from_verification,
)
from oryxenai.agents.code_generator.schemas import CodeGeneratorFailure
from oryxenai.agents.code_generator.validate import validate_page
from oryxenai.agents.shared.contracts import AgentContext
from oryxenai.agents.shared.providers.errors import ProviderError
from oryxenai.themes import ThemePackage
from oryxenai.themes.contract import HostRenderedContract
from oryxenai.themes.issues import Issue
from oryxenai.themes.lang import detect_language

StageCallback = Callable[[str], Awaitable[None]]

_RECEIPT_VERSION = "SiteReceipt/v1"
_ISSUES_IN_RECEIPT = 20


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """What a real-browser verification run found."""

    status: Literal["passed", "failed", "skipped", "unavailable"]
    issues: list[Issue]
    details: dict[str, Any]


class PageVerifier(Protocol):
    async def verify(self, bundle: SiteBundle, theme: ThemePackage) -> VerificationResult: ...


@dataclass(slots=True)
class BuildOutcome:
    bundle: SiteBundle
    receipt: dict[str, Any]


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)


async def _announce(callback: StageCallback | None, stage: str) -> None:
    if callback is not None:
        await callback(stage)


async def build_page(
    *,
    page_content: Mapping[str, Any],
    agent: CodeGeneratorAgent,
    context: AgentContext,
    theme: ThemePackage,
    max_body_bytes: int,
    trace: dict[str, Any],
    reference: str = "",
    on_stage: StageCallback | None = None,
    verifier: PageVerifier | None = None,
) -> BuildOutcome:
    """Run one build. Raises :class:`CodeGeneratorFailure`; fills ``trace`` as it goes."""
    timings: dict[str, float] = trace.setdefault("timings_ms", {})
    trace.setdefault("calls", [])
    derived = theme.contract.derive(page_content)

    # 1. produce the body: the theme's own renderer when it has one (a pure function of the
    #    approved content, so no model call and no copying risk), otherwise the model
    contract = theme.contract
    await _announce(on_stage, "generating")
    started = time.perf_counter()
    if isinstance(contract, HostRenderedContract):
        body_html = contract.render_body(page_content, derived)
        lang = detect_language(page_content, contract.default_language)
        trace["calls"].append({"operation": "host_render", "theme_id": theme.theme_id})
        engine = "host_template"
    else:
        try:
            page = await agent.generate_page(page_content, derived, context)
        except CodeGeneratorFailure:
            timings["generate"] = _ms(started)
            raise
        except ProviderError as exc:
            timings["generate"] = _ms(started)
            raise CodeGeneratorFailure(
                failure_from_provider_error(exc, stage="generate", reference=reference)
            ) from exc
        body_html, lang = page.body_html, page.lang
        trace["calls"].append(page.call.to_dict())
        engine = "model"
    timings["generate"] = _ms(started)
    trace["engine"] = engine
    trace["body_bytes"] = len(body_html.encode("utf-8"))

    # 2. validate: strict, never auto-fixed
    await _announce(on_stage, "validating")
    started = time.perf_counter()
    report = await asyncio.to_thread(
        validate_page,
        body_html,
        page_content,
        theme,
        derived=derived,
        max_bytes=max_body_bytes,
    )
    timings["validate"] = _ms(started)
    trace["validation"] = report.to_dict()
    if not report.ok:
        # Keep the rejected markup for debugging; it is never served.
        trace["rejected_body_html"] = body_html
        raise CodeGeneratorFailure(
            failure_from_validation(report, reference=reference, engine=engine)
        )

    # 3. seal: host head + model body + the theme's unchanged files
    started = time.perf_counter()
    bundle = build_bundle(page_content, derived, body_html, lang, theme)
    timings["bundle"] = _ms(started)

    # 4. browser verification (best effort; any defect it finds still blocks)
    browser: dict[str, Any] = {"status": "not_run"}
    if verifier is not None:
        await _announce(on_stage, "verifying")
        started = time.perf_counter()
        result = await verifier.verify(bundle, theme)
        timings["verify"] = _ms(started)
        browser = {"status": result.status, **result.details}
        trace["verification"] = {
            "status": result.status,
            "issues": [issue.to_dict() for issue in result.issues[:_ISSUES_IN_RECEIPT]],
        }
        if result.status == "failed":
            raise CodeGeneratorFailure(
                failure_from_verification(result.issues, reference=reference)
            )

    receipt: dict[str, Any] = {
        "contract_version": _RECEIPT_VERSION,
        "theme_id": bundle.theme_id,
        "theme_sha256": bundle.css_sha256,
        "index_sha256": bundle.index_sha256,
        "index_bytes": len(bundle.index_html.encode("utf-8")),
        "lang": bundle.lang,
        "validation": {
            "ok": True,
            "warning_count": len(report.warnings),
            "warnings": [issue.to_dict() for issue in report.warnings[:_ISSUES_IN_RECEIPT]],
        },
        "browser": browser,
        "engine": engine,
        "model": trace["calls"][-1] if trace["calls"] else {},
    }
    return BuildOutcome(bundle=bundle, receipt=receipt)
