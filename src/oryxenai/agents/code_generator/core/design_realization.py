"""Host-owned compilation of measurable v4 design realization contracts."""

from __future__ import annotations

from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import (
    DesignRealizationContract,
    DistinctiveMoveRuntimeCheckV1,
    ExperienceBlueprintV4,
    FontRuntimeCheckV1,
    ImagePolicySnapshotV1,
    InteractionRuntimeCheckV1,
    MotionRuntimeCheckV1,
    RegionRuntimeCheckV1,
    ResourceRuntimeCheckV1,
)


def _policy_image_obligations(
    blueprint: ExperienceBlueprintV4,
    *,
    route_id: str,
    image_policy: ImagePolicySnapshotV1 | dict[str, Any] | None,
) -> list[Any]:
    if image_policy is None:
        return []
    policy = (
        image_policy
        if isinstance(image_policy, ImagePolicySnapshotV1)
        else ImagePolicySnapshotV1.model_validate(image_policy)
    )
    if policy.text_only_exemption:
        return []
    approved = set(policy.approved_image_slot_ids)
    route_placements = []
    seen_slot_ids: set[str] = set()
    for item in blueprint.resource_placements:
        if item.route_id != route_id or item.resource_slot_id not in approved:
            continue
        if item.resource_slot_id in seen_slot_ids:
            continue
        seen_slot_ids.add(item.resource_slot_id)
        route_placements.append(item)
    if not route_placements:
        return []
    target_route = policy.primary_route_id or route_id
    if route_id != target_route:
        return []
    required_count = max(
        1 if policy.require_primary_route_image else 0,
        policy.minimum_visible_images,
    )
    return route_placements[:required_count]


def _acquired_local_paths_by_slot(
    resource_ledger: dict[str, Any] | None,
) -> dict[str, list[str]]:
    """Resolve every acquisition request namespace back to its execution slot."""

    if not isinstance(resource_ledger, dict):
        return {}
    bindings_by_request_hash = {
        str(item.get("request_id_or_pack_need_id", "")): item
        for item in resource_ledger.get("active_bindings", [])
        if isinstance(item, dict)
    }
    result: dict[str, set[str]] = {}
    for request in resource_ledger.get("requests", []):
        if not isinstance(request, dict):
            continue
        slot_id = str(request.get("request_id", "")).strip()
        for prefix in ("request-", "deferred-", "delegated-"):
            if slot_id.startswith(prefix):
                slot_id = slot_id.removeprefix(prefix)
                break
        request_hash = str(request.get("request_hash", ""))
        binding = bindings_by_request_hash.get(request_hash, {})
        paths = {str(value) for value in binding.get("local_paths", []) if str(value)}
        if slot_id and paths:
            result.setdefault(slot_id, set()).update(paths)
    return {slot_id: sorted(paths) for slot_id, paths in result.items()}


def _generated_local_paths_by_slot(
    generated_resources: dict[str, Any] | None,
) -> dict[str, list[str]]:
    """Return browser-facing paths from the trusted generated image manifest."""

    if not isinstance(generated_resources, dict):
        return {}
    result: dict[str, set[str]] = {}
    for asset in generated_resources.get("image_assets", []):
        if not isinstance(asset, dict):
            continue
        slot_id = str(asset.get("resource_slot_id") or asset.get("resource_id") or "").strip()
        paths = {
            str(source.get("path", ""))
            for source in asset.get("sources", [])
            if isinstance(source, dict) and str(source.get("path", ""))
        }
        if slot_id and paths:
            result.setdefault(slot_id, set()).update(paths)
    return {slot_id: sorted(paths) for slot_id, paths in result.items()}


