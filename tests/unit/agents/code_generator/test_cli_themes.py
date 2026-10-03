"""The developer render command must use the requested theme's markup."""

from __future__ import annotations

from argparse import Namespace

import pytest

from oryxenai.agents.code_generator.cli import _command_render
from oryxenai.themes import get_theme


@pytest.mark.parametrize("theme_id", ["cobalt-atlas/v1", "obsidian-signal/v1"])
def test_render_command_writes_selected_theme(tmp_path, theme_id: str) -> None:
    output = tmp_path / "render"
    args = Namespace(sample="01_strong_profile", content=None, theme=theme_id, out=output)

    assert _command_render(args) == 0
    assert (output / "styles.css").read_bytes() == get_theme(theme_id).stylesheet.data
    assert "Priya Nandan" in (output / "index.html").read_text(encoding="utf-8")
