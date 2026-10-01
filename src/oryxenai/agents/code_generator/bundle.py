"""Compose and seal the page bundle: host head + model body + theme files.

The sealed unit is ``index.html`` (stored with the version) plus the theme's
unchanged files, listed by hash. Preview and verification serve exactly these
bytes; nothing is rewritten after sealing.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from oryxenai.themes import ThemePackage, media_type_for


@dataclass(frozen=True, slots=True)
class SiteBundle:
    theme_id: str
    css_sha256: str
    lang: str
    index_html: str
    index_sha256: str
    manifest: dict[str, Any]


def compose_document(
    page_content: Mapping[str, Any],
    derived: Mapping[str, Any],
    body_html: str,
    lang: str,
    theme: ThemePackage,
) -> str:
    contract = theme.contract
    return (
        contract.render_head(page_content, derived, lang)
        + body_html.strip("\n")
        + contract.render_tail()
    )


def build_bundle(
    page_content: Mapping[str, Any],
    derived: Mapping[str, Any],
    body_html: str,
    lang: str,
    theme: ThemePackage,
) -> SiteBundle:
    index_html = compose_document(page_content, derived, body_html, lang, theme)
    data = index_html.encode("utf-8")
    index_sha = hashlib.sha256(data).hexdigest()
    safe_lang = lang if theme.contract.valid_language(lang) else theme.contract.default_language
    manifest: dict[str, Any] = {
        "contract_version": "SiteBundle/v1",
        "theme_id": theme.theme_id,
        "files": [
            {"path": "index.html", "sha256": index_sha, "bytes": len(data), "source": "version"},
            *theme.manifest_entries(),
        ],
    }
    return SiteBundle(theme.theme_id, theme.css_sha256, safe_lang, index_html, index_sha, manifest)


def resolve_bundle_file(
    index_html: str, theme: ThemePackage, path: str
) -> tuple[bytes, str] | None:
    """Bytes and media type for a bundle-relative path, or ``None`` if absent."""
    normalized = path.strip("/") or "index.html"
    if normalized == "index.html":
        return index_html.encode("utf-8"), media_type_for("index.html")
    entry = theme.file(normalized)
    if entry is None:
        return None
    return entry.data, entry.media_type
