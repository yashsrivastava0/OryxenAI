"""Canonical v4 resource-query compilation and receipts."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import ResourceSearchIntentV2
from oryxenai.agents.shared.image_retrieval import bounded_provider_query


def compile_resource_queries(
    intent: ResourceSearchIntentV2,
    *,
    provider: str,
    max_variants: int = 3,
) -> list[str]:
    """Return at most ``max_variants`` short positive provider queries."""

    variants: list[str] = intent.query_variants or [
        " ".join(intent.subject_terms + intent.context_terms)
    ]
    result: list[str] = []
    for variant in variants[: max(1, max_variants)]:
        value = variant if isinstance(variant, str) else " ".join(variant)
        query = bounded_provider_query(value, provider, max_terms=6)
        if query and query not in result:
            result.append(query)
    return result


def query_receipt(
    intent: ResourceSearchIntentV2,
    *,
    provider: str,
    sent_queries: list[str],
) -> dict[str, Any]:
    """Persist the exact values sent to a provider plus a stable intent hash."""

    payload = intent.model_dump(mode="json")
    intent_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    return {
        "schema_version": "resource-query-receipt-v1",
        "slot_id": intent.slot_id,
        "provider": provider,
        "intent_hash": intent_hash,
        "sent_queries": list(sent_queries),
        "negative_concepts": list(intent.negative_concepts),
        "provider_filters": list(intent.provider_filters),
    }


__all__ = ["compile_resource_queries", "query_receipt"]
