"""Deterministic, versioned Build Preparation pack-v2 projections.

This module deliberately contains no model or storage code.  It is the
consumer boundary for Build Preparation: a pack is accepted only when the
approved Content Architect and Visual Design Director projections describe
the same public route graph and can be written without lossy identifiers.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

PACK_VERSION = "build-preparation-pack-v2"
SCHEMA_VERSION = "build-preparation-contract-v2"


class PackContractError(ValueError):
    """A safe deterministic pack-contract rejection."""

    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def projection_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _id(value: object, label: str) -> str:
    result = str(value or "").strip()
    if not result or any(ord(char) < 32 for char in result):
        raise PackContractError(
            "BUILD_PACK_V2_INVALID_ID", f"{label} must be a non-empty safe identifier."
        )
    return result


def _path(value: object) -> str:
    path = str(value or "").strip()
    if not path.startswith("/") or "\\" in path or "//" in path or ".." in path.split("/"):
        raise PackContractError(
            "BUILD_PACK_V2_UNSAFE_ROUTE_PATH",
            "Every public route must have a normalized absolute path.",
            details={"path": path},
        )
    if any(ord(char) < 32 for char in path):
        raise PackContractError(
            "BUILD_PACK_V2_UNSAFE_ROUTE_PATH", "A route path contains control characters."
        )
    return "/" if path == "/" else path.rstrip("/")


def _storage_key(route_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", route_id.lower()).strip("-") or "route"
    digest = hashlib.sha256(route_id.encode("utf-8")).hexdigest()[:12]
    return f"routes/{slug}-{digest}"


def _public_routes(content: dict[str, Any]) -> list[dict[str, Any]]:
    raw = content.get("route_plan")
    if not isinstance(raw, list) or not raw:
        raise PackContractError(
            "BUILD_PACK_V2_CONTENT_ROUTES_EMPTY",
            "Approved Content Architect routes are required.",
        )
    routes: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    route_statuses: dict[str, str] = {}
    for item in raw:
        if (
            not isinstance(item, dict)
            or str(item.get("publication_status", "approved")) != "approved"
        ):
            if isinstance(item, dict):
                route_id = str(item.get("route_id", "") or "")
                route_statuses[route_id] = str(item.get("publication_status", "approved"))
            continue
        route_id = _id(item.get("route_id"), "route_id")
        path = _path(item.get("path"))
        if route_id in seen_ids or route_id.casefold() in {value.casefold() for value in seen_ids}:
            raise PackContractError(
                "BUILD_PACK_V2_ROUTE_ID_COLLISION",
                "Public route IDs must be unique without case collisions.",
            )
        if path.casefold() in seen_paths:
            raise PackContractError(
                "BUILD_PACK_V2_ROUTE_PATH_COLLISION",
                "Public route paths must be unique without case collisions.",
            )
        seen_ids.add(route_id)
        seen_paths.add(path.casefold())
        routes.append(
            {
                "route_id": route_id,
                "path": path,
                "title": str(item.get("title", "") or ""),
                "purpose": str(item.get("purpose", "") or ""),
                "storage_key": _storage_key(route_id),
                "section_sequence": [str(v) for v in item.get("section_sequence", []) if str(v)],
            }
        )
    if not routes:
        raise PackContractError(
            "BUILD_PACK_V2_CONTENT_ROUTES_NONE_APPROVED",
            "No approved public Content Architect routes are available.",
            details={"route_count": len(raw), "route_statuses": route_statuses},
        )
    return routes


def _content_by_route(content: dict[str, Any], route_ids: set[str]) -> dict[str, dict[str, Any]]:
    raw = content.get("page_content_packs")
    if not isinstance(raw, list):
        raise PackContractError(
            "BUILD_PACK_V2_CONTENT_MISSING", "Public page content packs are required."
        )
    result: dict[str, dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        route_id = str(item.get("route_id", "") or "")
        if route_id not in route_ids:
            continue
        if route_id in result:
            raise PackContractError(
                "BUILD_PACK_V2_CONTENT_DUPLICATE", "A route has duplicate public content packs."
            )
        sections = item.get("sections")
        if not isinstance(sections, list):
            raise PackContractError(
                "BUILD_PACK_V2_CONTENT_MISSING",
                "A route content pack has no sections.",
                details={"route_id": route_id},
            )
        clean_sections: list[dict[str, Any]] = []
        section_ids: set[str] = set()
        for section in sections:
            if not isinstance(section, dict):
                raise PackContractError(
                    "BUILD_PACK_V2_CONTENT_INVALID", "A public content section is invalid."
                )
            section_id = _id(section.get("section_id"), "section_id")
            if section_id in section_ids:
                raise PackContractError(
                    "BUILD_PACK_V2_SECTION_COLLISION", "Section IDs must be unique per route."
                )
            section_ids.add(section_id)
            clean_sections.append(
                {
                    "section_id": section_id,
                    "purpose": str(section.get("purpose", "") or ""),
                    "content": section.get("content", {})
                    if isinstance(section.get("content", {}), dict)
                    else {},
                    "claim_ids": [str(v) for v in section.get("claim_ids", []) if str(v)],
                    "priority": str(section.get("priority", "") or ""),
                }
            )
        result[route_id] = {"route_id": route_id, "sections": clean_sections}
    missing = route_ids - set(result)
    if missing:
        raise PackContractError(
            "BUILD_PACK_V2_CONTENT_MISSING",
            "Every public route needs an authoritative content pack.",
            details={"route_ids": sorted(missing)},
        )
    return result


def _claims(content: dict[str, Any]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in content.get("claim_grounding", []) or []:
        if not isinstance(item, dict):
            continue
        claim_id = _id(item.get("claim_id"), "claim_id")
        if claim_id in seen:
            raise PackContractError(
                "BUILD_PACK_V2_FACT_COLLISION", "Claim/fact IDs must be unique."
            )
        seen.add(claim_id)
        claims.append(
            {
                "fact_id": claim_id,
                "statement": str(item.get("statement", "") or ""),
                "source_reference": str(item.get("source_reference", "") or ""),
                "evidence_status": str(item.get("evidence_status", "") or ""),
                "ownership": str(item.get("ownership", "") or ""),
            }
        )
    return claims


def _strip_reasoning(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _strip_reasoning(item)
            for key, item in value.items()
            if key not in {"internal_notes", "memory_update", "rationale", "reasoning"}
        }
    if isinstance(value, list):
        return [_strip_reasoning(item) for item in value]
    return value


def _reference_ids(values: Any, field: str) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        candidate = str(value.get(field, "")) if isinstance(value, dict) else str(value)
        if candidate:
            result.append(candidate)
    return result


def _identified_contract_items(prefix: str, value: Any) -> list[dict[str, Any]]:
    """Give every free-form approved constraint a stable consumer identifier."""
    clean = _strip_reasoning(value)
    if isinstance(clean, dict):
        return [
            {f"{prefix}_id": f"{prefix}:{key}", "key": str(key), "value": item}
            for key, item in sorted(clean.items(), key=lambda item: str(item[0]))
        ]
    if isinstance(clean, list):
        return [
            {f"{prefix}_id": f"{prefix}:{index}", "value": item} for index, item in enumerate(clean)
        ]
    if clean in (None, "", {}):
        return []
    return [{f"{prefix}_id": f"{prefix}:0", "value": clean}]


def compile_v2_projections(
    *,
    content_architect: dict[str, Any],
    visual_design_director: dict[str, Any],
    source_ref: dict[str, Any],
    target_contract: dict[str, Any],
    max_routes: int,
) -> dict[str, dict[str, Any]]:
    """Compile hashable consumer projections; fail closed on any scope drift."""
    routes = _public_routes(content_architect)
    if len(routes) > max_routes:
        raise PackContractError(
            "BUILD_PACK_V2_ROUTE_CEILING",
            "Approved route scope exceeds the configured pack ceiling.",
            details={"count": len(routes), "max_routes": max_routes},
        )
    route_ids = {route["route_id"] for route in routes}
    content = _content_by_route(content_architect, route_ids)
    pages = visual_design_director.get("pages")
    if not isinstance(pages, list):
        raise PackContractError(
            "BUILD_PACK_V2_VDD_ROUTES_MISSING", "Visual Design Director pages are required."
        )
    visual_by_route: dict[str, dict[str, Any]] = {}
    expected_paths = {route["route_id"]: route["path"] for route in routes}
    for page in pages:
        if not isinstance(page, dict):
            continue
        route_id = _id(page.get("route_id"), "route_id")
        if route_id in visual_by_route:
            raise PackContractError(
                "BUILD_PACK_V2_VDD_ROUTE_DUPLICATE",
                "Visual direction contains duplicate route IDs.",
            )
        if route_id not in route_ids:
            raise PackContractError(
                "BUILD_PACK_V2_VDD_ROUTE_UNKNOWN",
                "Visual direction includes a route absent from Content Architect.",
                details={"route_id": route_id},
            )
        if _path(page.get("path")) != expected_paths[route_id]:
            raise PackContractError(
                "BUILD_PACK_V2_ROUTE_PATH_MISMATCH",
                "Content and visual route paths differ.",
                details={"route_id": route_id},
            )
        if (
            str(page.get("publication_status", "approved")) != "approved"
            or page.get("compilable", True) is False
        ):
            raise PackContractError(
                "BUILD_PACK_V2_VDD_ROUTE_PARTIAL",
                "An approved Content route is not compilable in visual direction.",
                details={"route_id": route_id},
            )
        visual_by_route[route_id] = page
    if set(visual_by_route) != route_ids:
        raise PackContractError(
            "BUILD_PACK_V2_VDD_ROUTES_MISSING",
            "Content and visual route sets must match exactly.",
            details={"missing": sorted(route_ids - set(visual_by_route))},
        )

    facts = _claims(content_architect)
    fact_ids = {item["fact_id"] for item in facts}
    for route in routes:
        route_content = content[route["route_id"]]
        section_ids = {section["section_id"] for section in route_content["sections"]}
        if route["section_sequence"] and not set(route["section_sequence"]).issubset(section_ids):
            raise PackContractError(
                "BUILD_PACK_V2_SECTION_COVERAGE",
                "Route section sequence references missing public content.",
                details={"route_id": route["route_id"]},
            )
        for section in route_content["sections"]:
            unknown = set(section["claim_ids"]) - fact_ids
            if unknown:
                raise PackContractError(
                    "BUILD_PACK_V2_FACT_REFERENCE",
                    "Public content references an unknown fact.",
                    details={"route_id": route["route_id"], "fact_ids": sorted(unknown)},
                )
        route["sections"] = [
            {"section_id": item["section_id"], "content_file": f"{route['storage_key']}/data.json"}
            for item in route_content["sections"]
        ]
        route["files"] = {
            "content": f"{route['storage_key']}/data.json",
            "resources": f"{route['storage_key']}/resources.json",
        }

    site = {
        "schema_version": SCHEMA_VERSION,
        "pack_version": PACK_VERSION,
        "routes": routes,
        "public_content": [content[route["route_id"]] for route in routes],
        "facts": facts,
        "criteria": [
            {
                "criterion_id": f"criterion:{route['route_id']}:{index}",
                "route_id": route["route_id"],
                "text": str(item),
            }
            for route in routes
            for index, item in enumerate(
                visual_by_route[route["route_id"]].get("acceptance_criteria", []) or []
            )
        ],
        "runtime_requirements": _identified_contract_items(
            "runtime", content_architect.get("visual_director_handoff", {})
        ),
        "freedoms": _identified_contract_items(
            "freedom", content_architect.get("site_story_strategy", {})
        ),
        "public_content_manifest": _strip_reasoning(
            content_architect.get("public_content_manifest", {})
        ),
    }
    visual = {
        "schema_version": SCHEMA_VERSION,
        "pack_version": PACK_VERSION,
        "global": {
            key: _strip_reasoning(visual_design_director.get(key, {}))
            for key in (
                "visual_language",
                "shared_visual_systems",
                "navigation_direction",
                "motion_system",
                "interaction_system",
                "accessibility_and_performance",
                "must_preserve",
                "must_not_fabricate",
                "compiler_handoff",
            )
        },
        "routes": [
            {
                "route_id": route["route_id"],
                "path": route["path"],
                "scenes": _strip_reasoning(visual_by_route[route["route_id"]].get("scenes", [])),
                "asset_ids": _reference_ids(
                    visual_by_route[route["route_id"]].get("asset_briefs", []), "asset_id"
                ),
                "resource_ids": _reference_ids(
                    visual_by_route[route["route_id"]].get("resource_candidates", []),
                    "resource_id",
                ),
                "acceptance_criteria": _strip_reasoning(
                    visual_by_route[route["route_id"]].get("acceptance_criteria", [])
                ),
                "direction": _strip_reasoning(
                    {
                        key: value
                        for key, value in visual_by_route[route["route_id"]].items()
                        if key
                        not in {
                            "route_id",
                            "path",
                            "scenes",
                            "asset_briefs",
                            "resource_candidates",
                            "acceptance_criteria",
                        }
                    }
                ),
            }
            for route in routes
        ],
        "assets": _strip_reasoning(visual_design_director.get("asset_briefs", [])),
        "resources": _strip_reasoning(visual_design_director.get("resource_candidates", [])),
    }
    content_hash = str(
        (content_architect.get("approved") or {}).get("content_hash", "")
        or source_ref.get("content_architect_content_hash", "")
    )
    visual_hash = str(
        (visual_design_director.get("approved") or {}).get("visual_direction_hash", "")
        or source_ref.get("visual_design_director_direction_hash", "")
    )
    approvals = {
        "schema_version": SCHEMA_VERSION,
        "pack_version": PACK_VERSION,
        "content_architect_content_hash": content_hash,
        "visual_design_director_direction_hash": visual_hash,
        "source_projection_hash": str(source_ref.get("input_projection_hash", "")),
        "approved": bool(content_hash) and bool(visual_hash),
    }
    if not approvals["approved"]:
        raise PackContractError(
            "BUILD_PACK_V2_APPROVALS_MISSING",
            "Both upstream approvals must be present for a v2 pack.",
        )
    targets = {
        "schema_version": SCHEMA_VERSION,
        "pack_version": PACK_VERSION,
        "target": _strip_reasoning(target_contract),
    }
    return {"site": site, "visual": visual, "approvals": approvals, "targets": targets}
