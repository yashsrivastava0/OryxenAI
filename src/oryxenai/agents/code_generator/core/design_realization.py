"""Host-owned compilation of measurable v4 design realization contracts."""

from __future__ import annotations

from oryxenai.agents.code_generator.core.development_schemas import (
    DesignRealizationContract,
    DistinctiveMoveRuntimeCheckV1,
    ExperienceBlueprintV4,
    FontRuntimeCheckV1,
    InteractionRuntimeCheckV1,
    MotionRuntimeCheckV1,
    RegionRuntimeCheckV1,
    ResourceRuntimeCheckV1,
)


def compile_design_realization(
    blueprint: ExperienceBlueprintV4,
    *,
    route_id: str,
    section_order: list[str],
) -> DesignRealizationContract:
    shells = [item for item in blueprint.route_shells if item.route_id == route_id]
    if len(shells) != 1:
        raise ValueError("design realization requires exactly one route shell")
    shell = shells[0]
    if shell.section_order != section_order:
        raise ValueError("design realization section order does not match the trusted route")
    moves = [item for item in blueprint.distinctive_moves if item.route_id == route_id]
    regions = [item for item in blueprint.section_regions if item.route_id == route_id]
    return DesignRealizationContract(
        route_id=route_id,
        section_order=list(section_order),
        region_checks=[
            RegionRuntimeCheckV1(
                region_id=item.region_id,
                section_id=item.section_id,
                section_selector=item.section_selector,
                region_selector=item.region_selector,
                order_mobile=item.order_mobile,
                order_tablet=item.order_tablet,
                order_desktop=item.order_desktop,
                columns_mobile=item.columns_mobile,
                columns_tablet=item.columns_tablet,
                columns_desktop=item.columns_desktop,
                max_measure_ch=item.max_measure_ch,
                gap=item.gap,
                width_ratio_min=item.width_ratio_min,
                width_ratio_max=item.width_ratio_max,
                overlap_ratio_max=item.overlap_ratio_max,
                sticky_allowed=item.sticky_allowed,
            )
            for item in regions
        ],
        distinctive_move_checks=[
            DistinctiveMoveRuntimeCheckV1(
                move_id=item.move_id,
                section_id=item.section_id,
                source_selector=item.source_selector,
                target_selector=item.target_selector,
                relationship=item.relationship,
                minimum_ratio=item.minimum_ratio,
                maximum_ratio=item.maximum_ratio,
                viewports=list(item.viewports),
                required_css_properties=list(item.required_css_properties),
            )
            for item in moves
        ],
        resource_checks=[
            ResourceRuntimeCheckV1(
                resource_slot_id=item.resource_slot_id,
                section_id=item.section_id,
                element_selector=item.element_selector,
                loading=item.loading,
                aspect_ratio_min=item.aspect_ratio_min,
                aspect_ratio_max=item.aspect_ratio_max,
                minimum_visible_ratio=item.minimum_visible_ratio,
            )
            for item in blueprint.resource_placements
            if item.route_id == route_id
        ],
        interaction_checks=[
            InteractionRuntimeCheckV1(
                interaction_id=item.interaction_id,
                target_selector=item.target_selector,
                outcome_selector=item.outcome_selector,
                trigger=item.trigger,
                expected_navigation=item.expected_navigation,
                expected_state_attribute=item.expected_state_attribute,
                expected_state_value=item.expected_state_value,
                focus_behavior=item.focus_behavior,
            )
            for item in blueprint.interaction_assignments
            if item.route_id == route_id
        ],
        motion_checks=[
            MotionRuntimeCheckV1(
                motion_id=item.motion_id,
                target_selector=item.target_selector,
                trigger_selector=item.trigger_selector,
                trigger=item.trigger,
                changed_properties=list(item.changed_properties),
                duration_min_ms=item.duration_min_ms,
                duration_max_ms=item.duration_max_ms,
                performance_budget_ms=item.performance_budget_ms,
                reduced_motion_replacement=item.reduced_motion_replacement,
            )
            for item in blueprint.motion_beats
            if item.route_id == route_id
        ],
        font_checks=[
            FontRuntimeCheckV1(
                role=item.role,
                selector="body" if item.role == "body" else "h1, h2, h3",
                family=item.family,
                weights=list(item.weights),
                local_files=list(item.local_files),
            )
            for item in blueprint.tokens.typography_roles
        ],
    )


__all__ = ["compile_design_realization"]
