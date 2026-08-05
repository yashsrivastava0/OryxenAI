"""Unit tests for Discovery input preprocessing."""

from __future__ import annotations

from oryxenai.agents.discovery.preprocessing import (
    compact_resume,
    compute_source_hash,
    deduplicate_lines,
    normalize_line_endings,
    normalize_unicode,
    normalize_url,
    preprocess_text,
    remove_unsafe_control_characters,
    trim_repeated_blank_lines,
)


class TestNormalizeLineEndings:
    def test_crlf_to_lf(self):
        assert normalize_line_endings("hello\r\nworld") == "hello\nworld"

    def test_cr_to_lf(self):
        assert normalize_line_endings("hello\rworld") == "hello\nworld"

    def test_no_change(self):
        assert normalize_line_endings("hello\nworld") == "hello\nworld"


class TestNormalizeUnicode:
    def test_nfc_normalization(self):
        text = "C\u0327"
        result = normalize_unicode(text)
        assert len(result) < len(text)

    def test_already_normalized(self):
        assert normalize_unicode("hello") == "hello"


class TestRemoveUnsafeControlCharacters:
    def test_removes_bell(self):
        assert "\x07" not in remove_unsafe_control_characters("a\x07b")

    def test_preserves_newline(self):
        assert "\n" in remove_unsafe_control_characters("a\nb")

    def test_preserves_tab(self):
        assert "\t" in remove_unsafe_control_characters("a\tb")

    def test_removes_null(self):
        assert "\x00" not in remove_unsafe_control_characters("a\x00b")


class TestTrimRepeatedBlankLines:
    def test_collapses_many_blanks(self):
        text = "a\n\n\n\n\nb"
        result = trim_repeated_blank_lines(text, max_consecutive=2)
        assert result == "a\n\n\nb"

    def test_leaves_two_blanks(self):
        text = "a\n\n\nb"
        result = trim_repeated_blank_lines(text, max_consecutive=2)
        assert result == "a\n\n\nb"


class TestDeduplicateLines:
    def test_removes_exact_duplicate(self):
        text = "Python\nJava\nPython\nC"
        result = deduplicate_lines(text)
        assert result.count("Python") == 1

    def test_keeps_unique_lines(self):
        text = "Python\nJava\nC++"
        result = deduplicate_lines(text)
        assert result.count("Python") == 1
        assert result.count("Java") == 1
        assert result.count("C++") == 1

    def test_preserves_non_empty_blanks(self):
        text = "Python\n\nJava\nPython"
        result = deduplicate_lines(text)
        parts = result.split("\n")
        assert parts[0] == "Python"
        assert parts[2] == "Java"


class TestCompactResume:
    def test_no_compaction_needed(self):
        text = "Short resume"
        compacted, was_compacted = compact_resume(text, 1000)
        assert compacted == text
        assert not was_compacted

    def test_compaction_applied(self):
        text = "EXPERIENCE\nEngineer at Corp\nDid many things\nBuilt systems\n" * 100
        compacted, was_compacted = compact_resume(text, 200)
        assert len(compacted) <= 200
        assert was_compacted


class TestNormalizeUrl:
    def test_lowercase_scheme_host(self):
        result = normalize_url("HTTPS://Example.COM/Path")
        assert result.startswith("https://example.com")

    def test_trailing_slash_added(self):
        result = normalize_url("https://example.com")
        assert result == "https://example.com/"

    def test_strips_tracking(self):
        result = normalize_url("https://example.com/path")
        assert result == "https://example.com/path"


class TestComputeSourceHash:
    def test_same_text_same_hash(self):
        h1 = compute_source_hash("Hello World")
        h2 = compute_source_hash("Hello World")
        assert h1 == h2

    def test_different_text_different_hash(self):
        h1 = compute_source_hash("Hello World")
        h2 = compute_source_hash("Hello World!")
        assert h1 != h2


class TestPreprocessText:
    def test_basic_preprocessing(self):
        text = "Hello\r\n\r\n\r\n\r\n\r\nWorld\x00"
        result, _warnings = preprocess_text(text)
        assert "Hello" in result
        assert "World" in result
        assert "\x00" not in result

    def test_compaction_warning(self):
        text = "x " * 5000
        _result, warnings = preprocess_text(text, max_chars=500)
        assert any(w.code == "resume_input_compacted" for w in warnings)

    def test_no_warning_for_short_text(self):
        text = "Short text"
        _result, warnings = preprocess_text(text, max_chars=1000)
        assert len(warnings) == 0
