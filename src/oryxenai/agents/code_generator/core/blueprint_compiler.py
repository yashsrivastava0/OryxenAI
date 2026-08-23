"""Compile the provider-safe v4 blueprint into the legacy internal plan domain."""

from __future__ import annotations

from typing import Any

from oryxenai.agents.code_generator.core.content_compiler import content_ids_by_section
from oryxenai.agents.code_generator.core.development_schemas import (
    AcceptanceCoverageItem,
    CreativeThesis,
    ExperienceBlueprintV4,
    InteractionContract,
    ResourceInventoryItem,
    ResourceSlot,
    ResponsiveBehavior,
    RouteComposition,
    RoutePlan,
    SharedComponentContract,
    ShellContract,
    SitePlan,
    VisualSystem,
    WorkGraph,
)
from oryxenai.agents.code_generator.core.path_policy import semantic_segment
from oryxenai.agents.code_generator.core.source_manifest import digest
from oryxenai.agents.code_generator.core.work_graph_compiler import (
    compile_execution_bindings,
    compile_site_plan,
)


def compile_blueprint_site_plan(
    blueprint: ExperienceBlueprintV4,
    projections: dict[str, dict[str, Any]],
    *,
    max_sections_per_unit: int,
) -> SitePlan:
    """Compile route/content/criterion/resource ownership without model-authored paths."""

    site = projections["site/contract.json"]
    routes = [item for item in site.get("routes", []) if isinstance(item, dict)]
    public_content = [item for item in site.get("public_content", []) if isinstance(item, dict)]
    content_by_route = {str(item.get("route_id", "")): item for item in public_content}
    content_keys = content_ids_by_section(
        public_content,
        [item for item in site.get("facts", []) if isinstance(item, dict)],
    )
    shells = {item.route_id: item for item in blueprint.route_shells}
    moves_by_route = {
        route_id: [item for item in blueprint.distinctive_moves if item.route_id == route_id]
        for route_id in shells
    }
    criteria = [item for item in site.get("criteria", []) if isinstance(item, dict)]
    bindings = compile_execution_bindings(projections)

    route_plans: list[RoutePlan] = []
    for route in routes:
        route_id = str(route.get("route_id", ""))
        shell = shells.get(route_id)
        if shell is None:
            raise ValueError("v4 blueprint is missing an admitted route shell")
        sections = shell.section_order
        route_content = content_by_route.get(route_id, {})
        fact_ids = sorted(
            {
                str(fact_id)
                for section in route_content.get("sections", [])
                if isinstance(section, dict)
                for fact_id in section.get("claim_ids", [])
                if str(fact_id)
            }
        )
        route_criteria = [
            str(item.get("criterion_id", ""))
            for item in criteria
            if str(item.get("route_id", "")) in {"", route_id} and str(item.get("criterion_id", ""))
        ]
        route_moves = moves_by_route.get(route_id, [])
        regions = [item for item in blueprint.section_regions if item.route_id == route_id]
        route_interactions = [
            item for item in blueprint.interaction_assignments if item.route_id == route_id
        ]
        route_resources = [
            item for item in blueprint.resource_placements if item.route_id == route_id
        ]
        route_motion = [item for item in blueprint.motion_beats if item.route_id == route_id]
        route_plans.append(
            RoutePlan(
                route_id=route_id,
                path=str(route.get("path", "")),
                storage_key=semantic_segment(
                    _storage_key(str(route.get("storage_key") or route_id))
                ),
                section_ids=list(sections),
                section_order=list(sections),
                content_bindings=[
                    content_id
                    for section_id in sections
                    for content_id in content_keys.get((route_id, section_id), [])
                ],
                fact_ids=fact_ids,
                criterion_ids=route_criteria,
                responsive_outcome=_responsive_outcome(regions),
                reduced_motion_outcome=(
                    "Every declared motion beat has a static visible replacement."
                    if route_motion
                    else "The route is complete and visible without motion."
                ),
                interaction_outcome=(
                    "Every approved interaction has selector-bound keyboard and state evidence."
                    if route_interactions
                    else "Native navigation and focus behavior remain available."
                ),
                purpose=str(route.get("purpose", "")),
                composition=RouteComposition(
                    hierarchy=blueprint.narrative_arc,
                    layout_strategy="; ".join(
                        f"{item.implementation_kind}:{item.relationship}" for item in route_moves
                    ),
                    visual_anchor="; ".join(item.thesis for item in route_moves),
                    evidence_treatment="Approved content keys remain compiler-owned.",
                    section_transitions="; ".join(
                        f"{item.section_id}:{item.gap.value:g}{item.gap.unit}" for item in regions
                    ),
                    avoid=list(blueprint.anti_patterns),
                ),
                responsive_behavior=ResponsiveBehavior(
                    mobile_strategy=_viewport_strategy(regions, "mobile"),
                    breakpoint_strategy=_viewport_strategy(regions, "tablet"),
                    overflow_strategy="Exact region width, measure, and overlap bounds apply.",
                    touch_target_strategy="Trusted runtime verification enforces configured targets.",
                ),
                interaction_ids=[item.interaction_id for item in route_interactions],
                planned_resource_slots=[item.resource_slot_id for item in route_resources],
            )
        )

    interactions = [
        InteractionContract(
            interaction_id=item.interaction_id,
            route_id=item.route_id,
            trigger=item.trigger,
            outcome=item.state_transition,
            keyboard_behavior=item.keyboard_behavior,
            reduced_motion_behavior="Interaction state is available without motion.",
            target=item.target_selector,
            expected_url=item.expected_navigation,
            accessible_name=item.literal_marker,
        )
        for item in blueprint.interaction_assignments
    ]
    resource_inventory = [
        ResourceInventoryItem(
            resource_id=item.resource_slot_id,
            route_id=item.route_id,
            purpose=item.purpose,
            disposition=(
                "bound"
                if item.resolution_type in {"local_materialized", "target_package_binding"}
                else "fallback"
                if item.fallback_behavior
                else "slot"
            ),
            local_reference=item.local_paths[0] if item.local_paths else item.package_name,
            fallback=item.fallback_behavior,
        )
        for item in bindings
    ]
    shared_components = [
        SharedComponentContract(
            component_id=f"resource:{item.resource_slot_id}",
            purpose=item.purpose or "Execute an admitted component binding.",
            visual_role=item.category,
            expected_exports=list(item.expected_exports),
            accessibility_contract="Preserve the admitted accessibility and reduced-motion contract.",
        )
        for item in bindings
        if "component" in item.category.casefold() and item.expected_exports
    ]
    if not shared_components:
        shared_components.append(
            SharedComponentContract(
                component_id="trusted-route-shell",
                purpose="Own navigation, main, skip link, error boundary, and preview bridge.",
                visual_role="semantic route frame without portfolio styling authority",
                expected_exports=["RouteShell"],
                accessibility_contract="Exactly one main landmark and visible keyboard focus.",
            )
        )
    plan = SitePlan(
        plan_id=f"plan-v4-{digest(blueprint.model_dump(mode='json'))[:20]}",
        routes=route_plans,
        shared_systems=["RouteShell", "LocalImage", "approved-content-module"],
        resource_slots=[
            ResourceSlot(
                slot_id=item.resource_slot_id, route_id=item.route_id, purpose=item.purpose
            )
            for item in bindings
        ],
        work_graph=WorkGraph(units=[]),
        creative_thesis=CreativeThesis(
            thesis=blueprint.narrative_arc,
            distinction="; ".join(item.thesis for item in blueprint.distinctive_moves),
            narrative_arc=blueprint.narrative_arc,
            visual_tension="; ".join(
                f"{item.relationship}:{item.minimum_ratio:g}-{item.maximum_ratio:g}"
                for item in blueprint.distinctive_moves
            ),
            avoid=list(blueprint.anti_patterns),
        ),
        visual_system=VisualSystem(
            typography="; ".join(
                f"{item.role}:{item.family}:{','.join(str(weight) for weight in item.weights)}"
                for item in blueprint.tokens.typography_roles
            ),
            color_strategy="; ".join(item.name for item in blueprint.tokens.colors),
            spacing_rhythm="; ".join(item.name for item in blueprint.tokens.spacing),
            surface_treatment="; ".join(
                [item.name for item in blueprint.tokens.borders]
                + [item.name for item in blueprint.tokens.shadows]
            )
            or "tokenized flat surfaces",
            density_strategy="; ".join(item.name for item in blueprint.tokens.containers),
            motion_vocabulary="; ".join(
                f"{item.trigger}:{','.join(change.property_name for change in item.changed_properties)}"
                for item in blueprint.motion_beats
            )
            or "static",
        ),
        shell=ShellContract(
            navigation="Trusted RouteShell owns approved local navigation.",
            main_landmark="Trusted RouteShell owns exactly one main landmark.",
            footer_strategy="Trusted RouteShell owns the route footer when approved.",
            focus_treatment="Visible focus and skip-link behavior are host-owned.",
            route_transition="Routes remain complete without transition motion.",
        ),
        shared_component_contracts=shared_components,
        interactions=interactions,
        resource_inventory=resource_inventory,
        acceptance_coverage=[
            AcceptanceCoverageItem(
                criterion_id=str(item.get("criterion_id", "")),
                route_id=str(item.get("route_id", "")),
                expected_outcome=str(item.get("text", "")) or "Admitted criterion is realized.",
                source_marker=f"marker:{item.get('criterion_id', '')}",
            )
            for item in criteria
            if str(item.get("criterion_id", ""))
        ],
        experience_blueprint=blueprint,
        execution_bindings=bindings,
    )
    return compile_site_plan(
        plan,
        projections,
        max_sections_per_unit=max_sections_per_unit,
        design_neutral=True,
    )


def _storage_key(value: str) -> str:
    normalized = value.replace("\\", "/").strip("/")
    if normalized.startswith("routes/"):
        normalized = normalized.removeprefix("routes/")
    if not normalized or ".." in normalized.split("/"):
        raise ValueError("route storage key is unsafe")
    return normalized


def _responsive_outcome(regions: list[Any]) -> str:
    return "; ".join(
        f"{item.section_id}:m{item.columns_mobile}/t{item.columns_tablet}/d{item.columns_desktop}"
        for item in regions
    )


def _viewport_strategy(regions: list[Any], viewport: str) -> str:
    return "; ".join(
        f"{item.section_id}:order-{getattr(item, f'order_{viewport}')}:"
        f"columns-{getattr(item, f'columns_{viewport}')}"
        for item in sorted(regions, key=lambda value: getattr(value, f"order_{viewport}"))
    )


__all__ = ["compile_blueprint_site_plan"]