def _admitted_resource_slot_ids(
    execution: dict[str, Any] | None,
    resource_ledger: dict[str, Any] | None,
    generated_resources: dict[str, Any] | None,
) -> set[str] | None:
    """Return resource slots with a required or materialized runtime binding.

    Acquisition requests may be namespaced as ``request-``, ``deferred-``,
    or ``delegated-`` independently of an immutable execution slot's original
    resolution type. Generated image assets are the browser-facing authority;
    durable acquisition paths remain useful evidence for other resource types.
    """

    if not isinstance(execution, dict) or (
        not isinstance(resource_ledger, dict) and not isinstance(generated_resources, dict)
    ):
        return None
    acquired_paths = _acquired_local_paths_by_slot(resource_ledger)
    generated_paths = _generated_local_paths_by_slot(generated_resources)
    admitted: set[str] = set()
    for slot in execution.get("slots", []):
        if not isinstance(slot, dict):
            continue
        slot_id = str(slot.get("resource_slot_id", ""))
        if not slot_id:
            continue
        resolution = slot.get("resolution", {})
        local_paths = (
            [str(value) for value in resolution.get("local_paths", []) if str(value)]
            if isinstance(resolution, dict)
            else []
        )
        if (
            slot.get("required")
            or local_paths
            or acquired_paths.get(slot_id)
            or generated_paths.get(slot_id)
        ):
            admitted.add(slot_id)
    return admitted


def _local_paths_by_slot(
    execution: dict[str, Any] | None,
    resource_ledger: dict[str, Any] | None,
    generated_resources: dict[str, Any] | None,
) -> dict[str, list[str]]:
    if not isinstance(execution, dict):
        return {}
    acquired_paths = _acquired_local_paths_by_slot(resource_ledger)
    generated_paths = _generated_local_paths_by_slot(generated_resources)
    result: dict[str, list[str]] = {}
    for raw_slot in execution.get("slots", []):
        if not isinstance(raw_slot, dict):
            continue
        slot_id = str(raw_slot.get("resource_slot_id", "")).strip()
        resolution = raw_slot.get("resolution", {})
        if not slot_id or not isinstance(resolution, dict):
            continue
        paths = {str(value) for value in resolution.get("local_paths", []) if str(value)}
        paths.update(acquired_paths.get(slot_id, []))
        paths.update(generated_paths.get(slot_id, []))
        if paths:
            result[slot_id] = sorted(paths)
    return result


def compile_design_realization(
    blueprint: ExperienceBlueprintV4,
    *,
    route_id: str,
    section_order: list[str],
    execution: dict[str, Any] | None = None,
    resource_ledger: dict[str, Any] | None = None,
    generated_resources: dict[str, Any] | None = None,
    image_policy: ImagePolicySnapshotV1 | dict[str, Any] | None = None,
) -> DesignRealizationContract:
    shells = [item for item in blueprint.route_shells if item.route_id == route_id]
    if len(shells) != 1:
        raise ValueError("design realization requires exactly one route shell")
    shell = shells[0]
    if shell.section_order != section_order:
        raise ValueError("design realization section order does not match the trusted route")
    moves = [item for item in blueprint.distinctive_moves if item.route_id == route_id]
    regions = [item for item in blueprint.section_regions if item.route_id == route_id]
    admitted_resource_slot_ids = _admitted_resource_slot_ids(
        execution, resource_ledger, generated_resources
    )
    local_paths_by_slot = _local_paths_by_slot(execution, resource_ledger, generated_resources)
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
                layout_recipe=item.layout_recipe,
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
                runtime_marker=item.runtime_marker,
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
                admitted_local_paths=local_paths_by_slot.get(item.resource_slot_id, []),
            )
            for item in blueprint.resource_placements
            if item.route_id == route_id
            and (
                admitted_resource_slot_ids is None
                or item.resource_slot_id in admitted_resource_slot_ids
            )
        ],
        image_obligations=[
            ResourceRuntimeCheckV1(
                resource_slot_id=item.resource_slot_id,
                section_id=item.section_id,
                element_selector=item.element_selector,
                loading=item.loading,
                aspect_ratio_min=item.aspect_ratio_min,
                aspect_ratio_max=item.aspect_ratio_max,
                minimum_visible_ratio=0.5,
                policy_required=True,
                admitted_local_paths=local_paths_by_slot.get(item.resource_slot_id, []),
            )
            for item in _policy_image_obligations(
                blueprint, route_id=route_id, image_policy=image_policy
            )
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
