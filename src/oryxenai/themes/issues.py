"""Typed validation issues shared by theme contracts and the Code Generator.

An issue says what is wrong (``code``), where (content ``path``, DOM
``selector``, source ``line``/``column``), and what was expected versus found.
Evidence strings are bounded and print invisible or confusable characters as
``\\uXXXX`` so a mismatch never reads "expected X, found X".
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Literal

Severity = Literal["error", "warning"]

_EVIDENCE_LIMIT = 240


_ESCAPED_CATEGORIES = frozenset({"Zs", "Zl", "Zp", "Cc", "Cf", "Cn", "Co", "Cs", "Pd", "Pi", "Pf"})


def escape_invisible(text: str) -> str:
    """Make invisible, control, special-space, dash and curly-quote characters visible.

    Plain ASCII and ordinary letters (including non-Latin scripts) stay readable;
    the characters people cannot tell apart on screen print as ``\\uXXXX``.
    """
    out: list[str] = []
    for char in text:
        if char == " " or (ord(char) < 128 and char.isprintable()):
            out.append(char)
        elif unicodedata.category(char) in _ESCAPED_CATEGORIES or not char.isprintable():
            out.append(f"\\u{ord(char):04x}" if ord(char) <= 0xFFFF else f"\\U{ord(char):08x}")
        else:
            out.append(char)
    return "".join(out)


def bounded(text: str | None, limit: int = _EVIDENCE_LIMIT) -> str | None:
    """Escape invisibles, then truncate with an ellipsis marker."""
    if text is None:
        return None
    escaped = escape_invisible(text)
    if len(escaped) <= limit:
        return escaped
    return escaped[: limit - 1] + "…"


@dataclass(frozen=True, slots=True)
class Issue:
    """One precise validation finding."""

    code: str
    severity: Severity
    message: str
    path: str | None = None
    selector: str | None = None
    expected: str | None = None
    found: str | None = None
    line: int | None = None
    column: int | None = None
    # Where a browser finding happened: ``viewport:390``, ``request:/styles.css``, ``file:...``.
    origin: str | None = None

    @property
    def is_error(self) -> bool:
        return self.severity == "error"

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }
        for key, value in (
            ("path", self.path),
            ("selector", self.selector),
            ("expected", bounded(self.expected)),
            ("found", bounded(self.found)),
            ("line", self.line),
            ("column", self.column),
            ("origin", self.origin),
        ):
            if value is not None:
                data[key] = value
        return data


def errors_of(issues: list[Issue]) -> list[Issue]:
    return [issue for issue in issues if issue.is_error]


def warnings_of(issues: list[Issue]) -> list[Issue]:
    return [issue for issue in issues if not issue.is_error]
