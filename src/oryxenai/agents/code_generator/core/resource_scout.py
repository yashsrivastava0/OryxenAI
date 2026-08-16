"""Bounded text-only resource-scout context assembly."""

from __future__ import annotations

from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import (
    ResourceCandidate,
    ResourceRequest,
)


def build_resource_scout_context(
    request: ResourceRequest, candidates: list[ResourceCandidate]
) -> dict[str, Any]:
    """Return metadata only; resource bytes and provider clients never enter context."""

    return {
        "request_text": {
            "category": request.category,
            "purpose": request.placement.purpose,
            "positive_terms": request.query.positive_terms,
            "negative_terms": request.query.negative_terms,
            "requiredness": request.requiredness,
        },
        "candidate_summaries": [
            {
                "candidate_id": candidate.candidate_id,
                "provider_key": candidate.provider_key,
                "title": candidate.title,
                "description": candidate.description,
                "tags": candidate.tags,
                "technical_metadata": candidate.technical_metadata,
                "canonical_source": candidate.canonical_source,
                "licence": candidate.licence,
                "attribution": candidate.attribution,
                "vendoring_policy": candidate.vendoring_policy,
                "dependency_metadata": candidate.dependency_metadata,
            }
            for candidate in candidates
        ],
    }
