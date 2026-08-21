"""Host-owned compilation of measurable v4 design realization contracts."""

from __future__ import annotations

from oryxenai.agents.code_generator.core.development_schemas import (
    DesignRealizationContract,
    ExperienceBlueprintV4,
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
        signature_move_ids=[item.move_id for item in moves],
        region_ids=[item.region_id for item in regions],
        motion_ids=[item.motion_id for item in blueprint.motion_beats if item.route_id == route_id],
        resource_slot_ids=[
            item.resource_slot_id
            for item in blueprint.resource_placements
            if item.route_id == route_id
        ],
        interaction_ids=[
            item.interaction_id
            for item in blueprint.interaction_assignments
            if item.route_id == route_id
        ],
        acceptance_markers=[item.runtime_marker for item in moves],
    )


__all__ = ["compile_design_realization"]
