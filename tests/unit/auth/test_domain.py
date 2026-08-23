from __future__ import annotations

import pytest

from oryxenai.auth.domain import (
    AuthInputError,
    normalize_email,
    normalize_email_list,
    normalize_username,
)


def test_email_lists_are_trimmed_lowercased_and_deduplicated() -> None:
    assert normalize_email_list(" ADMIN@example.com, user@example.com ") == (
        "admin@example.com",
        "user@example.com",
    )

    with pytest.raises(AuthInputError, match="duplicates"):
        normalize_email_list("user@example.com USER@example.com")

    with pytest.raises(AuthInputError):
        normalize_email("not-an-email")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" Ava-Portfolio ", "ava-portfolio"),
        ("a_1", "a_1"),
        ("designer_2026", "designer_2026"),
    ],
)
def test_username_normalization(raw: str, expected: str) -> None:
    assert normalize_username(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "ab",
        "a" * 31,
        "-starts-with-symbol",
        "ends-with-symbol_",
        "has space",
        "name@example.com",
        "admin",
        "API",
        "naïve",
    ],
)
def test_username_rules_and_reserved_names(raw: str) -> None:
    with pytest.raises(AuthInputError):
        normalize_username(raw)
