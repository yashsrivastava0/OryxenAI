"""Regression tests for two runtime-verifier fixes found live in the same
session: the region column-count check treating an abstract "columns_*"
design-grid span as a literal CSS grid-template-columns track-count
requirement (penalizing a legitimate, well-considered asymmetric split),
and the distinctive-move CSS-property check having no way to look at a
nested element carrying the move's own runtime_marker, only at
source_selector itself.
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
    RegionRuntimeCheckV1,
    VerificationJourney,
    VerificationPlan,
    VerificationProfile,
    VerificationStep,
)
from oryxenai.agents.code_generator.core.runtime_verifier import RuntimeVerifier


def _serve(tmp_path: Path, html: str):
    site_root = tmp_path / "site"
    site_root.mkdir()
    (site_root / "index.html").write_text(html, encoding="utf-8")
    handler = http.server.SimpleHTTPRequestHandler
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    return server, site_root


@pytest.fixture
def region_site_url(tmp_path: Path):
    """A region using a considered 2-track asymmetric grid, contracted
    against an abstract columns_desktop=8 design-grid span."""

    server, site_root = _serve(
        tmp_path,
        "<!doctype html><html><body>"
        '<main data-route-id="home">'
        '<section id="hero" data-content-id="hero">'
        '<div id="region" style="display:grid; grid-template-columns: 1.1fr 0.9fr; width:600px;">'
        "<div>A</div><div>B</div>"
        "</div></section></main></body></html>",
    )
    import os

    original_cwd = Path.cwd()
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


@pytest.fixture
def collapsed_region_site_url(tmp_path: Path):
    """A region contracted for multiple columns that actually collapsed to
    a single one -- the real defect this check must still catch."""

    server, site_root = _serve(
        tmp_path,
        "<!doctype html><html><body>"
        '<main data-route-id="home">'
        '<section id="hero" data-content-id="hero">'
        '<div id="region" style="width:600px;">'
        "<div>A</div><div>B</div>"
        "</div></section></main></body></html>",
    )
    import os

    original_cwd = Path.cwd()
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


@pytest.fixture
def padded_region_site_url(tmp_path: Path):
    """A region with no explicit width (auto, block-level, filling its
    containing block) but real inline padding creating visual inset -- the
    extremely common "full-bleed section, inset via padding" pattern.
    getBoundingClientRect() always reports the border box, so before the
    fix this always measured a 1.000 width ratio no matter how much
    padding-based inset the design actually had."""

    server, site_root = _serve(
        tmp_path,
        "<!doctype html><html><body style='margin:0;'>"
        '<main data-route-id="home" style="margin:0; width:1000px; font-size:16px;">'
        '<section id="hero" data-content-id="hero">'
        '<div id="region" style="padding-inline:100px; box-sizing:border-box;">'
        "<div>content</div>"
        "</div></section></main></body></html>",
    )
    import os

    original_cwd = Path.cwd()
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


@pytest.fixture
def marker_scoped_site_url(tmp_path: Path):
    """A distinctive move whose required CSS properties live on a nested
    marker-carrying element, not on source_selector's own outer wrapper --
    the real shape a well-organized implementation produces."""

    server, site_root = _serve(
        tmp_path,
        "<!doctype html><html><body>"
        '<main data-route-id="home">'
        '<section id="hero" data-content-id="hero">'
        '<div id="outer" style="width:300px;">'
        '<div data-distinctive="inner-layout" style="display:grid; grid-template-columns: 1fr 1fr; column-gap: 8px;">'
        '<div id="target" style="width:300px;">content</div>'
        "</div></div></section></main></body></html>",
    )
    import os

    original_cwd = Path.cwd()
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


def _region_check(
    columns: int, *, width_ratio_min: float = 0.0, width_ratio_max: float = 1.0
) -> RegionRuntimeCheckV1:
    return RegionRuntimeCheckV1(
        region_id="region-1",
        section_id="hero",
        section_selector="#hero",
        region_selector="#region",
        order_mobile=0,
        order_tablet=0,
        order_desktop=0,
        columns_mobile=1,
        columns_tablet=1,
        columns_desktop=columns,
        max_measure_ch=1000,
        width_ratio_min=width_ratio_min,
        width_ratio_max=width_ratio_max,
        overlap_ratio_max=1.0,
        sticky_allowed=True,
    )


def _font_check() -> FontRuntimeCheckV1:
    return FontRuntimeCheckV1(
        role="display",
        selector="#hero",
        family="Georgia",
        weights=[400],
        local_files=["dummy.woff2"],
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


async def test_asymmetric_two_track_grid_satisfies_an_abstract_multi_column_contract(
    region_site_url,
) -> None:
    contract = DesignRealizationContract(
        route_id="home",
        section_order=["hero"],
        region_checks=[_region_check(columns=8)],
        distinctive_move_checks=[
            DistinctiveMoveRuntimeCheckV1(
                move_id="move-1",
                section_id="hero",
                source_selector="#region",
                target_selector="#region",
                relationship="width_ratio",
                minimum_ratio=0.0,
                maximum_ratio=10.0,
                viewports=["desktop"],
                required_css_properties=[],
            )
        ],
        font_checks=[_font_check()],
    )

    _evidence, diagnostics = await RuntimeVerifier().verify(
        region_site_url, plan=_plan(contract), profile=_profile()
    )

    assert not any(d.code == "RUNTIME_REGION_COLUMN_COUNT" for d in diagnostics), diagnostics


async def test_padding_based_visual_inset_is_measured_as_narrower_than_border_box(
    padded_region_site_url,
) -> None:
    """The real bug: a region with no explicit width but 100px inline
    padding on each side, inside a 1000px main, renders a border box that
    exactly fills main (ratio 1.000) even though its visible content is
    only 800px (ratio 0.8). Before the fix this always failed a tight
    0.75-0.85 contract; the fix must measure the content box instead."""

    contract = DesignRealizationContract(
        route_id="home",
        section_order=["hero"],
        region_checks=[_region_check(columns=1, width_ratio_min=0.75, width_ratio_max=0.85)],
        distinctive_move_checks=[
            DistinctiveMoveRuntimeCheckV1(
                move_id="move-1",
                section_id="hero",
                source_selector="#region",
                target_selector="#region",
                relationship="width_ratio",
                minimum_ratio=0.0,
                maximum_ratio=10.0,
                viewports=["desktop"],
                required_css_properties=[],
            )
        ],
        font_checks=[_font_check()],
    )

    _evidence, diagnostics = await RuntimeVerifier().verify(
        padded_region_site_url, plan=_plan(contract), profile=_profile()
    )

    assert not any(d.code == "RUNTIME_REGION_WIDTH_RATIO" for d in diagnostics), diagnostics


async def test_a_region_collapsed_to_one_column_is_still_caught(
    collapsed_region_site_url,
) -> None:
    contract = DesignRealizationContract(
        route_id="home",
        section_order=["hero"],
        region_checks=[_region_check(columns=8)],
        distinctive_move_checks=[
            DistinctiveMoveRuntimeCheckV1(
                move_id="move-1",
                section_id="hero",
                source_selector="#region",
                target_selector="#region",
                relationship="width_ratio",
                minimum_ratio=0.0,
                maximum_ratio=10.0,
                viewports=["desktop"],
                required_css_properties=[],
            )
        ],
        font_checks=[_font_check()],
    )

    _evidence, diagnostics = await RuntimeVerifier().verify(
        collapsed_region_site_url, plan=_plan(contract), profile=_profile()
    )

    assert any(d.code == "RUNTIME_REGION_COLUMN_COUNT" for d in diagnostics), diagnostics


async def test_required_css_properties_are_found_on_the_runtime_marker_element(
    marker_scoped_site_url,
) -> None:
    contract = DesignRealizationContract(
        route_id="home",
        section_order=["hero"],
        region_checks=[_region_check(columns=1)],
        distinctive_move_checks=[
            DistinctiveMoveRuntimeCheckV1(
                move_id="move-1",
                section_id="hero",
                source_selector="#outer",
                target_selector="#target",
                relationship="width_ratio",
                minimum_ratio=0.0,
                maximum_ratio=10.0,
                viewports=["desktop"],
                required_css_properties=["display", "grid-template-columns", "column-gap"],
                runtime_marker='data-distinctive="inner-layout"',
            )
        ],
        font_checks=[_font_check()],
    )

    _evidence, diagnostics = await RuntimeVerifier().verify(
        marker_scoped_site_url, plan=_plan(contract), profile=_profile()
    )

    assert not any(d.code == "RUNTIME_DISTINCTIVE_PROPERTY" for d in diagnostics), diagnostics


async def test_without_a_marker_the_property_check_still_looks_at_source_itself(
    marker_scoped_site_url,
) -> None:
    """Backward compatible: an empty runtime_marker keeps checking
    source_selector directly, unchanged from before this field existed."""

    contract = DesignRealizationContract(
        route_id="home",
        section_order=["hero"],
        region_checks=[_region_check(columns=1)],
        distinctive_move_checks=[
            DistinctiveMoveRuntimeCheckV1(
                move_id="move-1",
                section_id="hero",
                source_selector="#outer",
                target_selector="#target",
                relationship="width_ratio",
                minimum_ratio=0.0,
                maximum_ratio=10.0,
                viewports=["desktop"],
                required_css_properties=["grid-template-columns"],
            )
        ],
        font_checks=[_font_check()],
    )

    _evidence, diagnostics = await RuntimeVerifier().verify(
        marker_scoped_site_url, plan=_plan(contract), profile=_profile()
    )

    assert any(d.code == "RUNTIME_DISTINCTIVE_PROPERTY" for d in diagnostics), diagnostics
