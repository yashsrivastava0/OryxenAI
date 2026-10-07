"""Immutable Claret Marquee v1 CSS and JavaScript theme."""

from pathlib import Path

from oryxenai.themes import ThemePackage, load_package
from oryxenai.themes.claret_marquee.v1.contract import MarqueeContract


def load() -> ThemePackage:
    root = Path(__file__).resolve().parent
    return load_package(root, MarqueeContract(root))
