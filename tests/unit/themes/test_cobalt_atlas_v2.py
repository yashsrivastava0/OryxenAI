"""Cobalt Atlas v2 keeps all person-specific content in checked HTML."""

from __future__ import annotations

from copy import deepcopy

from oryxenai.agents.code_generator.admission import content_admission_issues
from oryxenai.agents.code_generator.bundle import build_bundle
from oryxenai.agents.code_generator.serving import (
    ServedBundle,
    bundle_integrity_ok,
    preview_headers,
)
from oryxenai.agents.code_generator.validate import validate_page
from oryxenai.agents.content_architect.page_content import atlas_page_errors
from oryxenai.themes import get_theme
from oryxenai.themes.cobalt_atlas.v2.contract import _symbolic_content
from tests.unit.agents.code_generator.helpers import sample_content

THEME = get_theme("cobalt-atlas/v2")


def _body(content: dict) -> str:
    return THEME.contract.render_reference_body(content)  # type: ignore[attr-defined]


def test_real_case_and_empty_work_are_valid_routes() -> None:
    rich = _symbolic_content()
    assert validate_page(_body(rich), rich, THEME).ok
    assert 'id="case-1"' in _body(rich)

    sparse = deepcopy(rich)
    sparse["atlas"]["projects"] = []
    sparse["atlas"]["statistics"] = []
    body = _body(sparse)
    assert validate_page(body, sparse, THEME).ok
    assert 'class="work-empty' in body
    assert 'id="case-' not in body


def test_sparse_approved_content_remains_buildable_without_a_project() -> None:
    content = sample_content("01_strong_profile")
    content["atlas"] = _symbolic_content()["atlas"]
    content["atlas"]["projects"] = []
    content["atlas"]["statistics"] = []
    assert not content_admission_issues(content, theme_id=THEME.theme_id)
    assert validate_page(_body(content), content, THEME).ok


def test_illustration_requires_opt_in_and_a_visible_label() -> None:
    content = _symbolic_content()
    content["atlas"]["projects"] = [
        {
            "kind": "illustrative",
            "title": "Concept",
            "summary": "A hypothetical concept.",
            "role": "",
            "period": "",
            "problem": "A hypothetical challenge.",
            "approach": "A proposed direction.",
            "outcome": "",
            "external_url": "",
        }
    ]
    assert atlas_page_errors(content, allow_illustrative_work=False)
    assert not atlas_page_errors(content, allow_illustrative_work=True)
    body = _body(content)
    assert body.count("Illustrative concept — not real client work") >= 2
    assert validate_page(body, content, THEME).ok


def test_generated_script_and_broken_route_are_rejected() -> None:
    content = _symbolic_content()
    body = _body(content)
    assert not validate_page(body + "<script>alert(1)</script>", content, THEME).ok
    assert not validate_page(body.replace('href="#about"', 'href="#gone"', 1), content, THEME).ok


def test_scripted_preview_checks_all_assets_and_keeps_opaque_sandbox() -> None:
    content = _symbolic_content()
    bundle = build_bundle(content, THEME.contract.derive(content), _body(content), "en", THEME)
    served = ServedBundle(
        bundle.index_html, bundle.theme_id, bundle.css_sha256, bundle.index_sha256, bundle.manifest
    )
    assert bundle_integrity_ok(served, THEME)
    assert not bundle_integrity_ok(
        ServedBundle(
            served.index_html,
            served.theme_id,
            served.theme_sha256,
            served.index_sha256,
            {"files": []},
        ),
        THEME,
    )
    policy = preview_headers(html=True, scripts=True)["Content-Security-Policy"]
    assert "script-src 'self'" in policy
    assert "sandbox allow-scripts" in policy
    assert "allow-same-origin" not in policy
