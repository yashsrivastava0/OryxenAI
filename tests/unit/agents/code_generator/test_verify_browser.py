"""Browser verification: policy paths always run; real-Chromium cases skip without a browser."""

from __future__ import annotations

import hashlib

import pytest

from oryxenai.agents.code_generator.bundle import SiteBundle, build_bundle
from oryxenai.agents.code_generator.dev.reference_renderer import render_body
from oryxenai.agents.code_generator.verify_browser import BrowserVerifier, build_verifier
from oryxenai.core.settings import CodeGeneratorVerificationConfig
from oryxenai.themes import get_theme
from tests.unit.agents.code_generator.helpers import sample_content, shapes

THEME = get_theme()
HEAD_CONTENT = sample_content("01_strong_profile")
DERIVED = THEME.contract.derive(HEAD_CONTENT)
ALL_VIEWPORTS = [320, 390, 768, 1280]


def _config(**overrides: object) -> CodeGeneratorVerificationConfig:
    values: dict[str, object] = {
        "browser": "best_effort",
        "viewports": ALL_VIEWPORTS,
        "page_timeout_seconds": 25.0,
    }
    values.update(overrides)
    return CodeGeneratorVerificationConfig(**values)  # type: ignore[arg-type]


def _golden(content: dict | None = None) -> SiteBundle:
    content = content or HEAD_CONTENT
    derived = THEME.contract.derive(content)
    return build_bundle(content, derived, render_body(content, derived), "en", THEME)


def _custom(body: str, *, with_head: bool = True) -> SiteBundle:
    head = (
        THEME.contract.render_head(HEAD_CONTENT, DERIVED, "en")
        if with_head
        else "<!doctype html><html lang=en><head><meta charset=utf-8><title>x</title></head><body>"
    )
    html = head + body + THEME.contract.render_tail()
    data = html.encode()
    index_hash = hashlib.sha256(data).hexdigest()
    return SiteBundle(
        THEME.theme_id,
        THEME.css_sha256,
        "en",
        html,
        index_hash,
        {
            "contract_version": "SiteBundle/v1",
            "theme_id": THEME.theme_id,
            "files": [
                {
                    "path": "index.html",
                    "sha256": index_hash,
                    "bytes": len(data),
                    "source": "version",
                },
                *THEME.manifest_entries(),
            ],
        },
    )


# ── policy (no browser needed) ──────────────────────────────────────────────


def test_off_means_no_verifier_at_all() -> None:
    assert build_verifier(_config(browser="off")) is None
    assert isinstance(build_verifier(_config(browser="best_effort")), BrowserVerifier)
    assert isinstance(build_verifier(_config(browser="required")), BrowserVerifier)


@pytest.mark.asyncio
async def test_an_unlaunchable_browser_is_recorded_but_never_blocks_best_effort() -> None:
    verifier = BrowserVerifier(_config(browser_executable="C:/definitely/not/a/browser.exe"))
    result = await verifier.verify(_golden(), THEME)
    assert result.status == "unavailable" and result.issues == []
    assert result.details.get("reason")


@pytest.mark.asyncio
async def test_required_mode_turns_an_unlaunchable_browser_into_a_blocking_finding() -> None:
    verifier = BrowserVerifier(
        _config(browser="required", browser_executable="C:/definitely/not/a/browser.exe")
    )
    result = await verifier.verify(_golden(), THEME)
    assert result.status == "failed"
    assert [issue.code for issue in result.issues] == ["BROWSER_UNAVAILABLE"]
    assert result.issues[0].is_error


# ── real browser ────────────────────────────────────────────────────────────


async def _verify(bundle: SiteBundle, **overrides: object):
    for options in ({}, {"browser_channel": "chrome"}):
        result = await BrowserVerifier(_config(**{**options, **overrides})).verify(bundle, THEME)
        if result.status != "unavailable":
            return result
    pytest.skip("no headless browser can be started on this machine")


