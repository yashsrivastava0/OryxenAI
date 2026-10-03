"""Immutable one-page package for the Cobalt Atlas design."""

from pathlib import Path

from oryxenai.themes import ThemePackage, load_package
from oryxenai.themes.prototype_contract import PrototypeContract

ROOT = Path(__file__).resolve().parent


def load() -> ThemePackage:
    return load_package(
        ROOT,
        PrototypeContract(
            ROOT,
            theme_id="cobalt-atlas/v1",
            body_class="atlas-page",
            theme_color="#f7f9fc",
            section_classes={
                "top": "atlas-intro",
                "practice": "atlas-gallery",
                "capabilities": "atlas-method",
                "about": "atlas-profile",
                "contact": "atlas-contact",
            },
        ),
    )
