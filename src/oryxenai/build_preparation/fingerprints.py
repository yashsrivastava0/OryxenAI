"""Canonical, secret-free fingerprints used for reproducibility and staleness."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def projection_hash(*values: Any) -> str:
    return sha256_json(values)


def strip_internal_content(content: dict[str, Any]) -> dict[str, Any]:
    """Return the public, consumed Content Architect projection.

    Persisted agent state also contains worker bookkeeping (run IDs, retry
    counters and timestamps).  Hashing that bookkeeping would make a valid
    preparation stale every time a worker heartbeat or retry is written.
    Keep this allow-list deliberately explicit so new internal fields cannot
    accidentally cross the public build boundary.
    """
    fields = (
        "status",
        "version",
        "source_ref",
        "intake",
        "approved",
        "user_summary",
        "site_story_strategy",
        "decision_basis",
        "route_plan",
        "page_content_packs",
        "public_content_manifest",
        "claim_grounding",
        "omissions",
        "unresolved_issues",
        "privacy_and_confidentiality",
        "media_status",
        "visual_director_handoff",
        "warnings",
    )
    result = {key: content.get(key) for key in fields if key in content}
    packs = result.get("page_content_packs")
    if isinstance(packs, list):
        cleaned_packs: list[Any] = []
        for pack in packs:
            if not isinstance(pack, dict):
                cleaned_packs.append(pack)
                continue
            clean_pack = dict(pack)
            clean_pack.pop("internal_notes", None)
            cleaned_packs.append(clean_pack)
        result["page_content_packs"] = cleaned_packs
    return result


def _visual_public_projection(visual: dict[str, Any]) -> dict[str, Any]:
    """Return the Visual Design Director fields consumed by preparation."""
    fields = (
        "status",
        "version",
        "source_ref",
        "approved",
        "user_summary",
        "meta",
        "source_refs",
        "visual_language",
        "shared_visual_systems",
        "navigation_direction",
        "motion_system",
        "interaction_system",
        "pages",
        "asset_briefs",
        "resource_candidates",
        "accessibility_and_performance",
        "must_preserve",
        "must_not_fabricate",
        "conflicts",
        "warnings",
        "compiler_handoff",
    )
    return {key: visual.get(key) for key in fields if key in visual}


def source_fingerprints(
    content_state: dict[str, Any], visual_state: dict[str, Any]
) -> dict[str, str]:
    content_projection = strip_internal_content(content_state)
    visual_projection = _visual_public_projection(visual_state)
    route_plan = content_projection.get("route_plan", [])
    pairs = sorted(
        (str(item.get("route_id", "")), str(item.get("publication_status", "approved")))
        for item in route_plan
        if isinstance(item, dict) and item.get("route_id")
    )
    return {
        "discovery_projection_hash": sha256_json(
            {
                "source_ref": content_projection.get("source_ref", {}),
                "intake": content_projection.get("intake", {}),
            }
        ),
        "content_projection_hash": sha256_json(content_projection),
        "visual_projection_hash": sha256_json(visual_projection),
        "route_publication_hash": sha256_json(pairs),
    }


def preparation_input_hash(
    source: dict[str, str],
    *,
    policy_hash: str,
    target_contract_hash: str,
    provider_availability: dict[str, bool],
) -> str:
    return sha256_json(
        {
            "source": source,
            "policy_hash": policy_hash,
            "target_contract_hash": target_contract_hash,
            "provider_availability": provider_availability,
        }
    )
