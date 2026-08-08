"""Deterministic local resource-catalogue lookup for Visual Design Director.

Plain in-process Python, NOT a model tool-calling loop — no such mechanism
exists in this codebase's ModelClient protocol (single-shot JSON-object-mode
structured generation only), and DECISIONS.md D-001 rules out adding one.
`find_candidates` runs entirely before any model call; its result is fed
into the prompt as ordinary data, and the model may only ever reference a
`resource_id` that was actually in the shortlist it was given — enforced in
validators.py, not here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_CATALOGUE_PATH = Path(__file__).resolve().parent / "resources" / "catalogue.json"

_REQUIRED_KEYS = {
    "resource_id",
    "category",
    "name",
    "tags",
    "description",
    "when_to_use",
    "constraints",
}


def _load_catalogue() -> list[dict[str, Any]]:
    with _CATALOGUE_PATH.open("r", encoding="utf-8") as fh:
        data: list[dict[str, Any]] = json.load(fh)
    return data


def _load_catalogue_version() -> str:
    """Stable 12-char hash of the checked-in catalogue file's raw bytes.

    Stamped onto every persisted ResourceCandidate so a future consumer can
    tell exactly which catalogue snapshot verified a given resource_id,
    without re-deriving it from git history or code behavior.
    """
    raw = _CATALOGUE_PATH.read_bytes()
    return hashlib.sha256(raw).hexdigest()[:12]


# Loaded once at import time — a small, checked-in, deterministic fixture,
# never a network call or per-request re-read.
_CATALOGUE: list[dict[str, Any]] = _load_catalogue()
_CATALOGUE_VERSION: str = _load_catalogue_version()
_CATALOGUE_BY_ID: dict[str, dict[str, Any]] = {
    str(entry["resource_id"]): entry for entry in _CATALOGUE if entry.get("resource_id")
}


def find_candidates(tags: list[str], *, limit: int = 6) -> list[dict[str, Any]]:
    """Return up to `limit` catalogue entries ranked by tag overlap with `tags`.

    Deterministic: identical `tags` input always produces identical output.
    Scoring is the count of overlapping tags; ties break by catalogue file
    order (stable, no randomness). An empty `tags` list returns the first
    `limit` catalogue entries as a generic baseline shortlist rather than an
    empty result.
    """
    if not tags:
        return [dict(entry) for entry in _CATALOGUE[:limit]]

    wanted = set(tags)
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for index, entry in enumerate(_CATALOGUE):
        entry_tags = set(entry.get("tags", []) or [])
        overlap = len(wanted & entry_tags)
        if overlap > 0:
            scored.append((overlap, index, entry))

    if not scored:
        return [dict(entry) for entry in _CATALOGUE[:limit]]

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [dict(entry) for _, _, entry in scored[:limit]]


def catalogue_size() -> int:
    return len(_CATALOGUE)


def catalogue_version() -> str:
    """Stable identifier for the currently-loaded catalogue snapshot."""
    return _CATALOGUE_VERSION


def get_entry(resource_id: str) -> dict[str, Any] | None:
    """Look up one catalogue entry by resource_id, or None if unknown.

    Used by agent.py to deterministically stamp `category` onto a
    ResourceCandidate after validation has already confirmed the
    resource_id is real — never used to validate the reference itself.
    """
    entry = _CATALOGUE_BY_ID.get(resource_id)
    return dict(entry) if entry is not None else None


def validate_catalogue_integrity() -> list[str]:
    """Self-check the checked-in fixture — used by tests, not runtime code."""
    errors: list[str] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(_CATALOGUE):
        missing = _REQUIRED_KEYS - entry.keys()
        if missing:
            errors.append(f"entry {index} missing keys: {sorted(missing)}")
        resource_id = entry.get("resource_id", "")
        if not resource_id:
            errors.append(f"entry {index} has no resource_id")
        elif resource_id in seen_ids:
            errors.append(f"duplicate resource_id: {resource_id}")
        else:
            seen_ids.add(resource_id)
    return errors
