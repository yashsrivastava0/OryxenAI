"""Sparse input: assumed Atlas rows are labelled on the page and listed for review."""

from __future__ import annotations

from copy import deepcopy

from oryxenai.agents.code_generator.validate import validate_page
from oryxenai.agents.content_architect.page_content import (
    assumption_notes,
    atlas_page_errors,
)
from oryxenai.themes import get_theme
from oryxenai.themes.cobalt_atlas.v2.contract import SAMPLE_LABEL, _symbolic_content

THEME = get_theme("cobalt-atlas/v2")


def _sparse() -> dict:
    content = _symbolic_content()
    content["atlas"]["statistics"] = [{"kind": "sample", "value": "3", "label": "Projects shipped"}]
    content["atlas"]["experience"] = [
        {
            "kind": "sample",
            "role": "Software Engineer",
            "organization": "A product company",
            "dates": "2021 — Now",
            "description": "Builds and maintains product features.",
        }
    ]
    content["atlas"]["education"] = [
        {"kind": "real", "credential": "B.Tech", "institution": "A university", "dates": "2020"}
    ]
    return content


def test_sample_rows_render_one_label_per_section_and_validate() -> None:
    content = _sparse()
    body = THEME.contract.render_body(content)  # type: ignore[attr-defined]
    assert body.count(SAMPLE_LABEL) == 2
    assert validate_page(body, content, THEME).ok


def test_real_only_content_shows_no_sample_label() -> None:
    content = _sparse()
    for group in ("statistics", "experience"):
        content["atlas"][group][0]["kind"] = "real"
    assert SAMPLE_LABEL not in THEME.contract.render_body(content)  # type: ignore[attr-defined]


def test_a_missing_sample_label_is_rejected() -> None:
    content = _sparse()
    body = THEME.contract.render_body(content)  # type: ignore[attr-defined]
    stripped = body.replace(f'<p class="project-meta">{SAMPLE_LABEL}</p>', "", 1)
    report = validate_page(stripped, content, THEME)
    assert "ATLAS_SAMPLE_LABEL" in {issue.code for issue in report.errors}


def test_sample_disclaimer_in_approved_copy_does_not_duplicate_a_heading_label() -> None:
    content = _sparse()
    content["atlas"]["experience"][0]["description"] = SAMPLE_LABEL
    body = THEME.contract.render_body(content)  # type: ignore[attr-defined]
    assert body.count(SAMPLE_LABEL) == 3
    assert validate_page(body, content, THEME).ok


def test_a_disclaimer_in_copy_cannot_replace_its_missing_section_label() -> None:
    content = _sparse()
    content["atlas"]["experience"][0]["description"] = SAMPLE_LABEL
    body = THEME.contract.render_body(content)  # type: ignore[attr-defined]
    body = body.replace(f'<p class="project-meta">{SAMPLE_LABEL}</p>', "", 1)
    assert body.count(SAMPLE_LABEL) == 2
    assert "ATLAS_SAMPLE_LABEL" in {
        issue.code for issue in validate_page(body, content, THEME).errors
    }


def test_row_kind_is_validated() -> None:
    content = deepcopy(_sparse())
    content["atlas"]["statistics"][0]["kind"] = "invented"
    assert any(
        "kind must be real or sample" in e
        for e in atlas_page_errors(content, allow_illustrative_work=False)
    )
    assert not atlas_page_errors(_sparse(), allow_illustrative_work=False)


def test_every_assumed_item_gets_a_review_note() -> None:
    content = _sparse()
    content["atlas"]["projects"][0]["kind"] = "illustrative"
    notes = assumption_notes(content)
    assert [n.split(" is ")[0] for n in notes] == [
        "Assumed: atlas.experience[0]",
        "Assumed: atlas.statistics[0]",
        "Assumed: atlas.projects[0]",
    ]
    assert assumption_notes({"atlas": _symbolic_content()["atlas"]}) == []
