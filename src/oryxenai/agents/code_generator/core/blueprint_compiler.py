"""Compile the provider-safe v4 blueprint into the legacy internal plan domain."""

from __future__ import annotations

import re
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

    blueprint = canonicalize_v4_h1_owners(blueprint)
    blueprint = canonicalize_v4_criterion_ids(blueprint, projections)
    blueprint = _canonicalize_resource_placement_slots(blueprint, projections)
    blueprint = canonicalize_v4_resource_placement_selectors(blueprint)
    blueprint = canonicalize_v4_distinctive_move_selectors(blueprint)
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


def _canonicalize_resource_placement_slots(
    blueprint: ExperienceBlueprintV4,
    projections: dict[str, dict[str, Any]],
) -> ExperienceBlueprintV4:
    """Resolve unique materialized-resource aliases to host-owned slot IDs.

    Creative direction discusses concrete resources by resource ID, while the
    executable placement contract is keyed by ``resource_slot_id``. Providers
    can therefore return the right resource, route, section, and geometry with
    the concrete resource ID in the slot field. The execution contract owns a
    one-to-one resource-to-slot mapping, so canonicalize only unique aliases;
    unknown or ambiguous values remain untouched for semantic validation.
    """

    execution = projections.get("execution/contract.json", {})
    slots = execution.get("slots", []) if isinstance(execution, dict) else []
    known_slots: set[str] = set()
    aliases: dict[str, set[str]] = {}
    for raw_slot in slots:
        if not isinstance(raw_slot, dict):
            continue
        slot_id = str(raw_slot.get("resource_slot_id", "")).strip()
        if not slot_id:
            continue
        known_slots.add(slot_id)
        raw_resolution = raw_slot.get("resolution")
        resolution = raw_resolution if isinstance(raw_resolution, dict) else {}
        resource_id = str(resolution.get("resource_id", "")).strip()
        if resource_id:
            aliases.setdefault(resource_id, set()).add(slot_id)

    changed = False
    placements = []
    for placement in blueprint.resource_placements:
        value = placement.resource_slot_id
        candidates = aliases.get(value, set()) if value not in known_slots else set()
        if len(candidates) == 1:
            placement = placement.model_copy(update={"resource_slot_id": next(iter(candidates))})
            changed = True
        placements.append(placement)
    if not changed:
        return blueprint
    return blueprint.model_copy(update={"resource_placements": placements})


def canonicalize_v4_h1_owners(blueprint: ExperienceBlueprintV4) -> ExperienceBlueprintV4:
    """Assign each route heading to its first approved content section.

    The trusted shell owns the main landmark but has no approved route copy,
    so it cannot author the page heading.  This ownership is fully determined
    by the approved section order and is host-canonicalized like materialized
    resource slots instead of trusting a model echo.
    """

    changed = False
    shells = []
    for shell in blueprint.route_shells:
        owner = shell.section_order[0]
        if shell.h1_owner != owner:
            shell = shell.model_copy(update={"h1_owner": owner})
            changed = True
        shells.append(shell)
    if not changed:
        return blueprint
    return blueprint.model_copy(update={"route_shells": shells})


def canonicalize_v4_criterion_ids(
    blueprint: ExperienceBlueprintV4, projections: dict[str, dict[str, Any]]
) -> ExperienceBlueprintV4:
    """Bind each responsive region to the admitted criterion for its section.

    Acceptance criteria are compiler-owned facts from Build Preparation. A
    model may describe the right region while omitting or echoing a stale
    criterion id; retaining that omission makes an otherwise valid portfolio
    fail late with an opaque coverage error. Rebinding the exact section
    criteria is deterministic and preserves the source-audit contract.
    """

    site = projections.get("site/contract.json", {})
    expected: dict[tuple[str, str], list[str]] = {}
    section_order: dict[str, list[str]] = {}
    for route in site.get("routes", []) if isinstance(site, dict) else []:
        if not isinstance(route, dict):
            continue
        route_id = str(route.get("route_id", "")).strip()
        section_order[route_id] = [
            str(item.get("section_id", "")).strip()
            for item in route.get("sections", [])
            if isinstance(item, dict) and str(item.get("section_id", "")).strip()
        ]
    for content in site.get("public_content", []) if isinstance(site, dict) else []:
        if not isinstance(content, dict):
            continue
        route_id = str(content.get("route_id", "")).strip()
        if route_id and route_id not in section_order:
            section_order[route_id] = [
                str(item.get("section_id", "")).strip()
                for item in content.get("sections", [])
                if isinstance(item, dict) and str(item.get("section_id", "")).strip()
            ]
    for criterion in site.get("criteria", []) if isinstance(site, dict) else []:
        if not isinstance(criterion, dict):
            continue
        route_id = str(criterion.get("route_id", "")).strip()
        section_id = str(criterion.get("section_id", "")).strip()
        criterion_id = str(criterion.get("criterion_id", "")).strip()
        if not route_id or not criterion_id:
            continue
        # Build Preparation may express a route-level criterion with an empty
        # section ID.  The validator intentionally treats that as applying to
        # every approved section, so the canonicalizer must do the same before
        # the compiled plan is validated.  Keeping this rule in one place
        # removes the late PLAN_REGION_CRITERION_COVERAGE failure seen in live
        # runs when the model echoed an otherwise valid blueprint.
        target_sections = [section_id] if section_id else section_order.get(route_id, [])
        for target_section in target_sections:
            if target_section:
                expected.setdefault((route_id, target_section), []).append(criterion_id)
    changed = False
    regions = []
    for region in blueprint.section_regions:
        criterion_ids = expected.get((region.route_id, region.section_id), [])
        if region.criterion_ids != criterion_ids:
            region = region.model_copy(update={"criterion_ids": criterion_ids})
            changed = True
        regions.append(region)
    return blueprint.model_copy(update={"section_regions": regions}) if changed else blueprint


