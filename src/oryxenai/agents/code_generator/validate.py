"""Strict validation of a generated page body (no auto-fixing, ever).

Pipeline: size and shape checks, strict parse, forbidden constructs, id/anchor
integrity, class vocabulary, **closed-world visible text**, then the theme's
region-by-region copy binding. Every finding is a typed :class:`Issue` naming
what is wrong, where, and what was expected versus found.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from oryxenai.themes import ThemePackage
from oryxenai.themes.htmltree import Element, ParsedFragment, normalize_text, parse_fragment
from oryxenai.themes.issues import Issue, errors_of, warnings_of

DEFAULT_MAX_BODY_BYTES = 262_144
_MAX_ISSUES = 80
_MAX_TEXT_ISSUES = 25

_DOCUMENT_TAGS = re.compile(r"<\s*(?:!doctype|html|head|body)\b", re.IGNORECASE)
_FORBIDDEN_ATTRIBUTES = frozenset(
    {
        "style", "srcdoc", "srcset", "action", "formaction", "data", "poster", "content",
        "value", "placeholder", "title", "download", "ping", "xlink:href", "integrity",
    }
)  # fmt: skip


@dataclass(slots=True)
class ValidationReport:
    issues: list[Issue]
    fragment: ParsedFragment | None = None
    derived: Mapping[str, Any] = field(default_factory=dict)
    truncated: bool = False

    @property
    def errors(self) -> list[Issue]:
        return errors_of(self.issues)

    @property
    def warnings(self) -> list[Issue]:
        return warnings_of(self.issues)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "truncated": self.truncated,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _early(
    code: str, message: str, *, found: str | None = None, expected: str | None = None
) -> ValidationReport:
    return ValidationReport([Issue(code, "error", message, expected=expected, found=found)])


def validate_page(
    body_html: str,
    page_content: Mapping[str, Any],
    theme: ThemePackage,
    *,
    derived: Mapping[str, Any] | None = None,
    max_bytes: int = DEFAULT_MAX_BODY_BYTES,
) -> ValidationReport:
    """Validate the model's ``body_html`` against the approved content and theme."""
    contract = theme.contract
    values = dict(derived) if derived is not None else contract.derive(page_content)

    if len(body_html.encode("utf-8")) > max_bytes:
        return _early(
            "SIZE_LIMIT",
            f"The generated page body is larger than the {max_bytes}-byte limit.",
            expected=f"<= {max_bytes} bytes",
            found=f"{len(body_html.encode('utf-8'))} bytes",
        )
    stripped = body_html.strip()
    if not stripped.startswith("<"):
        return _early(
            "OUTPUT_NOT_HTML",
            "The output does not start with HTML markup (a code fence or commentary precedes it).",
            expected='markup starting with <a class="skip-link">',
            found=stripped[:80],
        )
    document_tag = _DOCUMENT_TAGS.search(stripped)
    if document_tag is not None:
        return _early(
            "BODY_HAS_DOCUMENT_TAGS",
            "The body must not include <!doctype>, <html>, <head> or <body>; the host owns the document shell.",
            found=stripped[document_tag.start() : document_tag.start() + 40],
        )

    fragment = parse_fragment(stripped)
    issues: list[Issue] = list(fragment.issues)
    if not fragment.ok:
        return ValidationReport(issues, fragment, values)
    for text, line, column in fragment.comments:
        issues.append(
            Issue(
                "COMMENT_PRESENT",
                "warning",
                "HTML comments are not allowed in the page body.",
                found=text.strip()[:80],
                line=line,
                column=column,
            )
        )

    _check_elements(fragment.root, page_content, theme, issues)
    _check_text(fragment.root, page_content, values, theme, issues)
    issues.extend(contract.validate_body(fragment.root, page_content, values))

    truncated = len(issues) > _MAX_ISSUES
    if truncated:
        issues = sorted(issues, key=lambda issue: issue.severity != "error")[:_MAX_ISSUES]
    return ValidationReport(issues, fragment, values, truncated)


# ── element-level checks ─────────────────────────────────────────────────────


