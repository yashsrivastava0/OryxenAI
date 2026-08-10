"""Deterministic Blueprint and context compiler."""

from __future__ import annotations

import re
from typing import Any

from oryxenai.agents.content_architect.schemas import ContentArchitectState, PublicationStatus
from oryxenai.agents.visual_design_director.schemas import VisualDesignDirectorState
from oryxenai.build_preparation.fingerprints import sha256_json
from oryxenai.build_preparation.schemas import (
    ExperienceBlueprint,
    GatedRoute,
    GlobalExperienceContext,
    PageBuildPacket,
    PortfolioBuildContext,
    ResourceRequirement,
    RouteBlueprint,
    SourceRef,
)


class BlueprintCompilationError(ValueError):
    """Safe structural error; no upstream source is included in its message."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def _safe_id(value: str, fallback: str) -> str:
    candidate = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return candidate[:100] or fallback


def _as_public_content(pack: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for section in pack.sections:
        result.append(
            {
                "section_id": section.section_id,
                "purpose": section.purpose,
                "content": section.content,
                "claim_ids": section.claim_ids,
                "priority": section.priority,
                "optional": section.optional,
                "mobile_condensation": section.mobile_condensation,
                "link_targets": section.link_targets,
            }
        )
    return result


def _public_links(
    content: ContentArchitectState,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Collect approved link intent without copying private intake or notes."""
    internal: list[dict[str, Any]] = []
    external: list[dict[str, Any]] = []

    def _allowed_external(value: str) -> bool:
        return value.startswith(("http://", "https://", "mailto:"))

    for pack in content.page_content_packs:
        for section in pack.sections:
            for target in section.link_targets:
                if not isinstance(target, dict):
                    continue
                href = str(target.get("href", target.get("url", "")) or "")
                if not href:
                    continue
                if href.lower().startswith(("javascript:", "data:")):
                    raise BlueprintCompilationError(
                        "UNSAFE_LINK_REFERENCE", "A public link uses an unsafe URL scheme."
                    )
                item = {
                    "route_id": pack.route_id,
                    "section_id": section.section_id,
                    "label": str(target.get("label", "") or ""),
                    "href": href,
                    "kind": str(target.get("kind", "") or ""),
                }
                if href.startswith(("http://", "https://", "mailto:")):
                    external.append(item)
                else:
                    internal.append(item)
    manifest = content.public_content_manifest
    if isinstance(manifest, dict):
        for item in manifest.get("external_links", []):
            if isinstance(item, dict) and _allowed_external(str(item.get("url", "") or "")):
                external.append({key: item[key] for key in item if key in {"label", "url", "kind"}})
    profile = content.intake.profile
    profile_links = profile.links if hasattr(profile, "links") else profile.get("links", [])
    for link in profile_links:
        if isinstance(link, dict):
            label = str(link.get("label", "") or "")
            url = str(link.get("url", "") or "")
        else:
            label = str(getattr(link, "label", "") or "")
            url = str(getattr(link, "url", "") or "")
        if _allowed_external(url):
            external.append({"label": label, "url": url, "kind": "profile"})
    return internal, external


