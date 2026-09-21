from __future__ import annotations

from oryxenai.agents.code_generator.core.source_lexing import strip_source_comments


def test_regex_literal_with_escaped_slash_is_not_mistaken_for_a_comment() -> None:
    source = (
        "export function trimTrailingSlash(path: string): string {\n"
        '  return path.replace(/\\/+$/, "");\n'
        "}\n"
        "export const HOME_PATTERN = /^\\/api\\//;\n"
        'export const isHome = HOME_PATTERN.test("/api/");\n'
    )

    clean = strip_source_comments(source)

    assert "export function trimTrailingSlash" in clean
    assert 'path.replace(/\\/+$/, "")' in clean
    assert "HOME_PATTERN = /^\\/api\\//" in clean
    assert 'HOME_PATTERN.test("/api/")' in clean
    assert "export const isHome" in clean


def test_regex_literal_start_of_expression_after_operators_and_parens() -> None:
    source = (
        "const parts = value.split(/\\/\\//);\n"
        "const matched = value && /\\/[a-z]+\\//.test(value);\n"
        "const filtered = list.filter((item) => /\\/x\\//.test(item));\n"
    )

    clean = strip_source_comments(source)

    assert "value.split(/\\/\\//)" in clean
    assert "/\\/[a-z]+\\//.test(value)" in clean
    assert "/\\/x\\//.test(item)" in clean


def test_division_after_identifier_or_closing_paren_is_not_treated_as_regex() -> None:
    source = "const half = total / 2; // real trailing comment\nconst ratio = getWidth() / getHeight();\n"

    clean = strip_source_comments(source)

    assert "total / 2" in clean
    assert "real trailing comment" not in clean
    assert "getWidth() / getHeight()" in clean


def test_real_comments_still_stripped_around_regex_literals() -> None:
    source = (
        "// leading comment about the pattern\n"
        "const re = /\\/foo\\//; /* trailing block comment */\n"
    )

    clean = strip_source_comments(source)

    assert "leading comment about the pattern" not in clean
    assert "const re = /\\/foo\\//;" in clean
    assert "trailing block comment" not in clean


def test_division_context_after_identifier_is_never_treated_as_regex_start() -> None:
    source = "const path = a / b\nconst next = 1;\n"

    clean = strip_source_comments(source)

    assert "const path = a / b" in clean
    assert "const next = 1;" in clean


def test_jsx_closing_tag_slash_does_not_swallow_a_following_comment() -> None:
    source = (
        '<a href="https://example.test/profile">Link</a> // marker-only comment\n'
        "export const ready = true;\n"
    )

    clean = strip_source_comments(source)

    assert "https://example.test/profile" in clean
    assert "</a>" in clean
    assert "marker-only comment" not in clean
    assert "export const ready = true;" in clean


def test_regex_scan_that_hits_a_newline_before_closing_falls_back_unchanged() -> None:
    source = "const re = /abc\ndef/;\nconst next = 2;\n"

    clean = strip_source_comments(source)

    assert "const re = /abc" in clean
    assert "def/;" in clean
    assert "const next = 2;" in clean