def _check_elements(
    root: Element,
    page_content: Mapping[str, Any],
    theme: ThemePackage,
    issues: list[Issue],
) -> None:
    contract = theme.contract
    vocabulary = contract.class_vocabulary()
    approved_urls = contract.approved_urls(page_content)
    asset_paths = contract.asset_paths()
    ids: dict[str, Element] = {}
    anchors: list[tuple[str, Element]] = []
    reported_classes: set[str] = set()

    for element in root.iter_descendants():
        tag = element.tag
        if tag not in contract.allowed_tags:
            issues.append(
                Issue(
                    "TAG_NOT_ALLOWED",
                    "error",
                    f"<{tag}> is not allowed in this theme's markup.",
                    found=f"<{tag}>",
                    line=element.line,
                    column=element.column,
                )
            )
            continue
        permitted = contract.allowed_attributes.get(
            "*", frozenset()
        ) | contract.allowed_attributes.get(tag, frozenset())
        for name, value in element.attrs.items():
            if name.startswith("on") or name in _FORBIDDEN_ATTRIBUTES:
                issues.append(
                    Issue(
                        "ATTRIBUTE_FORBIDDEN",
                        "error",
                        f"The attribute '{name}' is not allowed (<{tag}>).",
                        found=f'{name}="{value[:60]}"',
                        line=element.line,
                        column=element.column,
                    )
                )
            elif name not in permitted:
                issues.append(
                    Issue(
                        "ATTRIBUTE_UNKNOWN",
                        "warning",
                        f"The attribute '{name}' is not part of this theme's markup (<{tag}>).",
                        found=name,
                        line=element.line,
                        column=element.column,
                    )
                )
        for klass in element.classes:
            if klass not in vocabulary and klass not in reported_classes:
                reported_classes.add(klass)
                issues.append(
                    Issue(
                        "CLASS_NOT_IN_THEME",
                        "error",
                        f"The class '{klass}' does not exist in the theme stylesheet.",
                        found=klass,
                        line=element.line,
                        column=element.column,
                    )
                )
        element_id = element.get("id")
        if element_id is not None:
            if element_id in ids:
                issues.append(
                    Issue(
                        "ID_DUPLICATE",
                        "error",
                        f"The id '{element_id}' is used more than once.",
                        found=element_id,
                        line=element.line,
                        column=element.column,
                    )
                )
            ids[element_id] = element
        if tag == "a":
            href = element.get("href")
            if href is None or not href:
                issues.append(
                    Issue(
                        "URL_NOT_ALLOWED",
                        "error",
                        "A link has no href.",
                        line=element.line,
                        column=element.column,
                    )
                )
            elif href.startswith("#"):
                anchors.append((href[1:], element))
            elif href not in approved_urls:
                issues.append(
                    Issue(
                        "URL_NOT_ALLOWED",
                        "error",
                        "A link points to a URL that is not an approved destination.",
                        found=href[:120],
                        line=element.line,
                        column=element.column,
                    )
                )
            target = element.get("target")
            if target is not None and target != "_blank":
                issues.append(
                    Issue(
                        "ATTRIBUTE_UNKNOWN",
                        "warning",
                        'Only target="_blank" is used by this theme.',
                        found=f'target="{target}"',
                        line=element.line,
                        column=element.column,
                    )
                )
        elif tag == "img":
            src = element.get("src")
            if src not in asset_paths:
                issues.append(
                    Issue(
                        "URL_NOT_ALLOWED",
                        "error",
                        "Images must use a bundled theme asset.",
                        expected=", ".join(sorted(asset_paths)),
                        found=(src or "")[:120],
                        line=element.line,
                        column=element.column,
                    )
                )
    for anchor, element in anchors:
        if anchor not in ids:
            issues.append(
                Issue(
                    "ANCHOR_UNRESOLVED",
                    "error",
                    f"The link #{anchor} does not match any id on the page.",
                    found=f"#{anchor}",
                    line=element.line,
                    column=element.column,
                )
            )


# ── closed-world visible text ────────────────────────────────────────────────


def _check_text(
    root: Element,
    page_content: Mapping[str, Any],
    derived: Mapping[str, Any],
    theme: ThemePackage,
    issues: list[Issue],
) -> None:
    approved = theme.contract.approved_text(page_content, derived)
    reported = 0
    suppressed = 0

    def report(found: str, line: int, column: int, where: str) -> None:
        nonlocal reported, suppressed
        if reported >= _MAX_TEXT_ISSUES:
            suppressed += 1
            return
        reported += 1
        issues.append(
            Issue(
                "TEXT_NOT_APPROVED",
                "error",
                f"{where} contains text that is not approved copy, derived data or fixed interface text.",
                found=found,
                line=line,
                column=column,
            )
        )

    for text in root.iter_text_nodes():
        value = normalize_text(text.value)
        if value and value not in approved:
            report(value, text.line, text.column, "The page")
    for element in root.iter_descendants():
        for attribute in ("aria-label", "alt"):
            raw = element.get(attribute)
            if raw is not None and normalize_text(raw) and normalize_text(raw) not in approved:
                report(
                    normalize_text(raw),
                    element.line,
                    element.column,
                    f"The {attribute} attribute",
                )
    if suppressed:
        issues.append(
            Issue(
                "TEXT_NOT_APPROVED",
                "error",
                f"{suppressed} more text nodes were not approved (not listed).",
            )
        )
