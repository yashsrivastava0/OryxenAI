"""Independent theme contracts accept the supported single-page content shapes."""

from __future__ import annotations

import pytest

from oryxenai.agents.code_generator.dev.reference_renderer import render_body
from oryxenai.agents.code_generator.validate import validate_page
from oryxenai.themes import get_theme
from tests.unit.agents.code_generator.helpers import shapes


@pytest.mark.parametrize("theme_id", ["cobalt-atlas/v1", "obsidian-signal/v1"])
@pytest.mark.parametrize("shape_name", list(shapes()))
def test_selected_theme_accepts_supported_content_shapes(theme_id: str, shape_name: str) -> None:
    theme = get_theme(theme_id)
    content = shapes()[shape_name]
    body = render_body(content, theme_id=theme_id)

    report = validate_page(body, content, theme)
    assert report.ok, [issue.to_dict() for issue in report.errors]


@pytest.mark.parametrize("theme_id", ["cobalt-atlas/v1", "obsidian-signal/v1"])
def test_selected_theme_rejects_copy_changed_in_markup(theme_id: str) -> None:
    theme = get_theme(theme_id)
    content = shapes()["01_strong_profile"]
    body = render_body(content, theme_id=theme_id)
    altered = body.replace(content["hero"]["name"], "Someone Else", 1)

    report = validate_page(altered, content, theme)
    assert not report.ok
    assert {issue.code for issue in report.errors} & {"PAGE_COPY_MISMATCH", "CONTENT_BINDING_VALUE"}
