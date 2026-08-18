"""Pure deterministic Stage 0 scope compiler."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from oryxenai.agents.build_preparation.schemas import (
    BuildPreparationSourceRef,
    ComponentIntent,
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
from oryxenai.agents.build_preparation.visual_input import (
    component_provider_terms,
    normalize_visual_input,
)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _component_intent(
    resource: dict[str, Any], *, route_id: str, scene_ids: list[str], section_ids: list[str]
) -> ComponentIntent | None:
    category = str(resource.get("category", "") or "").casefold()
    if category not in {"component", "visual_component", "registry_component"}:
        return None
    raw = resource.get("component_intent")
    if isinstance(raw, dict):
        try:
            return ComponentIntent.model_validate(raw)
        except ValueError:
            pass
    role_id = str(resource.get("interaction_role", "") or resource.get("resource_id", ""))
    terms = [str(item) for item in resource.get("provider_terms", []) or [] if str(item).strip()]
    terms = _unique([*terms, *component_provider_terms(role_id)])
    section_id = str(section_ids[0] if section_ids else resource.get("section_id", "") or "")
    scene_id = str(scene_ids[0] if scene_ids else resource.get("scene_id", "") or "")
    return ComponentIntent(
        role_id=role_id,
        route_id=route_id,
        scene_id=scene_id,
        section_id=section_id,
        interaction_class=str(resource.get("interaction_class", "") or role_id),
        interaction_outcome=str(
            resource.get("interaction_outcome", "")
            or resource.get("possible_use", "")
            or resource.get("why_it_matches", "")
        ),
        placement=str(resource.get("where_it_may_help", "") or resource.get("placement", "")),
        purpose=str(resource.get("possible_use", "") or resource.get("purpose", "")),
        provider_terms=terms,
        negative_concepts=[
            str(item) for item in resource.get("negative_concepts", []) or [] if str(item).strip()
        ],
        required=bool(resource.get("required_for_handoff", False)),
        fallback_type="semantic_local",
        responsive_behavior=str(resource.get("responsive_behavior", "") or ""),
        reduced_motion_behavior=str(resource.get("reduced_motion_behavior", "") or ""),
        expected_exports=[
            str(item) for item in resource.get("expected_exports", []) or [] if str(item).strip()
        ],
        prohibitions=[
            str(item) for item in resource.get("prohibitions", []) or [] if str(item).strip()
        ],
    )


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
            "visual_language": visual_design_director.get("visual_language", {}),
            "resource_policy": visual_design_director.get("resource_policy", {}),
            "visual_input_mode": visual_design_director.get("visual_input_mode", ""),
            "assumption_hash": visual_design_director.get("assumption_hash", ""),
            "assumptions": visual_design_director.get("assumptions", []),
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
    visual_input_mode = str(
        visual_design_director.get("visual_input_mode", "")
        or ("approved_vdd" if approved_vdd.get("visual_direction_hash") else "assumed_from_content")
    )
    assumption_hash = str(visual_design_director.get("assumption_hash", "") or "")
    assumptions = [
        str(item)
        for item in visual_design_director.get("assumptions", []) or []
        if str(item).strip()
    ]
    producer_provenance_hash = hashlib.sha256(
        json.dumps(
            {
                "content_architect_content_hash": str(
                    approved_ca.get("content_hash", "")
                    or visual_source_ref.get("content_architect_content_hash", "")
                    or ""
                ),
                "visual_design_director_direction_hash": str(
                    approved_vdd.get("visual_direction_hash", "") or ""
                ),
                "assumption_hash": assumption_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
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
        visual_input_mode=visual_input_mode,  # type: ignore[arg-type]
        assumption_hash=assumption_hash,
        assumptions=assumptions,
        producer_provenance_hash=producer_provenance_hash,
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


def _public_routes_by_id(content_architect: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not content_architect:
        return {}
    return {
        str(route.get("route_id", "") or ""): route
        for route in content_architect.get("route_plan", []) or []
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
    editorial_image_budget: int = 5,
    visual_component_budget: int = 4,
    editorial_image_maximum: int = 6,
    visual_component_maximum: int = 6,
    auto_derive_visual_resources: bool = True,
) -> Stage0Result:
    """Compile public route scope and resource needs without I/O."""
    normalized = normalize_visual_input(
        content_architect,
        visual_design_director,
        image_target=editorial_image_budget,
        image_maximum=editorial_image_maximum,
        component_target=visual_component_budget,
        component_maximum=visual_component_maximum,
        enabled=auto_derive_visual_resources,
    )
    visual_design_director = normalized.visual
    visual_policy = visual_design_director.get("resource_policy")
    if not isinstance(visual_policy, dict):
        visual_policy = {}
    editorial_image_budget = int(
        visual_policy.get("image_target_count", editorial_image_budget) or 0
    )
    visual_component_budget = int(
        visual_policy.get("component_target_count", visual_component_budget) or 0
    )
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
    canonical_routes = _public_routes_by_id(content_architect)
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
        canonical_route = canonical_routes.get(route_id, {})
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
                path=str(canonical_route.get("path", page.get("path", "")) or ""),
                title=str(
                    canonical_route.get(
                        "title", canonical_route.get("purpose", page.get("purpose", ""))
                    )
                    or ""
                ),
                purpose=str(canonical_route.get("purpose", page.get("purpose", "")) or ""),
                publication_status=publication_status,
                section_ids=[
                    str(item)
                    for item in canonical_route.get("section_sequence", []) or []
                    if str(item)
                ],
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
                str(asset.get("composition_role", "") or ""),
            ]
        )
        asset_type = str(asset.get("asset_type", "") or "")
        is_component_role = asset_type.casefold() in {
            "component",
            "visual_component",
            "registry_component",
        }
        is_image_role = asset_type.casefold() in {
            "image",
            "photo",
            "editorial_photo",
            "portrait",
        }
        result_need = ResourceNeed(
            need_id=_need_id("asset", asset_id),
            kind="resource" if is_component_role else "asset",
            source_id=asset_id,
            category="visual_component" if is_component_role else asset_type,
            purpose=str(asset.get("purpose", "") or ""),
            route_ids=sorted(used_route_ids),
            scene_ids=sorted(used_scene_ids),
            section_ids=_unique(
                [
                    str(asset.get("section_id", "") or ""),
                    *[str(item) for item in asset.get("section_ids", []) or []],
                ]
            ),
            source_status=str(asset.get("source_status", "") or ""),
            source_policy=source_policy,
            importance=str(asset.get("importance", "") or ""),
            required_for_handoff=is_component_role or is_image_role,
            query_terms=query_terms,
            fallback=fallback,
            details={
                "orientation": asset.get("orientation", ""),
                "focal_point": asset.get("focal_point", ""),
                "alt_text_intent": asset.get("alt_text_intent", ""),
                "expected_exports": asset.get("expected_exports", []),
                "placement": asset.get("placement", "") or asset.get("composition_role", ""),
                "style_mood": asset.get("mood", ""),
                "theme_colors": [
                    str(item) for item in asset.get("theme_colors", []) or [] if str(item).strip()
                ],
                "negative_concepts": [
                    str(item)
                    for item in asset.get("negative_concepts", []) or []
                    if str(item).strip()
                ],
                "aspect_ratio": asset.get("aspect_ratio_need", ""),
                "minimum_width": int(asset.get("minimum_width", 0) or 0),
                "minimum_height": int(asset.get("minimum_height", 0) or 0),
                "responsive_behavior": asset.get("mobile_treatment", ""),
                "reduced_motion_behavior": "Render the complete image treatment statically.",
                "provider_terms": [
                    str(item) for item in asset.get("provider_terms", []) or [] if str(item).strip()
                ],
                "interaction_class": str(asset.get("interaction_class", "") or ""),
                "interaction_outcome": str(asset.get("interaction_outcome", "") or ""),
            },
        )
        if is_component_role:
            result_need = result_need.model_copy(
                update={
                    "component_intent": _component_intent(
                        asset,
                        route_id=sorted(used_route_ids)[0] if used_route_ids else "",
                        scene_ids=sorted(used_scene_ids),
                        section_ids=result_need.section_ids,
                    )
                }
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
        component_intent = _component_intent(
            resource,
            route_id=sorted(used_route_ids)[0] if used_route_ids else "",
            scene_ids=sorted(used_scene_ids),
            section_ids=_unique(
                [
                    str(resource.get("section_id", "") or ""),
                    *[str(item) for item in resource.get("section_ids", []) or []],
                ]
            ),
        )
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
                section_ids=_unique(
                    [
                        str(resource.get("section_id", "") or ""),
                        *[str(item) for item in resource.get("section_ids", []) or []],
                    ]
                ),
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
                    "placement": resource.get("where_it_may_help", ""),
                    "interaction_role": resource.get("interaction_role", ""),
                    "responsive_behavior": resource.get("responsive_behavior", ""),
                    "reduced_motion_behavior": resource.get("reduced_motion_behavior", ""),
                    "required_for_handoff": resource.get("required_for_handoff"),
                    "provider_terms": [
                        str(item)
                        for item in resource.get("provider_terms", []) or []
                        if str(item).strip()
                    ],
                    "negative_concepts": [
                        str(item)
                        for item in resource.get("negative_concepts", []) or []
                        if str(item).strip()
                    ],
                    "interaction_class": str(resource.get("interaction_class", "") or ""),
                    "interaction_outcome": str(resource.get("interaction_outcome", "") or ""),
                },
                required_for_handoff=(
                    bool(resource["required_for_handoff"])
                    if isinstance(resource.get("required_for_handoff"), bool)
                    else str(resource.get("category", "") or "").casefold()
                    in {"visual_component", "component", "registry_component"}
                ),
                component_intent=component_intent,
            )
        )

    image_need_count = sum(
        1
        for need in result_needs
        if need.category.casefold() in {"image", "photo", "editorial_photo", "portrait"}
    )
    component_need_count = sum(
        1
        for need in result_needs
        if need.category.casefold() in {"visual_component", "component", "registry_component"}
    )
    if routes and editorial_image_budget > image_need_count:
        warnings.append(
            f"Approved Visual Design Director output contains {image_need_count} image roles; "
            f"the configured image target is {editorial_image_budget}. The target is advisory; "
            "no image roles are manufactured and no quota gap is created."
        )
    if routes and visual_component_budget > component_need_count:
        warnings.append(
            f"Approved Visual Design Director output contains {component_need_count} component roles; "
            f"the configured component target is {visual_component_budget}. The target is advisory; "
            "no component roles are manufactured and no quota gap is created."
        )

    # Typography is executable material too: give the downstream generator a
    # real, locally vendorable Fontsource candidate whenever the provider is
    # available, with the deterministic recipe remaining the explicit fallback.
    if routes and (
        visual_design_director.get("visual_language")
        or visual_design_director.get("typography")
        or visual_design_director.get("global_visual_language")
    ):
        result_needs.append(
            ResourceNeed(
                need_id=_need_id("resource", "typography-font"),
                kind="resource",
                source_id="typography-font",
                category="font",
                purpose="A distinctive display/body font family for the approved visual language, vendored locally with Latin glyph coverage.",
                route_ids=[route.route_id for route in routes],
                scene_ids=[],
                source_status="needs_acquisition",
                source_policy="optional_external_acquisition",
                importance="important",
                required_for_handoff=True,
                query_terms=["space grotesk", "manrope", "technical sans"],
                fallback="Use the typed local system font recipe with the declared weights.",
                details={
                    "font_profile": "editorial_technical",
                    "weights": ["400", "500", "600", "700"],
                    "subsets": ["latin"],
                },
            )
        )

    events.append(
        _event(
            "scope_compiled",
            "Compiled approved route scope and structured resource needs.",
            details={
                "route_count": len(routes),
                "resource_need_count": len(result_needs),
                "dropped_routes": dropped_routes,
                "visual_input_mode": normalized.mode,
                "assumption_hash": normalized.assumption_hash,
                "assumptions": list(normalized.assumptions),
                "resource_targets": {
                    "image_target": editorial_image_budget,
                    "component_target": visual_component_budget,
                },
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
        visual_input_mode=normalized.mode,  # type: ignore[arg-type]
        assumption_hash=normalized.assumption_hash,
        assumptions=list(normalized.assumptions),
        resource_targets={
            "image_target": min(
                max(0, editorial_image_budget), min(6, max(0, editorial_image_maximum))
            ),
            "component_target": min(
                max(0, visual_component_budget), min(6, max(0, visual_component_maximum))
            ),
        },
        routes=routes,
        resource_needs=result_needs,
        warnings=warnings,
        events=events,
    )
    return validate_stage0_result(result)
