"""Server-owned Explorer presentation, separate from immutable theme packages."""

from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from oryxenai.themes import list_theme_ids

Color = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
Colors = tuple[Color, Color, Color]
CATALOG_PATH = Path(__file__).resolve().parents[3] / "config" / "themes.toml"


class ThemePresentation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    collection: Literal["interactive", "classic"] = "classic"
    badge: str = Field(default="", max_length=60)
    style: Literal["editorial", "minimal", "bold", "layered", "cinematic"] = "editorial"
    colors: Colors


class ThemeChoice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    theme_id: str = Field(min_length=1)
    label: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=180)
    swatches: Colors
    selectable: bool = True
    presentation: ThemePresentation


class _Catalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    themes: list[ThemeChoice] = Field(min_length=1)


def load_catalog(path: Path) -> tuple[ThemeChoice, ...]:
    with path.open("rb") as source:
        choices = _Catalog.model_validate(tomllib.load(source)).themes
    if len({choice.id for choice in choices}) != len(choices):
        raise ValueError("Theme catalog choice ids must be unique")
    if len({choice.theme_id for choice in choices}) != len(choices):
        raise ValueError("Theme catalog versions must be unique")
    if any(choice.theme_id not in list_theme_ids() for choice in choices):
        raise ValueError("Theme catalog references an unregistered theme")
    if not any(choice.selectable for choice in choices):
        raise ValueError("Theme catalog must contain a selectable theme")
    return tuple(choices)


@lru_cache(maxsize=1)
def theme_catalog() -> tuple[ThemeChoice, ...]:
    return load_catalog(CATALOG_PATH)
