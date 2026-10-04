"""Exemplars shown to the model must be placeholders, never literal sample copy."""

from __future__ import annotations

import re

import pytest

from oryxenai.agents.code_generator.validate import validate_page
from oryxenai.themes import get_theme
from oryxenai.themes.cobalt_atlas.v2.contract import exemplar_content
from oryxenai.themes.placeholders import placeholderize

THEME = get_theme("cobalt-atlas/v2")


def _exemplar_body(contract_text: str) -> str:
    return re.search(r"<exemplar>\n(.*)</exemplar>", contract_text, re.DOTALL).group(1)  # type: ignore[union-attr]


def test_placeholderize_uses_data_field_paths() -> None:
    assert placeholderize({"a": {"b": ["x", ""]}, "c": [{"d": "y"}]}) == {
        "a": {"b": ["{a.b[0]}", ""]},
        "c": [{"d": "{c[0].d}"}],
    }


def test_atlas_exemplar_has_placeholders_not_sample_words() -> None:
    body = _exemplar_body(THEME.contract.prompt_contract())
    assert 'aria-label="{atlas.projects[0].title} case study"' in body
    assert 'data-title="{metadata.title}"' in body
    assert 'data-title="{atlas.projects[0].title} — {hero.name}"' in body
    assert "Example Name" not in body
    assert "Project case study" not in body


def test_atlas_exemplar_is_a_valid_page_for_its_own_placeholder_content() -> None:
    content = exemplar_content()
    body = _exemplar_body(THEME.contract.prompt_contract())
    report = validate_page(body, content, THEME)
    assert report.ok, [issue.to_dict() for issue in report.errors]


@pytest.mark.parametrize("project", [0, 1, 2])
def test_atlas_exemplar_shows_each_project_variant(project: int) -> None:
    body = _exemplar_body(THEME.contract.prompt_contract())
    assert f"{{atlas.projects[{project}].title}}" in body