def compile_blueprint(
    content: ContentArchitectState,
    visual: VisualDesignDirectorState,
    *,
    source: SourceRef,
    preparation_hash: str,
    max_routes: int = 12,
    target_contract_hash: str = "",
    fixture_mode: bool = False,
) -> tuple[ExperienceBlueprint, list[PageBuildPacket], list[str]]:
    if not fixture_mode and (content.approved is None or content.status.value != "approved"):
        raise BlueprintCompilationError(
            "CONTENT_NOT_APPROVED", "Content Architect must be approved."
        )
    if not fixture_mode and (visual.approved is None or visual.status.value != "approved"):
        raise BlueprintCompilationError(
            "VISUAL_NOT_APPROVED", "Visual Design Director must be approved."
        )
    if len(content.route_plan) > max_routes:
        raise BlueprintCompilationError(
            "ROUTE_BUDGET_EXCEEDED", "Approved route count exceeds the configured budget."
        )

    routes_by_id = {route.route_id: route for route in content.route_plan if route.route_id}
    if len(routes_by_id) != len(content.route_plan):
        raise BlueprintCompilationError("DUPLICATE_ROUTE_ID", "Approved route IDs must be unique.")
    paths = [route.path for route in content.route_plan]
    if len(set(paths)) != len(paths):
        raise BlueprintCompilationError(
            "DUPLICATE_ROUTE_PATH", "Approved route paths must be unique."
        )

    packs_by_route = {pack.route_id: pack for pack in content.page_content_packs if pack.route_id}
    pages_by_route = {page.route_id: page for page in visual.pages if page.route_id}
    if set(packs_by_route) - set(routes_by_id) or set(pages_by_route) - set(routes_by_id):
        raise BlueprintCompilationError(
            "UNKNOWN_ROUTE_REFERENCE", "An upstream page references an unknown route."
        )
    valid_nav_targets = set(routes_by_id)
    valid_nav_targets.update(
        section.section_id
        for pack in content.page_content_packs
        for section in pack.sections
        if section.section_id
    )
    public_manifest = content.public_content_manifest
    if isinstance(public_manifest, dict):
        for item in public_manifest.get("nav", []):
            if not isinstance(item, dict):
                continue
            target = str(item.get("target", "") or "").lstrip("#")
            if (
                target
                and target not in valid_nav_targets
                and not target.startswith(("/", "http://", "https://", "mailto:"))
            ):
                raise BlueprintCompilationError(
                    "NAVIGATION_REFERENCE_INVALID",
                    "Public navigation references an unknown route or section.",
                )

    claims = {claim.claim_id: claim for claim in content.claim_grounding if claim.claim_id}
    source_entities = {
        claim.source_entity_id for claim in content.claim_grounding if claim.source_entity_id
    }
    assets = {asset.asset_id: asset for asset in visual.asset_briefs if asset.asset_id}
    candidates = {
        resource.resource_id: resource
        for resource in visual.resource_candidates
        if resource.resource_id
    }
    warnings: list[str] = []
    if fixture_mode:
        warnings.append(
            "fixture mode: this package is for preparation testing only and is not publishable"
        )
        if content.approved is None or content.status.value != "approved":
            warnings.append("fixture content was derived from embedded Visual Design intake")
        if visual.approved is None or visual.status.value != "approved":
            warnings.append(
                "fixture Visual Design output is not approval-stamped; production preparation remains blocked"
            )
    requirements: list[ResourceRequirement] = []
    packets: list[PageBuildPacket] = []
    route_blueprints: list[RouteBlueprint] = []
    gated: list[dict[str, Any]] = []
    link_graph, external_links = _public_links(content)

    for route in content.route_plan:
        page = pages_by_route.get(route.route_id)
        pack = packs_by_route.get(route.route_id)
        if route.publication_status is not PublicationStatus.APPROVED:
            gated.append(
                {
                    "route_id": route.route_id,
                    "publication_status": route.publication_status.value,
                    "path": route.path if route.path.startswith("/") else "",
                    "reason": "route is not publication-approved",
                }
            )
            continue
        if page is None or pack is None:
            raise BlueprintCompilationError(
                "ROUTE_COVERAGE_MISSING",
                "An approved route lacks a complete page and content pack.",
            )
        if page.publication_status.value != "approved":
            gated.append(
                {
                    "route_id": route.route_id,
                    "publication_status": page.publication_status.value,
                    "path": route.path if route.path.startswith("/") else "",
                    "reason": "visual direction is not publication-approved",
                }
            )
            continue
        if not page.compilable:
            raise BlueprintCompilationError(
                "ROUTE_NOT_COMPILABLE", "An approved route is marked non-compilable."
            )
        if page.path and page.path != route.path:
            raise BlueprintCompilationError(
                "ROUTE_PATH_MISMATCH", "Content and Visual route paths differ."
            )

        section_ids = {section.section_id for section in pack.sections if section.section_id}
        for asset_id in page.asset_briefs:
            if asset_id not in assets:
                raise BlueprintCompilationError(
                    "ASSET_REFERENCE_INVALID", "A page references an unknown asset brief."
                )
            asset = assets[asset_id]
            if asset.content_ref and not (
                asset.content_ref in section_ids
                or asset.content_ref in claims
                or asset.content_ref in source_entities
            ):
                raise BlueprintCompilationError(
                    "ASSET_CONTENT_REFERENCE_INVALID",
                    "An asset brief references an unknown public content item.",
                )
        for resource_id in page.resource_candidates:
            if resource_id not in candidates:
                warnings.append(
                    f"resource hint '{resource_id}' is not in the current catalogue; custom implementation may be needed"
                )

        for section_id in route.section_sequence:
            if section_id not in section_ids:
                raise BlueprintCompilationError(
                    "SECTION_REFERENCE_INVALID",
                    "Route section sequence contains an unknown section.",
                )
        for section in pack.sections:
            for claim_id in section.claim_ids:
                claim = claims.get(claim_id)
                if claim is None:
                    if fixture_mode:
                        warnings.append(
                            f"fixture section {section.section_id} references claim {claim_id} without Content Architect grounding"
                        )
                        continue
                    raise BlueprintCompilationError(
                        "CLAIM_REFERENCE_INVALID", "A public section references an unknown claim."
                    )
                if claim.publication_status is not PublicationStatus.APPROVED:
                    if fixture_mode:
                        warnings.append(
                            f"fixture claim {claim_id} is not approval-grounded for publication"
                        )
                        continue
                    raise BlueprintCompilationError(
                        "CLAIM_NOT_PUBLISHABLE", "A public section references a non-public claim."
                    )

        scene_ids: list[str] = []
        packet_scenes: list[dict[str, Any]] = []
        selected_assets: list[str] = []
        selected_resources: list[str] = []
        adaptation: list[str] = []
        for resource_id in page.resource_candidates:
            if resource_id in candidates:
                selected_resources.append(resource_id)
                requirement_id = f"resource-{_safe_id(route.route_id, 'route')}-{_safe_id(resource_id, 'resource')}"
                requirements.append(
                    ResourceRequirement(
                        requirement_id=requirement_id,
                        kind="component_or_effect",
                        scope="route",
                        route_id=route.route_id,
                        intent=candidates[resource_id].why_it_matches
                        or candidates[resource_id].possible_use,
                        source_refs=[resource_id],
                        constraints={"category": candidates[resource_id].category},
                        fallback=candidates[resource_id].fallback,
                    )
                )
        for scene in page.scenes:
            if scene.route_id != route.route_id:
                raise BlueprintCompilationError(
                    "SCENE_ROUTE_MISMATCH", "A scene belongs to another route."
                )
            if scene.scene_id in scene_ids:
                raise BlueprintCompilationError(
                    "DUPLICATE_SCENE_ID", "Scene IDs must be unique within a route."
                )
            scene_ids.append(scene.scene_id)
            for ref in scene.content_refs:
                if ref not in section_ids and ref not in claims:
                    raise BlueprintCompilationError(
                        "SCENE_CONTENT_REFERENCE_INVALID",
                        "A scene references an unknown public content item.",
                    )
                if (
                    ref in claims
                    and claims[ref].publication_status is not PublicationStatus.APPROVED
                ):
                    raise BlueprintCompilationError(
                        "CLAIM_NOT_PUBLISHABLE",
                        "A scene references a non-public claim.",
                    )
            for asset_id in scene.asset_requirements:
                if asset_id not in assets:
                    raise BlueprintCompilationError(
                        "ASSET_REFERENCE_INVALID", "A scene references an unknown asset brief."
                    )
                selected_assets.append(asset_id)
                asset = assets[asset_id]
                if asset.content_ref and not (
                    asset.content_ref in section_ids
                    or asset.content_ref in claims
                    or asset.content_ref in source_entities
                ):
                    raise BlueprintCompilationError(
                        "ASSET_CONTENT_REFERENCE_INVALID",
                        "An asset brief references an unknown public content item.",
                    )
                requirement_id = f"asset-{_safe_id(route.route_id, 'route')}-{_safe_id(scene.scene_id, 'scene')}-{_safe_id(asset_id, 'asset')}"
                requirements.append(
                    ResourceRequirement(
                        requirement_id=requirement_id,
                        kind="image"
                        if asset.asset_type.lower() in {"image", "photo", "illustration"}
                        else "visual_asset",
                        scope="scene",
                        route_id=route.route_id,
                        scene_id=scene.scene_id,
                        intent=asset.purpose or asset.subject,
                        source_refs=[asset_id, asset.content_ref],
                        constraints=asset.model_dump(mode="json"),
                        fallback=asset.fallback_strategy,
                    )
                )
            for resource_id in scene.resource_candidates:
                if resource_id not in candidates:
                    warnings.append(
                        f"resource hint '{resource_id}' is not in the current catalogue; custom implementation may be needed"
                    )
                    adaptation.append(f"resolve or replace resource hint {resource_id}")
                else:
                    selected_resources.append(resource_id)
                    requirement_id = f"resource-{_safe_id(route.route_id, 'route')}-{_safe_id(scene.scene_id, 'scene')}-{_safe_id(resource_id, 'resource')}"
                    requirements.append(
                        ResourceRequirement(
                            requirement_id=requirement_id,
                            kind="component_or_effect",
                            scope="scene",
                            route_id=route.route_id,
                            scene_id=scene.scene_id,
                            intent=candidates[resource_id].why_it_matches
                            or candidates[resource_id].possible_use,
                            source_refs=[resource_id],
                            constraints={"category": candidates[resource_id].category},
                            fallback=candidates[resource_id].fallback,
                        )
                    )
            packet_scenes.append(scene.model_dump(mode="json"))

        packet_id = f"page-{_safe_id(route.route_id, 'route')}"
        packet = PageBuildPacket(
            packet_id=packet_id,
            route_id=route.route_id,
            path=route.path,
            purpose=route.purpose,
            audience_takeaway=route.audience_takeaway,
            public_copy=_as_public_content(pack),
            public_entities=[
                {
                    "entity_id": claim.source_entity_id,
                    "claim_id": claim.claim_id,
                    "statement": claim.statement,
                }
                for section in pack.sections
                for claim_id in section.claim_ids
                if (claim := claims.get(claim_id)) is not None
                and claim.source_entity_id
                and claim.publication_status is PublicationStatus.APPROVED
            ],
            section_sequence=list(route.section_sequence),
            scene_sequence=scene_ids,
            scenes=packet_scenes,
            layout_intent={
                "storyboard": page.storyboard,
                "section_rhythm": page.section_rhythm,
                "primary_emphasis": page.primary_emphasis,
                "secondary_emphasis": page.secondary_emphasis,
            },
            responsive_transformations={
                "summary": page.responsive_summary,
                "route_mobile_notes": route.mobile_notes,
            },
            mobile_simplifications=[route.mobile_notes] if route.mobile_notes else [],
            touch_behavior={"main": page.main_interaction_moment},
            layer_behavior={"background_evolution": page.background_evolution},
            selected_resources=sorted(set(selected_resources)),
            selected_assets=sorted(set(selected_assets)),
            adaptation_intent=adaptation,
            motion_behavior={"global": visual.motion_system, "route": page.main_interaction_moment},
            reduced_motion_fallback="disable non-load-bearing motion and use the static scene end state",
            interaction_states={
                "navigation": page.navigation_behavior,
                "main": page.main_interaction_moment,
            },
            links=[item for item in link_graph if item.get("route_id") == route.route_id],
            custom_implementation_opportunities=[{"reason": item} for item in adaptation],
            acceptance_criteria=list(page.acceptance_criteria),
            failure_safe_static_states=[
                scene.failure_safe_static_state
                for scene in page.scenes
                if scene.failure_safe_static_state
            ]
            or ["render the approved content in a static layout"],
        )
        packet.packet_hash = sha256_json(packet.model_dump(mode="json"))
        packets.append(packet)
        route_blueprints.append(
            RouteBlueprint(
                route_id=route.route_id,
                path=route.path,
                title=route.title,
                purpose=route.purpose,
                audience_takeaway=route.audience_takeaway,
                priority=route.priority,
                content_density=route.content_density,
                publication_status=route.publication_status.value,
                section_sequence=list(route.section_sequence),
                scenes=scene_ids,
                packet_id=packet_id,
                acceptance_criteria=list(page.acceptance_criteria),
            )
        )

    strategy = content.site_story_strategy
    identity = content.intake.profile if isinstance(content.intake.profile, dict) else {}
    blueprint = ExperienceBlueprint(
        blueprint_id=f"blueprint-{preparation_hash[:16]}",
        source_ref=source,
        preparation_input_hash=preparation_hash,
        presentation_mode=str(strategy.get("presentation_mode", "") or ""),
        public_identity={
            "name": identity.get("name", ""),
            "title": identity.get("current_title", ""),
        },
        portfolio_goal=str(strategy.get("primary_goal", strategy.get("goal", "")) or ""),
        audience=str(strategy.get("primary_audience", strategy.get("audience", "")) or ""),
        desired_visitor_action=str(strategy.get("primary_action", "") or ""),
        narrative_thesis=str(strategy.get("narrative_thesis", "") or ""),
        route_map=route_blueprints,
        routes=route_blueprints,
        navigation={"items": content.public_content_manifest.get("nav", [])}
        if isinstance(content.public_content_manifest, dict)
        else {},
        link_graph=link_graph,
        external_links=external_links,
        visual_language=visual.visual_language,
        shared_visual_systems=visual.shared_visual_systems,
        navigation_direction=visual.navigation_direction,
        motion_system=visual.motion_system,
        interaction_system=visual.interaction_system,
        accessibility_and_performance=visual.accessibility_and_performance,
        responsive_philosophy={"routes": [page.responsive_summary for page in visual.pages]},
        fixed_constraints={"target_contract_hash": target_contract_hash},
        must_preserve=list(visual.must_preserve),
        must_not_fabricate=list(visual.must_not_fabricate),
        acceptance_criteria=[
            criterion for page in visual.pages for criterion in page.acceptance_criteria
        ],
        gated_routes=[
            GatedRoute(
                route_id=item["route_id"],
                publication_status=item["publication_status"],
                path=item["path"],
                reason=item["reason"],
            )
            for item in gated
        ],
        resource_requirements=requirements,
        custom_implementation_opportunities=[{"reason": warning} for warning in warnings],
        warnings=warnings,
    )
    hash_payload = blueprint.model_dump(mode="json", exclude={"blueprint_hash"})
    if isinstance(hash_payload.get("source_ref"), dict):
        hash_payload["source_ref"].pop("captured_at", None)
    blueprint.blueprint_hash = sha256_json(hash_payload)
    return blueprint, packets, warnings


