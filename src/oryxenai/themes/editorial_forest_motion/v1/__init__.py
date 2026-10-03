"""Immutable one-page package for the Editorial Forest Motion design."""

from pathlib import Path

from oryxenai.themes import ThemePackage, load_package
from oryxenai.themes.editorial_forest.v1.contract import EditorialForestContract

ROOT = Path(__file__).resolve().parent


class EditorialForestMotionContract(EditorialForestContract):
    theme_id = "editorial-forest-motion/v1"


def load() -> ThemePackage:
    return load_package(ROOT, EditorialForestMotionContract(ROOT))
