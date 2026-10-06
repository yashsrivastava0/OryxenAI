"""Page language for host-rendered builds: the dominant script of the approved copy."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

# (first code point, last code point, BCP-47 tag); kana is checked before CJK ideographs.
_SCRIPTS: tuple[tuple[int, int, str], ...] = (
    (0x0370, 0x03FF, "el"),
    (0x0400, 0x04FF, "ru"),
    (0x0590, 0x05FF, "he"),
    (0x0600, 0x06FF, "ar"),
    (0x0900, 0x097F, "hi"),
    (0x0980, 0x09FF, "bn"),
    (0x0B80, 0x0BFF, "ta"),
    (0x0E00, 0x0E7F, "th"),
    (0x3040, 0x30FF, "ja"),
    (0x4E00, 0x9FFF, "zh"),
    (0xAC00, 0xD7AF, "ko"),
)
_SAMPLE_FIELDS = (("hero", "intro"), ("hero", "headline_prefix"), ("systems_practice", "intro"))


def detect_language(page_content: Mapping[str, Any], default: str = "en") -> str:
    """BCP-47 tag of the script most of the hero copy is written in (``default`` for Latin)."""
    letters: Counter[str] = Counter()
    for region, field in _SAMPLE_FIELDS:
        block = page_content.get(region)
        text = block.get(field) if isinstance(block, Mapping) else None
        for char in text if isinstance(text, str) else "":
            if char.isalpha():
                letters[
                    next((tag for lo, hi, tag in _SCRIPTS if lo <= ord(char) <= hi), default)
                ] += 1
    if not letters:
        return default
    if letters["ja"]:
        letters["ja"] += letters.pop("zh", 0)
    tag, count = letters.most_common(1)[0]
    return tag if count * 2 >= sum(letters.values()) else default
