from pathlib import Path

import pytest
from pydantic import ValidationError

from oryxenai.agents.discovery import palette
from oryxenai.themes import get_theme
from oryxenai.themes.catalog import CATALOG_PATH, load_catalog, theme_catalog


def test_catalog_matches_theme_capabilities_and_preserves_pinned_ids() -> None:
    choices = theme_catalog()
    assert {choice.id: choice.theme_id for choice in choices} == palette.PALETTE_TO_THEME
    for choice in choices:
        theme = get_theme(choice.theme_id)
        assert (choice.presentation.collection == "interactive") == theme.allows_scripts
    question = palette.palette_question()
    assert question.options[0].theme.collection == "interactive"
    assert {option.id for option in question.options} == {choice.id for choice in choices}


@pytest.mark.parametrize(
    "original,replacement,error",
    [
        ('id = "claret_amber"', 'id = "cobalt_atlas_interactive"', ValueError),
        ('theme_id = "claret-marquee/v1"', 'theme_id = "unknown/v1"', ValueError),
        ('"#3b0f1e"', '"url(https://example.com)"', ValidationError),
        ('collection = "interactive"', 'collection = "unknown"', ValidationError),
    ],
)
def test_bad_catalog_entries_are_rejected(tmp_path: Path, original, replacement, error) -> None:
    source = tmp_path / "themes.toml"
    source.write_text(
        CATALOG_PATH.read_text(encoding="utf-8").replace(original, replacement), encoding="utf-8"
    )
    with pytest.raises(error):
        load_catalog(source)


def test_retiring_a_choice_keeps_history_without_accepting_new_selection(monkeypatch) -> None:
    choices = theme_catalog()
    retired = choices[0].model_copy(update={"selectable": False})
    monkeypatch.setattr(palette, "theme_catalog", lambda: (retired, *choices[1:]))
    assert retired.id not in {option.id for option in palette.palette_question().options}
    assert palette.PALETTE_TO_THEME[retired.id] == retired.theme_id
    assert palette.palette_answer({"choice_id": retired.id, "note": ""}) is None
    assert palette.palette_answer({"choice_id": choices[1].id, "note": ""})
