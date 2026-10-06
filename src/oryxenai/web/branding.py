"""Public app icon assets shared by product and authentication shells."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

BRAND_DIR = Path(__file__).resolve().parent / "static" / "brand"
BRAND_ASSETS = frozenset(
    {
        "favicon.ico",
        "favicon-32.png",
        "apple-touch-icon.png",
        "app-192.png",
        "app-512.png",
        "site.webmanifest",
    }
)


@lru_cache(maxsize=1)
def brand_version() -> str:
    """Content version stays stable across builds and changes with the artwork."""
    return hashlib.sha256((BRAND_DIR / "favicon.ico").read_bytes()).hexdigest()[:12]
