"""Fix D: DOM/runtime verification must optionally capture advisory
screenshots -- zero extra navigation, zero model calls, purely for visual
review. This is intentionally decoupled from the full Code Generator
plan/admission pipeline (no SitePlan, no fixture pack): it drives
RuntimeVerifier.verify() directly against a tiny local static site, the
same way the pipeline's own verification stage does, minus everything
unrelated to screenshot capture."""

from __future__ import annotations

import http.server
import threading
from pathlib import Path

import pytest

from oryxenai.agents.code_generator.core.development_schemas import (
    VerificationJourney,
    VerificationPlan,
    VerificationProfile,
    VerificationStep,
)
from oryxenai.agents.code_generator.core.runtime_verifier import RuntimeVerifier, _safe_filename


@pytest.fixture
def static_site_url(tmp_path: Path):
    site_root = tmp_path / "site"
    site_root.mkdir()
    (site_root / "index.html").write_text(
        "<!doctype html><html><body>"
        '<main data-route-id="home"><h1>Hello</h1><p>A minimal static page.</p></main>'
        "</body></html>",
        encoding="utf-8",
    )

    handler = http.server.SimpleHTTPRequestHandler
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    original_cwd = Path.cwd()

    import os

    os.chdir(site_root)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        os.chdir(original_cwd)


def _minimal_plan() -> VerificationPlan:
    journey = VerificationJourney(
        journey_id="direct:home",
        route_id="home",
        start_path="/",
        viewport_profile="desktop",
        steps=[VerificationStep(step_id="load", action="load")],
    )
    return VerificationPlan(
        based_on_candidate_identity="test-identity",
        runtime_journeys=[journey],
        expected_route_paths=["/"],
    )


def _minimal_profile() -> VerificationProfile:
    return VerificationProfile(
        profile_id="test-profile",
        viewport_profiles={"desktop": {"width": 1280, "height": 800}},
    )


async def test_verify_captures_a_screenshot_when_screenshot_dir_is_given(
    static_site_url, tmp_path: Path
) -> None:
    screenshot_dir = tmp_path / "shots"
    evidence, diagnostics = await RuntimeVerifier().verify(
        static_site_url,
        plan=_minimal_plan(),
        profile=_minimal_profile(),
        screenshot_dir=screenshot_dir,
    )

    assert not any(d.code == "RUNTIME_ASSERTION_FAILED" for d in diagnostics), diagnostics
    assert len(evidence) == 1
    expected_name = f"{_safe_filename('direct:home')}.png"
    assert evidence[0].screenshot_relative_path == expected_name
    screenshot_path = screenshot_dir / expected_name
    assert screenshot_path.is_file()
    assert screenshot_path.stat().st_size > 0


async def test_verify_omits_screenshot_when_no_screenshot_dir_is_given(
    static_site_url,
) -> None:
    evidence, _diagnostics = await RuntimeVerifier().verify(
        static_site_url,
        plan=_minimal_plan(),
        profile=_minimal_profile(),
    )

    assert len(evidence) == 1
    assert evidence[0].screenshot_relative_path == ""


def test_safe_filename_collapses_journey_id_separators() -> None:
    assert _safe_filename("direct:home") == "direct_home"
    assert _safe_filename("interaction:hero-cta") == "interaction_hero-cta"
    assert _safe_filename("") == "journey"


async def test_verify_deduplicates_identical_diagnostics_across_viewports(
    static_site_url,
) -> None:
    """Regression test for the 2026-09-05 live-discovered pattern: the same
    real defect was caught by more than one viewport's journey and reported
    as 6 identically-fingerprinted diagnostics inside one already-large
    bundle, adding no new information for a repair attempt. Two journeys
    sharing the same journey_id/route_id (the fingerprint's own key,
    alongside code/message) that both hit the same missing-content
    assertion must collapse to exactly one diagnostic."""
    step = VerificationStep(
        step_id="load",
        action="assert_content",
        expected_text=["text that will never appear on this page"],
    )
    plan = VerificationPlan(
        based_on_candidate_identity="test-identity",
        runtime_journeys=[
            VerificationJourney(
                journey_id="direct:home",
                route_id="home",
                start_path="/",
                viewport_profile="desktop",
                steps=[step],
            ),
            VerificationJourney(
                journey_id="direct:home",
                route_id="home",
                start_path="/",
                viewport_profile="tablet",
                steps=[step],
            ),
        ],
        expected_route_paths=["/"],
    )
    profile = VerificationProfile(
        profile_id="test-profile",
        viewport_profiles={
            "desktop": {"width": 1280, "height": 800},
            "tablet": {"width": 768, "height": 1024},
        },
    )

    _evidence, diagnostics = await RuntimeVerifier().verify(
        static_site_url,
        plan=plan,
        profile=profile,
    )

    assertion_failures = [d for d in diagnostics if d.code == "RUNTIME_ASSERTION_FAILED"]
    assert len(assertion_failures) == 1, diagnostics
