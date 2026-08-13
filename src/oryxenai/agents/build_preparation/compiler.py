"""Pure deterministic Stage 0 scope compiler."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from oryxenai.agents.build_preparation.schemas import (
    BuildPreparationSourceRef,
    ResourceNeed,
    RouteScope,
    Stage0Result,
    StageEvent,
)
from oryxenai.agents.build_preparation.validators import (
    BuildPreparationValidationError,
    validate_stage0_result,
    validate_visual_input,
)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _event(
    event_id: str, message: str, *, level: str = "info", details: dict[str, Any] | None = None
) -> StageEvent:
    return StageEvent(
        event_id=event_id,
        stage="stage_0",
        level=level,  # type: ignore[arg-type]
        message=message,
        details=details or {},
        timestamp=datetime.now(UTC).isoformat(),
    )


def _need_id(kind: str, source_id: str) -> str:
    digest = hashlib.sha256(f"{kind}:{source_id}".encode()).hexdigest()[:20]
    return f"need-{digest}"


def _projection_hash(
    content_architect: dict[str, Any] | None,
    visual_design_director: dict[str, Any],
) -> str:
    projection = {
        "content_architect": {
            "route_plan": (content_architect or {}).get("route_plan", []),
            "page_content_packs": [
                {**pack, "internal_notes": {}}
                for pack in ((content_architect or {}).get("page_content_packs") or [])
                if isinstance(pack, dict)
            ],
            "public_content_manifest": (content_architect or {}).get("public_content_manifest", {}),
        },
        "visual_design_director": {
            "pages": visual_design_director.get("pages", []),
            "asset_briefs": visual_design_director.get("asset_briefs", []),
            "resource_candidates": visual_design_director.get("resource_candidates", []),
        },
    }
    encoded = json.dumps(projection, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_source_ref(
    content_architect: dict[str, Any] | None,
    visual_design_director: dict[str, Any],
    *,
    content_architect_session_revision: int = 0,
    visual_design_director_session_revision: int = 0,
    snapshotted_at: str = "",
) -> BuildPreparationSourceRef:
    approved_ca = (content_architect or {}).get("approved") or {}
    approved_vdd = visual_design_director.get("approved") or {}
    visual_source_ref = visual_design_director.get("source_ref") or {}
    return BuildPreparationSourceRef(
        content_architect_content_hash=str(
            approved_ca.get("content_hash", "")
            or visual_source_ref.get("content_architect_content_hash", "")
            or ""
        ),
        visual_design_director_direction_hash=str(
            approved_vdd.get("visual_direction_hash", "") or ""
        ),
        input_projection_hash=_projection_hash(content_architect, visual_design_director),
        content_architect_session_revision=(
            content_architect_session_revision
            or int(visual_source_ref.get("content_architect_session_revision", 0) or 0)
        ),
        visual_design_director_session_revision=visual_design_director_session_revision,
        snapshotted_at=snapshotted_at or datetime.now(UTC).isoformat(),
    )


def _public_route_ids(content_architect: dict[str, Any] | None) -> set[str] | None:
    if not content_architect or not content_architect.get("route_plan"):
        return None
    return {
        str(route.get("route_id"))
        for route in content_architect.get("route_plan", [])
        if isinstance(route, dict)
        and route.get("route_id")
        and route.get("publication_status", "approved") == "approved"
    }


def compile_stage0(
    content_architect: dict[str, Any] | None,
    visual_design_director: dict[str, Any],
    *,
    source_ref: BuildPreparationSourceRef | None = None,
    max_routes: int = 12,
    editorial_image_budget: int = 1,
) -> Stage0Result:
    """Compile public route scope and resource needs without I/O."""
    validate_visual_input(visual_design_director)
    pages = visual_design_director.get("pages") or []
    assets = {
        str(item["asset_id"]): item for item in (visual_design_director.get("asset_briefs") or [])
    }
    resources = {
        str(item["resource_id"]): item
        for item in (visual_design_director.get("resource_candidates") or [])
    }
    allowed_routes = _public_route_ids(content_architect)
    ca_status_by_route: dict[str, str] = {}
    if content_architect and content_architect.get("route_plan"):
        for route in content_architect.get("route_plan", []) or []:
            if isinstance(route, dict):
                route_id = str(route.get("route_id", "") or "")
                if route_id:
                    ca_status_by_route[route_id] = str(
                        route.get("publication_status", "approved") or "approved"
                    )
    public_route_count = (
        len(allowed_routes)
        if allowed_routes is not None
        else sum(
            1
            for page in pages
            if isinstance(page, dict)
            and str(page.get("publication_status", "approved") or "approved") == "approved"
            and page.get("compilable", True) is not False
        )
    )
    if public_route_count > max(1, max_routes):
        raise BuildPreparationValidationError(
            "Approved route scope exceeds the configured Build Preparation ceiling; it was not truncated.",
            details={"max_routes": max(1, max_routes)},
        )
    events = [_event("input_validated", "Validated the Visual Design Director structure.")]
    warnings: list[str] = []
    dropped_routes: list[dict[str, str]] = []
    routes: list[RouteScope] = []
    result_needs: list[ResourceNeed] = []
    asset_usage: dict[str, tuple[set[str], set[str]]] = {}
    resource_usage: dict[str, tuple[set[str], set[str]]] = {}

    for page in pages:
        route_id = str(page.get("route_id", ""))
        publication_status = str(page.get("publication_status", "approved") or "approved")
        if allowed_routes is not None and route_id not in allowed_routes:
            ca_status = ca_status_by_route.get(route_id, "approved")
            warnings.append(
                f"Excluded route '{route_id}' because Content Architect did not "
                f"approve it (route_plan publication_status='{ca_status}')."
            )
            dropped_routes.append({"route_id": route_id, "publication_status": ca_status})
            continue
        if publication_status != "approved" or page.get("compilable", True) is False:
            reason = "not approved" if publication_status != "approved" else "not compilable"
            warnings.append(
                f"Excluded route '{route_id}' because it is not public and "
                f"compilable (publication_status='{publication_status}', {reason})."
            )
            dropped_routes.append({"route_id": route_id, "publication_status": publication_status})
            continue
        scene_ids: list[str] = []
        asset_ids = [str(item) for item in (page.get("asset_briefs") or [])]
        resource_ids = [str(item) for item in (page.get("resource_candidates") or [])]
        for scene in page.get("scenes") or []:
            scene_id = str(scene.get("scene_id", ""))
            scene_ids.append(scene_id)
            asset_ids.extend(str(item) for item in (scene.get("asset_requirements") or []))
            resource_ids.extend(str(item) for item in (scene.get("resource_candidates") or []))
            for asset_id in scene.get("asset_requirements") or []:
                asset_usage.setdefault(str(asset_id), (set(), set()))[0].add(route_id)
                asset_usage[str(asset_id)][1].add(scene_id)
            for resource_id in scene.get("resource_candidates") or []:
                resource_usage.setdefault(str(resource_id), (set(), set()))[0].add(route_id)
                resource_usage[str(resource_id)][1].add(scene_id)
        for asset_id in asset_ids:
            asset_usage.setdefault(asset_id, (set(), set()))[0].add(route_id)
        for resource_id in resource_ids:
            resource_usage.setdefault(resource_id, (set(), set()))[0].add(route_id)
        routes.append(
            RouteScope(
                route_id=route_id,
                path=str(page.get("path", "") or ""),
                title=str(page.get("purpose", "") or ""),
                purpose=str(page.get("purpose", "") or ""),
                publication_status=publication_status,
                scene_ids=_unique(scene_ids),
                asset_ids=_unique(asset_ids),
                resource_ids=_unique(resource_ids),
            )
        )

    known_route_ids = {route.route_id for route in routes}
    for asset_id, asset in assets.items():
        used_route_ids, used_scene_ids = asset_usage.get(asset_id, (set(), set()))
        used_route_ids &= known_route_ids
        if not used_route_ids:
            continue
        source_policy = str(asset.get("source_policy", "") or "")
        fallback = str(asset.get("fallback_strategy", "") or "")
        if source_policy == "approved_user_media" and not fallback.strip():
            raise BuildPreparationValidationError(
                "Approved user media must declare an honest local fallback.",
                details={"asset_id": asset_id},
            )
        query_terms = _unique(
            [
                str(asset.get("subject", "") or ""),
                str(asset.get("mood", "") or ""),
                str(asset.get("aspect_ratio_need", "") or ""),
                str(asset.get("asset_type", "") or ""),
            ]
        )
        result_need = ResourceNeed(
            need_id=_need_id("asset", asset_id),
            kind="asset",
            source_id=asset_id,
            category=str(asset.get("asset_type", "") or ""),
            purpose=str(asset.get("purpose", "") or ""),
            route_ids=sorted(used_route_ids),
            scene_ids=sorted(used_scene_ids),
            source_status=str(asset.get("source_status", "") or ""),
            source_policy=source_policy,
            importance=str(asset.get("importance", "") or ""),
            required_for_handoff=(
                source_policy == "optional_external_acquisition"
                and str(asset.get("importance", "") or "") == "critical"
            ),
            query_terms=query_terms,
            fallback=fallback,
            details={
                "orientation": asset.get("orientation", ""),
                "focal_point": asset.get("focal_point", ""),
                "alt_text_intent": asset.get("alt_text_intent", ""),
            },
        )
        if not routes or used_route_ids:
            # The need is retained for a single-route harness input even when
            # the sample does not repeat the asset ID on the page object.
            pass
        else:
            continue
        result_needs.append(result_need)

    for resource_id, resource in resources.items():
        used_route_ids, used_scene_ids = resource_usage.get(resource_id, (set(), set()))
        used_route_ids &= known_route_ids
        if not used_route_ids:
            continue
        result_needs.append(
            ResourceNeed(
                need_id=_need_id("resource", resource_id),
                kind="resource",
                source_id=resource_id,
                category=str(resource.get("category", "") or ""),
                purpose=str(
                    resource.get("possible_use", "") or resource.get("where_it_may_help", "") or ""
                ),
                route_ids=sorted(used_route_ids),
                scene_ids=sorted(used_scene_ids),
                importance=str(resource.get("priority", "") or ""),
                query_terms=_unique(
                    [
                        str(resource.get("category", "") or ""),
                        str(resource.get("possible_use", "") or ""),
                        str(resource.get("why_it_matches", "") or ""),
                    ]
                ),
                fallback=str(resource.get("fallback", "") or ""),
                details={
                    "adaptation_notes": resource.get("adaptation_notes", ""),
                    "lookup_status": resource.get("lookup_status", ""),
                },
            )
        )

    # The approved default policy permits one purely editorial, non-evidentiary
    # visual.  It is intentionally introduced by Build Preparation instead of
    # pretending that a VDD catalogue pattern is an image or registry component.
    if routes and editorial_image_budget > 0:
        route = routes[0]
        source_id = "editorial-hero-image"
        result_needs.append(
            ResourceNeed(
                need_id=_need_id("asset", source_id),
                kind="asset",
                source_id=source_id,
                category="editorial_photo",
                purpose=(
                    "A high-quality abstract technical editorial visual that supports the hero "
                    "without representing a person, project screen, or production evidence."
                ),
                route_ids=[route.route_id],
                scene_ids=route.scene_ids[:1],
                source_status="build_preparation_policy",
                source_policy="decorative_non_evidentiary_attributed",
                importance="optional",
                required_for_handoff=False,
                query_terms=["abstract technology", "editorial", "connected light"],
                fallback=(
                    "Use the approved custom text-led composition with a small abstract motif "
                    "or plain tonal surface."
                ),
                details={
                    "orientation": "landscape",
                    "alt_text_intent": "Decorative abstract technology visual; omit alt text when it conveys no content.",
                    "placement": "home hero supporting visual",
                    "forbidden_subjects": [
                        "portraits",
                        "faces",
                        "screenshots",
                        "dashboards",
                        "logos",
                        "product interfaces",
                    ],
                },
            )
        )
        warnings.append(
            "Added one optional policy-approved editorial-image opportunity; provider failure "
            "must use the approved custom fallback."
        )

    events.append(
        _event(
            "scope_compiled",
            "Compiled approved route scope and structured resource needs.",
            details={
                "route_count": len(routes),
                "resource_need_count": len(result_needs),
                "dropped_routes": dropped_routes,
            },
        )
    )
    if warnings:
        events.append(
            _event(
                "scope_warnings",
                "Scope compilation completed with warnings.",
                level="warning",
                details={"warning_count": len(warnings)},
            )
        )
    events.append(_event("stage_0_complete", "Stage 0 completed without model or provider calls."))

    scope_material = {
        "routes": [route.model_dump(mode="json") for route in routes],
        "resource_needs": [need.model_dump(mode="json") for need in result_needs],
        "warnings": warnings,
    }
    scope_hash = hashlib.sha256(
        json.dumps(scope_material, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    ).hexdigest()
    result = Stage0Result(
        scope_hash=scope_hash,
        source_ref=source_ref or build_source_ref(content_architect, visual_design_director),
        routes=routes,
        resource_needs=result_needs,
        warnings=warnings,
        events=events,
    )
    return validate_stage0_result(result)
