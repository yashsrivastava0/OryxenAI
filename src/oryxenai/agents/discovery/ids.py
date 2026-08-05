"""Stable, deterministic ID generation for Discovery artifacts.

IDs are derived from content so that retries and regenerations produce the
same identifiers. Never relies on model-generated IDs.
"""

from __future__ import annotations

import hashlib
from typing import Any


def _hash(*parts: str) -> str:
    combined = "|".join(parts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]


def fact_id(category: str, field: str, normalized_value: Any, source_refs: list[str]) -> str:
    value_str = _value_to_string(normalized_value)
    refs = sorted(source_refs) if source_refs else ["no-source"]
    return f"fact-{_hash(category, field, value_str, *refs)}"


def conflict_id(field_name: str, alternatives: list[str]) -> str:
    sorted_alts = sorted(alternatives)
    return f"conflict-{_hash(field_name, *sorted_alts)}"


def question_id(
    category: str,
    related_keys: list[str],
    version: int = 1,
) -> str:
    keys = sorted(related_keys) if related_keys else [category]
    return f"q-{_hash(category, str(version), *keys)}"


def operation_idempotency_key(
    session_id: str,
    operation: str,
    source_hash: str,
    answer_hash: str = "",
    prompt_version: str = "",
    model_profile: str = "",
) -> str:
    return _hash(session_id, operation, source_hash, answer_hash, prompt_version, model_profile)


def source_snapshot_id(session_id: str, source_hash: str) -> str:
    return _hash(session_id, "source", source_hash)


def answer_snapshot_hash(answers: dict[str, Any]) -> str:
    import json

    canonical = json.dumps(answers, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def brief_hash(brief: Any) -> str:
    import json

    if hasattr(brief, "model_dump_json"):
        raw = brief.model_dump_json(exclude_none=True)
    else:
        raw = json.dumps(brief, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _value_to_string(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip().lower()
    import json

    return json.dumps(value, sort_keys=True, default=str)
