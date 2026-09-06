"""Regression test for the motion transform-matrix comparison fix.

getComputedStyle always reports a "transform" property as a resolved
matrix()/matrix3d() string, never in the author's own function notation
(translateY(24px), scale(1.05), ...) that a motion beat's `after_value` is
written in. Before this fix, `_assert_design_realization`'s check was a
plain substring test against the matrix string, which a correct, working
animation could never satisfy. This drives a real browser through
RuntimeVerifier the same way tests/unit/agents/code_generator/
test_runtime_verifier_screenshots.py does, minus everything unrelated to
the motion check.
"""

from __future__ import annotations

import http.server
import threading
from pathlib import Path

import pytest

from oryxenai.agents.code_generator.core.development_schemas import (
    DesignRealizationContract,
    DistinctiveMoveRuntimeCheckV1,
    FontRuntimeCheckV1,
    MotionPropertyExpectationV4,
    MotionRuntimeCheckV1,
    RegionRuntimeCheckV1,
    VerificationJourney,
    VerificationPlan,
    VerificationProfile,
    VerificationStep,
)
from oryxenai.agents.code_generator.core.runtime_verifier import RuntimeVerifier


@pytest.fixture
def static_site_url(tmp_path: Path):
    site_root = tmp_path / "site"
    site_root.mkdir()
    (site_root / "index.html").write_text(
        "<!doctype html><html><body>"
        '<main data-route-id="home">'
        '<section id="hero" data-content-id="hero">'
        '<div id="region" style="width:300px;">'
        '<h1 id="heading" style="font-family: Georgia, serif; font-weight: 400;">Hello</h1>'
        "</div></section></main>"
        "<script>"
        "document.getElementById('heading').addEventListener('click', () => {"
        "  document.getElementById('heading').style.transform = 'translateY(24px)';"
        "});"
        "</script>"
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


def _realization_contract(after_value: str) -> DesignRealizationContract:
    return DesignRealizationContract(
        route_id="home",
        section_order=["hero"],
        region_checks=[
            RegionRuntimeCheckV1(
                region_id="region-1",
                section_id="hero",
                section_selector="#hero",
                region_selector="#region",
                order_mobile=0,
                order_tablet=0,
                order_desktop=0,
                columns_mobile=1,
                columns_tablet=1,
                columns_desktop=1,
                max_measure_ch=1000,
                width_ratio_min=0.0,
                width_ratio_max=1.0,
                overlap_ratio_max=1.0,
                sticky_allowed=True,
            )
        ],
        distinctive_move_checks=[
            DistinctiveMoveRuntimeCheckV1(
                move_id="move-1",
                section_id="hero",
                source_selector="#heading",
                target_selector="#heading",
                relationship="width_ratio",
                minimum_ratio=0.0,
                maximum_ratio=10.0,
                viewports=["desktop"],
                required_css_properties=[],
            )
        ],
        font_checks=[
            FontRuntimeCheckV1(
                role="display",
                selector="#heading",
                family="Georgia",
                weights=[400],
                local_files=["dummy.woff2"],
            )
        ],
        motion_checks=[
            MotionRuntimeCheckV1(
                motion_id="reveal-1",
                target_selector="#heading",
                trigger_selector="#heading",
                trigger="activate",
                changed_properties=[
                    MotionPropertyExpectationV4(
                        property_name="transform",
                        before_value="none",
                        after_value=after_value,
                    )
                ],
                duration_min_ms=1,
                duration_max_ms=50,
                performance_budget_ms=200,
                reduced_motion_replacement="opacity",
            )
        ],
    )


def _plan(contract: DesignRealizationContract) -> VerificationPlan:
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
        realization_contracts=[contract],
        expected_route_paths=["/"],
    )


def _profile() -> VerificationProfile:
    return VerificationProfile(
        profile_id="test-profile",
        viewport_profiles={"desktop": {"width": 1280, "height": 800}},
    )


async def test_author_style_transform_matches_the_equivalent_computed_matrix(
    static_site_url,
) -> None:
    """The real, previously-failing case: a motion beat authored the way a
    real generation prompt writes it ("translateY(24px)"), which resolves
    to the same matrix the click handler actually applies."""

    _evidence, diagnostics = await RuntimeVerifier().verify(
        static_site_url,
        plan=_plan(_realization_contract("translateY(24px)")),
        profile=_profile(),
    )

    assert not any(d.code == "RUNTIME_MOTION_STATE_MISMATCH" for d in diagnostics), diagnostics
    assert not any(d.code == "RUNTIME_MOTION_STATE_UNCHANGED" for d in diagnostics), diagnostics


async def test_a_genuinely_wrong_transform_still_fails(static_site_url) -> None:
    """The fix must not become a rubber stamp: a motion beat that expects a
    transform the page never actually applies must still be caught."""

    _evidence, diagnostics = await RuntimeVerifier().verify(
        static_site_url,
        plan=_plan(_realization_contract("translateY(9999px)")),
        profile=_profile(),
    )

    assert any(d.code == "RUNTIME_MOTION_STATE_MISMATCH" for d in diagnostics), diagnostics
