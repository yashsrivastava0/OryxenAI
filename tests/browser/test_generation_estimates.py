"""Configured estimates remain legible beside real progress on desktop and mobile."""

from __future__ import annotations

from typing import Any

import pytest
from tests.browser.helpers import BASE_URL, assert_no_horizontal_overflow, expect, shot


@pytest.mark.parametrize("width", [1366, 390])
@pytest.mark.parametrize(
    ("fixture", "range_text"),
    [
        ("discovery-questions-working", "10\u201330"),
        ("discovery-brief-working", "25\u201360"),
        ("content-working", "30\u201390"),
        ("studio-working", "25\u201335"),
    ],
)
def test_estimates_are_visible_without_overflow(
    browser_page: Any, fixture: str, range_text: str, width: int
) -> None:
    page = browser_page
    page.set_viewport_size({"width": width, "height": 900})
    page.goto(f"{BASE_URL}/?fixture={fixture}", wait_until="networkidle")
    estimate = page.get_by_label("Generation time estimate")
    expect(estimate).to_be_visible()
    expect(estimate).to_contain_text(range_text)
    expect(estimate).to_contain_text("Elapsed")
    assert_no_horizontal_overflow(page)
    shot(page, f"{fixture}-{width}")
