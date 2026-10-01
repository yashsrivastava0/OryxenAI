"""Editorial Forest v1: the pinned single-page portfolio theme.

``styles.css`` is byte-identical to the reviewed reference stylesheet; the
manifest pins every file. Never edit a file here: ship ``v2`` instead.
"""

from __future__ import annotations

from pathlib import Path

from oryxenai.themes import ThemePackage, load_package
from oryxenai.themes.editorial_forest.v1.contract import EditorialForestContract

ROOT = Path(__file__).resolve().parent


def load() -> ThemePackage:
    return load_package(ROOT, EditorialForestContract(ROOT))
