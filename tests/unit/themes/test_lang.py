from __future__ import annotations

import pytest

from oryxenai.themes.lang import detect_language


@pytest.mark.parametrize(
    ("intro", "expected"),
    [
        ("Building careful software for small teams.", "en"),
        ("मैं सावधानी से सॉफ़्टवेयर बनाता हूँ", "hi"),
        ("私は丁寧にソフトウェアを作ります", "ja"),
        ("我专注于构建可靠的软件", "zh"),
        ("Я создаю надёжное программное обеспечение", "ru"),
        ("أبني برمجيات موثوقة", "ar"),
        ("", "en"),
    ],
)
def test_language_follows_the_dominant_script(intro: str, expected: str) -> None:
    assert detect_language({"hero": {"intro": intro}}) == expected


def test_a_mostly_latin_page_with_one_foreign_word_stays_english() -> None:
    assert (
        detect_language({"hero": {"intro": "Designing systems, 設計 and more for teams"}}) == "en"
    )