@pytest.mark.asyncio
async def test_a_golden_page_passes_at_every_viewport() -> None:
    result = await _verify(_golden())
    assert result.status == "passed", [issue.to_dict() for issue in result.issues]
    assert result.details["viewports"] == ALL_VIEWPORTS
    pages = result.details["pages"]
    assert [page["viewport"] for page in pages] == ALL_VIEWPORTS
    assert all(
        page["loaded"] and page["console_errors"] == 0 and page["images"] >= 1 for page in pages
    )
    assert any(face.endswith(":loaded") for face in pages[0]["fonts"])
    assert result.details["engine"] == "chromium" and result.details["duration_ms"] > 0
    assert not [issue for issue in result.issues if issue.is_error]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "theme_id", ["editorial-forest-motion/v1", "cobalt-atlas/v1", "obsidian-signal/v1"]
)
async def test_selected_designs_pass_browser_verification(theme_id: str) -> None:
    theme = get_theme(theme_id)
    content = HEAD_CONTENT
    derived = theme.contract.derive(content)
    bundle = build_bundle(
        content, derived, render_body(content, derived, theme_id=theme_id), "en", theme
    )
    for options in ({}, {"browser_channel": "chrome"}):
        result = await BrowserVerifier(_config(**options)).verify(bundle, theme)
        if result.status != "unavailable":
            assert result.status == "passed", [issue.to_dict() for issue in result.issues]
            assert result.issues == []
            return
    pytest.skip("no headless browser can be started on this machine")


@pytest.mark.asyncio
async def test_atlas_sparse_page_routes_and_artwork_pass_browser_verification() -> None:
    from copy import deepcopy

    from oryxenai.themes.cobalt_atlas.v2.contract import _symbolic_content

    theme = get_theme("cobalt-atlas/v2")
    content = deepcopy(HEAD_CONTENT)
    content["atlas"] = _symbolic_content()["atlas"]
    content["atlas"]["projects"] = []
    bundle = build_bundle(
        content,
        theme.contract.derive(content),
        theme.contract.render_reference_body(content),
        "en",
        theme,
    )
    result = await BrowserVerifier(_config(viewports=[390, 1280])).verify(bundle, theme)
    if result.status == "unavailable":
        pytest.skip("no headless browser can be started on this machine")
    assert result.status == "passed", [issue.to_dict() for issue in result.issues]


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["minimal", "maximal", "non_latin", "special_characters"])
async def test_other_content_shapes_pass_too(name: str) -> None:
    result = await _verify(_golden(shapes()[name]), viewports=[390, 1280])
    assert result.status == "passed", [issue.to_dict() for issue in result.issues]


@pytest.mark.asyncio
async def test_a_missing_resource_is_reported_with_its_path_and_status() -> None:
    result = await _verify(
        _custom(
            '<main><h1>Hi</h1><img src="./assets/gone.png" alt="" width="10" height="10"></main>'
        ),
        viewports=[390],
    )
    codes = {issue.code for issue in result.issues}
    assert result.status == "failed" and {"REQUEST_FAILED", "IMAGE_BROKEN"} <= codes
    missing = next(issue for issue in result.issues if issue.code == "REQUEST_FAILED")
    assert missing.origin == "request:/assets/gone.png" and "404" in (missing.found or "")


@pytest.mark.asyncio
async def test_a_request_to_another_host_is_blocked_and_reported() -> None:
    result = await _verify(
        _custom('<main><h1>Hi</h1><img src="https://example.com/track.png" alt=""></main>'),
        viewports=[390],
    )
    assert result.status == "failed"
    # The page's own CSP stops the request before it leaves the browser.
    violations = [
        issue for issue in result.issues if issue.code in {"CSP_VIOLATION", "EXTERNAL_REQUEST"}
    ]
    assert violations and "example.com" in (violations[0].found or "")
    assert violations[0].origin in {"viewport:390", "request:https://example.com/track.png"}


@pytest.mark.asyncio
async def test_a_page_the_stylesheet_did_not_style_is_caught() -> None:
    result = await _verify(
        _custom("<main><h1>Unstyled</h1></main>", with_head=False), viewports=[390]
    )
    assert result.status == "failed"
    assert any(issue.code == "STYLESHEET_NOT_APPLIED" for issue in result.issues)


@pytest.mark.asyncio
async def test_horizontal_overflow_is_a_warning_that_never_blocks() -> None:
    wide = "x" * 4000
    result = await _verify(_custom(f"<main><h1>Hi</h1><p>{wide}</p></main>"), viewports=[320])
    overflow = [issue for issue in result.issues if issue.code == "HORIZONTAL_OVERFLOW"]
    assert overflow and not overflow[0].is_error and overflow[0].origin == "viewport:320"
    assert result.status == "passed"
    assert result.details["warning_count"] >= 1
