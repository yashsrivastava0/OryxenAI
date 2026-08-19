"""Deterministically compile model-authored experience intent into safe work ownership."""

from __future__ import annotations

import re
from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import (
    ExecutionBindingV2,
    SitePlan,
    WorkGraph,
    WorkUnit,
)


def compile_site_plan(
    plan: SitePlan,
    projections: dict[str, dict[str, Any]],
    *,
    max_sections_per_unit: int = 3,
) -> SitePlan:
    """Replace model-authored paths/dependencies with one canonical graph and binding set."""

    site = projections["site/contract.json"]
    routes = {
        str(item.get("route_id", "")): item
        for item in site.get("routes", [])
        if isinstance(item, dict)
    }
    bindings = compile_execution_bindings(projections)
    planned_usage: dict[str, set[tuple[str, str]]] = {}
    if plan.experience_blueprint is not None:
        for usage in plan.experience_blueprint.resource_usage:
            planned_usage.setdefault(usage.resource_slot_id, set()).add(
                (usage.route_id, usage.section_id)
            )
    units: list[WorkUnit] = [
        WorkUnit(
            unit_id="foundation",
            kind="foundation",
            owns_paths=[
                "src/design/generated-tokens.css",
                "src/components/generated/SharedSystems.tsx",
            ],
            required_shared_exports=["SharedSystems"],
            resource_slot_ids=[
                item.resource_slot_id
                for item in bindings
                if not item.route_id
                or "font" in item.category.casefold()
                or "typography" in item.category.casefold()
            ],
            context_estimate=12000,
            output_estimate=16000,
        )
    ]
    for route in plan.routes:
        source = routes.get(route.route_id, {})
        ordered_sections = [str(item) for item in source.get("section_sequence", [])]
        if set(ordered_sections) != set(route.section_ids):
            ordered_sections = list(route.section_ids)
        storage_key = _storage_key(source, route.route_id)
        batches = [
            ordered_sections[index : index + max(1, max_sections_per_unit)]
            for index in range(0, len(ordered_sections), max(1, max_sections_per_unit))
        ]
        if not batches:
            batches = [[]]
        criteria = [
            item.criterion_id
            for item in plan.acceptance_coverage
            if not item.route_id or item.route_id == route.route_id
        ]
        batch_ids: list[str] = []
        for index, sections in enumerate(batches, start=1):
            resource_ids = [
                item.resource_slot_id
                for item in bindings
                if item.route_id == route.route_id
                and "font" not in item.category.casefold()
                and "typography" not in item.category.casefold()
                and (
                    any(
                        usage_route == route.route_id and usage_section in sections
                        for usage_route, usage_section in planned_usage[item.resource_slot_id]
                    )
                    if planned_usage.get(item.resource_slot_id)
                    else not item.section_ids or set(item.section_ids).intersection(sections)
                )
            ]
            split = len(batches) > 1
            unit_id = (
                f"route-{_slug(route.route_id)}-batch-{index}"
                if split
                else f"route-{_slug(route.route_id)}"
            )
            path = (
                f"src/routes/{storage_key}/sections/Batch{index}.tsx"
                if split
                else f"src/routes/{storage_key}/index.tsx"
            )
            style_path = (
                f"src/routes/{storage_key}/sections/Batch{index}.css"
                if split
                else f"src/routes/{storage_key}/route.css"
            )
            units.append(
                WorkUnit(
                    unit_id=unit_id,
                    kind="route_batch" if split else "route",
                    route_id=route.route_id,
                    route_ids=[route.route_id],
                    owns_paths=[path, style_path],
                    depends_on=["foundation"],
                    section_ids=sections,
                    required_shared_exports=["SharedSystems"],
                    resource_slot_ids=resource_ids,
                    criterion_ids=[] if split else criteria,
                    context_estimate=14000,
                    output_estimate=18000,
                )
            )
            batch_ids.append(unit_id)
        if len(batch_ids) > 1:
            units.append(
                WorkUnit(
                    unit_id=f"route-{_slug(route.route_id)}-compose",
                    kind="route_compose",
                    route_id=route.route_id,
                    route_ids=[route.route_id],
                    owns_paths=[
                        f"src/routes/{storage_key}/index.tsx",
                        f"src/routes/{storage_key}/route.css",
                    ],
                    depends_on=["foundation", *batch_ids],
                    required_shared_exports=["SharedSystems"],
                    criterion_ids=criteria,
                    context_estimate=8000,
                    output_estimate=8000,
                )
            )
    prior_ids = [unit.unit_id for unit in units]
    units.append(
        WorkUnit(
            unit_id="integration-review",
            kind="integration",
            depends_on=sorted(prior_ids),
            terminal=True,
            context_estimate=16000,
            output_estimate=6000,
        )
    )
    return plan.model_copy(
        update={
            "work_graph": WorkGraph(units=units, terminal_integration_unit="integration-review"),
            "execution_bindings": bindings,
        }
    )


def compile_execution_bindings(
    projections: dict[str, dict[str, Any]],
) -> list[ExecutionBindingV2]:
    execution = projections.get("execution/contract.json", {})
    bindings: list[ExecutionBindingV2] = []
    for slot in execution.get("slots", []) if isinstance(execution, dict) else []:
        if not isinstance(slot, dict):
            continue
        resolution_value = slot.get("resolution")
        resolution: dict[str, Any] = resolution_value if isinstance(resolution_value, dict) else {}
        bindings.append(
            ExecutionBindingV2(
                resource_slot_id=str(slot.get("resource_slot_id", "")),
                route_id=str(slot.get("route_id", "")),
                section_ids=[str(item) for item in slot.get("section_ids", [])],
                category=str(slot.get("category", "")),
                purpose=str(slot.get("rationale", "")),
                resolution_type=str(resolution.get("resolution_type", "")),
                local_paths=[str(item) for item in resolution.get("local_paths", [])],
                package_name=str(resolution.get("package_name", "")),
                expected_exports=[str(item) for item in resolution.get("expected_exports", [])],
                font_family=str(resolution.get("font_family", "")),
                font_weights=[str(item) for item in resolution.get("font_weights", [])],
                required=bool(slot.get("required")),
                provenance={
                    "provider": str(resolution.get("provider", "")),
                    "source_reference": str(resolution.get("source_reference", "")),
                    "license": str(resolution.get("license", "")),
                },
                responsive_behavior=str(resolution.get("responsive_behavior", "")),
                reduced_motion_behavior=str(resolution.get("reduced_motion_behavior", "")),
                fallback_behavior=str(resolution.get("fallback_behavior", "")),
            )
        )
    return bindings


def _storage_key(route: dict[str, Any], route_id: str) -> str:
    value = str(route.get("storage_key", "")).replace("\\", "/").strip("/")
    if value.startswith("routes/"):
        value = value.removeprefix("routes/")
    return value or _slug(route_id)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "route"
