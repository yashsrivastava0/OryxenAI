"""Immutable one-page package for the Obsidian Signal design."""

from pathlib import Path

from oryxenai.themes import ThemePackage, load_package
from oryxenai.themes.prototype_contract import PrototypeContract

ROOT = Path(__file__).resolve().parent


def load() -> ThemePackage:
    return load_package(
        ROOT,
        PrototypeContract(
            ROOT,
            theme_id="obsidian-signal/v1",
            body_class="sg-page",
            theme_color="#0c0e0d",
            section_classes={
                "top": "sg-hero",
                "practice": "sg-work",
                "capabilities": "sg-process",
                "about": "sg-about",
                "contact": "sg-contact",
            },
        ),
    )
