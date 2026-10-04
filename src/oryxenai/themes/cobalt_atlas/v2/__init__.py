"""Immutable Cobalt Atlas v2 CSS and JavaScript theme."""

from pathlib import Path

from oryxenai.themes import ThemePackage, load_package
from oryxenai.themes.cobalt_atlas.v2.contract import AtlasContract


def load() -> ThemePackage:
    root = Path(__file__).resolve().parent
    return load_package(root, AtlasContract(root))
