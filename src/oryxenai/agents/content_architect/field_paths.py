"""Canonical field paths for model-authored Content Architect evidence links."""

from __future__ import annotations

from typing import Any


def normalize_output_field_paths(output: dict[str, Any]) -> dict[str, Any]:
    """Accept the unambiguous JSON-root prefix while storing page-relative paths.

    The schema calls the containing object ``page_content``. Models sometimes
    include that name in evidence paths, although the path resolver receives
    the page object itself. Only this exact prefix is removed; malformed or
    unpopulated paths still fail the usual validation gates.
    """
    normalized = dict(output)
    for field in ("claim_grounding", "coverage_ledger"):
        entries = output.get(field)
        if not isinstance(entries, list):
            continue
        normalized[field] = [
            _normalize_entry(entry) if isinstance(entry, dict) else entry for entry in entries
        ]
    return normalized


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    paths = entry.get("field_paths")
    if not isinstance(paths, list):
        return entry
    return {
        **entry,
        "field_paths": [
            path.removeprefix("page_content.")
            if isinstance(path, str) and path.startswith("page_content.")
            else path
            for path in paths
        ],
    }