def compile_context(
    blueprint: ExperienceBlueprint,
    packets: list[PageBuildPacket],
    manifest: Any,
    *,
    target_contract: dict[str, Any] | None = None,
) -> PortfolioBuildContext:
    strategy = blueprint.visual_language

    def _dict_or_note(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {"intent": value} if value else {}

    global_context = GlobalExperienceContext(
        public_identity=blueprint.public_identity,
        portfolio_goal=blueprint.portfolio_goal,
        audience=blueprint.audience,
        desired_visitor_action=blueprint.desired_visitor_action,
        narrative_thesis=blueprint.narrative_thesis,
        presentation_mode=blueprint.presentation_mode,
        route_graph=[route.model_dump(mode="json") for route in blueprint.route_map],
        navigation=blueprint.navigation,
        visual_language=strategy,
        shared_visual_systems=blueprint.shared_visual_systems,
        typography=_dict_or_note(
            strategy.get("typography", {}) if isinstance(strategy, dict) else {}
        ),
        color_surface_system=_dict_or_note(
            strategy.get("color_behavior", {}) if isinstance(strategy, dict) else {}
        ),
        grid_spacing_character=blueprint.shared_visual_systems,
        motion_system=blueprint.motion_system,
        interaction_system=blueprint.interaction_system,
        responsive_philosophy=blueprint.responsive_philosophy,
        accessibility=blueprint.accessibility_and_performance,
        reduced_motion_policy="non-load-bearing motion must have a static end state",
        performance_expectations=blueprint.accessibility_and_performance,
        shared_resources=[
            entry.manifest_resource_id
            for entry in manifest.entries
            if any(item.get("scope") == "shared" for item in entry.usages)
        ],
        fixed_dependencies=target_contract or {},
        security_deployment_constraints={
            "no_provider_network_access_at_codegen": True,
            "no_package_install_at_generation": True,
        },
        must_preserve=blueprint.must_preserve,
        must_not_fabricate=blueprint.must_not_fabricate,
    )
    packet_index = [
        {
            "route_id": packet.route_id,
            "path": packet.path,
            "packet_id": packet.packet_id,
            "packet_hash": packet.packet_hash,
        }
        for packet in packets
    ]
    context = PortfolioBuildContext(
        blueprint_hash=blueprint.blueprint_hash,
        manifest_hash=manifest.manifest_hash,
        global_context=global_context,
        page_packets=packet_index,
        packet_hashes={packet.packet_id: packet.packet_hash for packet in packets},
    )
    context.context_hash = sha256_json(context.model_dump(mode="json", exclude={"context_hash"}))
    return context