def canonicalize_v4_resource_placement_selectors(
    blueprint: ExperienceBlueprintV4,
) -> ExperienceBlueprintV4:
    """Bind each runtime resource check to its model-authored wrapper marker.

    ``LocalImage`` owns the nested ``img`` and intentionally exposes no API for
    arbitrary image attributes. The generated section owns its wrapper. A
    stable data-marker selector lets runtime verification select that wrapper
    and then inspect the trusted descendant image, which is the verifier's
    existing behavior.
    """

    changed = False
    placements = []
    for placement in blueprint.resource_placements:
        marker = placement.element_marker.strip()
        match = re.fullmatch(
            r"(?P<name>data-[A-Za-z_][\w:.-]*)\s*=\s*(?P<quote>[\"'])"
            r"(?P<value>[^\"'<>\[\]{}]+)(?P=quote)",
            marker,
        )
        if match is not None:
            selector = f"[{match.group('name')}={match.group('quote')}"
            selector += f"{match.group('value')}{match.group('quote')}]"
            if placement.element_selector != selector:
                placement = placement.model_copy(update={"element_selector": selector})
                changed = True
        placements.append(placement)
    if not changed:
        return blueprint
    return blueprint.model_copy(update={"resource_placements": placements})


def canonicalize_v4_distinctive_move_selectors(
    blueprint: ExperienceBlueprintV4,
) -> ExperienceBlueprintV4:
    """Bind section-level move sources to the executable layout region.

    The section selector identifies the semantic section anchor, while the
    region selector identifies the exact element that owns the layout
    declarations used by runtime verification. A provider can reasonably
    echo the former when it means "this section's layout", so normalize only
    that exact, unambiguous alias. Custom source selectors and already
    canonical region selectors remain provider-authored and are left alone.
    """

    regions = {
        (item.route_id, item.section_id, item.region_id): item for item in blueprint.section_regions
    }
    changed = False
    moves = []
    for move in blueprint.distinctive_moves:
        region = regions.get((move.route_id, move.section_id, move.region_id))
        if region is not None and move.source_selector.strip() == region.section_selector.strip():
            move = move.model_copy(update={"source_selector": region.region_selector})
            changed = True
        moves.append(move)
    if not changed:
        return blueprint
    return blueprint.model_copy(update={"distinctive_moves": moves})


def canonicalize_generation_plan(plan: SitePlan) -> SitePlan:
    """Apply deterministic V4 ownership normalization at every stage boundary."""

    blueprint = plan.experience_blueprint
    if not isinstance(blueprint, ExperienceBlueprintV4):
        return plan
    canonical = canonicalize_v4_h1_owners(blueprint)
    canonical = canonicalize_v4_resource_placement_selectors(canonical)
    canonical = canonicalize_v4_distinctive_move_selectors(canonical)
    if canonical is blueprint:
        return plan
    return plan.model_copy(update={"experience_blueprint": canonical})


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


__all__ = [
    "canonicalize_generation_plan",
    "canonicalize_v4_criterion_ids",
    "canonicalize_v4_distinctive_move_selectors",
    "canonicalize_v4_h1_owners",
    "canonicalize_v4_resource_placement_selectors",
    "compile_blueprint_site_plan",
]
