"""Pure SitePlan context construction and semantic validation for Phase 1."""

from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import SitePlan


class SitePlanValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def build_planner_context(
    projections: dict[str, dict[str, Any]], input_receipt: dict[str, Any]
) -> dict[str, Any]:
    """Return only the approved public contract and receipt hashes to the model."""
    site = projections["site/contract.json"]
    visual = projections["design/visual-direction.json"]
    resources = projections["resources/projection.json"]
    execution = projections["execution/contract.json"]
    ledger = projections["resources/ledger.json"]
    targets = projections["provenance/targets.json"]
    return {
        "site_contract": site,
        "visual_direction": visual,
        "resource_bindings": {
            "slots": execution.get("slots", []),
            "resource_ledger": ledger.get("resource_decisions", []),
            "materialized_resources": resources.get("resources", []),
        },
        "target_contract": targets.get("target", {}),
        "receipt": {
            "admitted_identity": input_receipt["admitted_identity"],
            "projection_hashes": input_receipt["projection_hashes"],
        },
    }


def context_hash(context: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(context)).hexdigest()


def validate_site_plan(
    value: SitePlan,
    projections: dict[str, dict[str, Any]],
    *,
    max_work_units: int = 64,
    require_blueprint: bool = False,
) -> SitePlan:
    site_routes = projections["site/contract.json"].get("routes", [])
    content = projections["site/contract.json"].get("public_content", [])
    expected_paths = {
        str(route.get("route_id", "")): str(route.get("path", ""))
        for route in site_routes
        if isinstance(route, dict)
    }
    expected_sections = {
        str(pack.get("route_id", "")): {
            str(section.get("section_id", ""))
            for section in pack.get("sections", [])
            if isinstance(section, dict)
        }
        for pack in content
        if isinstance(pack, dict)
    }
    route_ids = [route.route_id for route in value.routes]
    if len(route_ids) != len(set(route_ids)) or set(route_ids) != set(expected_paths):
        raise SitePlanValidationError(
            "PLAN_ROUTE_COVERAGE", "The SitePlan must cover the exact admitted route set."
        )
    for route in value.routes:
        if route.path != expected_paths[route.route_id] or not _route_path(route.path):
            raise SitePlanValidationError(
                "PLAN_ROUTE_PATH", "The SitePlan contains an invalid or mismatched route path."
            )
        if set(route.section_ids) != expected_sections.get(route.route_id, set()):
            raise SitePlanValidationError(
                "PLAN_SECTION_COVERAGE", "Every route must cover its exact admitted sections."
            )
        if not all(
            item.strip()
            for item in (
                route.responsive_outcome,
                route.reduced_motion_outcome,
                route.interaction_outcome,
            )
        ):
            raise SitePlanValidationError(
                "PLAN_EXPERIENCE_OUTCOME",
                "Every route requires explicit responsive, reduced-motion, and interaction outcomes.",
            )
    slot_ids = [slot.slot_id for slot in value.resource_slots]
    if len(slot_ids) != len(set(slot_ids)) or any(
        not slot.slot_id
        or (slot.route_id and slot.route_id not in expected_paths)
        or not slot.purpose.strip()
        for slot in value.resource_slots
    ):
        raise SitePlanValidationError(
            "PLAN_RESOURCE_SLOTS", "Resource slots must be unique, scoped, and recorded only."
        )
    if len(value.work_graph.units) > max_work_units:
        raise SitePlanValidationError(
            "PLAN_WORK_UNIT_CEILING", "The WorkGraph exceeds the configured planning ceiling."
        )
    _validate_design_contract(value, expected_paths, site_routes, projections["site/contract.json"])
    if require_blueprint:
        _validate_experience_blueprint(value, expected_paths, expected_sections)
    _validate_work_graph(value, set(expected_paths), expected_sections)
    return value


def _validate_experience_blueprint(
    plan: SitePlan,
    expected_paths: dict[str, str],
    expected_sections: dict[str, set[str]],
) -> None:
    blueprint = plan.experience_blueprint
    if blueprint is None:
        raise SitePlanValidationError(
            "PLAN_BLUEPRINT_REQUIRED",
            "Session generation requires a measurable ExperienceBlueprintV2.",
        )
    region_ids = [item.region_id for item in blueprint.layout_regions]
    if len(region_ids) != len(set(region_ids)):
        raise SitePlanValidationError("PLAN_LAYOUT_REGION_IDS", "Layout-region IDs must be unique.")
    covered: dict[str, set[str]] = {}
    for region in blueprint.layout_regions:
        if region.route_id not in expected_paths or region.section_id not in expected_sections.get(
            region.route_id, set()
        ):
            raise SitePlanValidationError(
                "PLAN_LAYOUT_REGION_SCOPE", "A layout region is outside approved route scope."
            )
        covered.setdefault(region.route_id, set()).add(region.section_id)
    if covered != expected_sections:
        raise SitePlanValidationError(
            "PLAN_LAYOUT_REGION_COVERAGE",
            "The experience blueprint must cover every approved section.",
        )
    if len(blueprint.layout_regions) != sum(len(items) for items in expected_sections.values()):
        raise SitePlanValidationError(
            "PLAN_LAYOUT_REGION_DUPLICATE",
            "Each approved section must have exactly one layout region.",
        )
    regions = {item.region_id: item for item in blueprint.layout_regions}
    binding_ids = {item.resource_slot_id for item in plan.execution_bindings}
    bindings = {item.resource_slot_id: item for item in plan.execution_bindings}
    typography_binding = bindings.get(blueprint.tokens.typography.resource_slot_id)
    if typography_binding is None or "font" not in typography_binding.category.casefold():
        raise SitePlanValidationError(
            "PLAN_TYPOGRAPHY_BINDING",
            "Blueprint typography must reference an admitted executable font binding.",
        )
    used_slots: set[str] = set()
    for usage in blueprint.resource_usage:
        usage_region = regions.get(usage.region_id)
        if (
            usage.resource_slot_id not in binding_ids
            or usage.route_id not in expected_paths
            or usage.section_id not in expected_sections.get(usage.route_id, set())
            or usage_region is None
            or usage_region.route_id != usage.route_id
            or usage_region.section_id != usage.section_id
        ):
            raise SitePlanValidationError(
                "PLAN_RESOURCE_USAGE_SCOPE",
                "Blueprint resource usage must reference an executable binding and approved region.",
            )
        used_slots.add(usage.resource_slot_id)
    required_visual_slots = {
        item.resource_slot_id
        for item in plan.execution_bindings
        if item.required
        and any(
            value in item.category.casefold()
            for value in ("image", "photo", "media", "illustration", "texture", "visual")
        )
    }
    if not required_visual_slots.issubset(used_slots):
        raise SitePlanValidationError(
            "PLAN_REQUIRED_VISUAL_USAGE",
            "Every required visual binding must have an approved section-level usage plan.",
        )
    for beat in blueprint.motion_beats:
        beat_region = regions.get(beat.target_region_id)
        if (
            beat_region is None
            or beat.route_id != beat_region.route_id
            or (beat.section_id and beat.section_id != beat_region.section_id)
            or not beat.reduced_motion_replacement.strip()
        ):
            raise SitePlanValidationError(
                "PLAN_MOTION_SCOPE",
                "Motion beats must target an approved region with an explicit reduced-motion replacement.",
            )


def _route_path(value: str) -> bool:
    return (
        bool(value) and value.startswith("/") and "\\" not in value and ".." not in value.split("/")
    )


def _safe_owned_path(value: str) -> bool:
    path = PurePosixPath(value)
    return (
        bool(value)
        and not path.is_absolute()
        and not bool(PureWindowsPath(value).drive)
        and ".." not in path.parts
        and all(part for part in path.parts)
    )


def _validate_design_contract(
    plan: SitePlan,
    expected_paths: dict[str, str],
    site_routes: list[Any],
    site_contract: dict[str, Any],
) -> None:
    """Reject a technically valid but visually/content-wise empty SitePlan."""

    required_text = (
        plan.creative_thesis.thesis,
        plan.creative_thesis.distinction,
        plan.creative_thesis.narrative_arc,
        plan.visual_system.typography,
        plan.visual_system.color_strategy,
        plan.visual_system.spacing_rhythm,
        plan.visual_system.motion_vocabulary,
        plan.shell.navigation,
        plan.shell.main_landmark,
        plan.shell.focus_treatment,
    )
    if not all(item.strip() for item in required_text):
        raise SitePlanValidationError(
            "PLAN_DESIGN_CONTRACT",
            "The SitePlan needs a concrete creative thesis, visual system, and accessible shell contract.",
        )
    for route in plan.routes:
        composition = route.composition
        responsive = route.responsive_behavior
        if not all(
            item.strip()
            for item in (
                composition.hierarchy,
                composition.layout_strategy,
                composition.visual_anchor,
                responsive.mobile_strategy,
                responsive.overflow_strategy,
                responsive.touch_target_strategy,
            )
        ):
            raise SitePlanValidationError(
                "PLAN_ROUTE_DESIGN_CONTRACT",
                "Every route needs concrete composition and responsive behavior, not empty design fields.",
            )
    component_ids = [item.component_id for item in plan.shared_component_contracts]
    if (
        not component_ids
        or len(component_ids) != len(set(component_ids))
        or any(
            not item.purpose.strip() or not item.visual_role.strip() or not item.expected_exports
            for item in plan.shared_component_contracts
        )
    ):
        raise SitePlanValidationError(
            "PLAN_SHARED_COMPONENTS",
            "The SitePlan needs uniquely identified shared component contracts with exports and visual roles.",
        )
    interaction_ids = [item.interaction_id for item in plan.interactions]
    if len(interaction_ids) != len(set(interaction_ids)) or any(
        (item.route_id and item.route_id not in expected_paths)
        or not all(
            value.strip()
            for value in (
                item.trigger,
                item.outcome,
                item.keyboard_behavior,
                item.reduced_motion_behavior,
            )
        )
        for item in plan.interactions
    ):
        raise SitePlanValidationError(
            "PLAN_INTERACTIONS",
            "Interaction contracts must be unique, scoped, keyboard accessible, and reduced-motion safe.",
        )
    expected_criteria = {
        str(item.get("criterion_id", ""))
        for item in site_contract.get("criteria", [])
        if isinstance(item, dict) and str(item.get("criterion_id", ""))
    }
    coverage_ids = [item.criterion_id for item in plan.acceptance_coverage]
    if set(coverage_ids) != expected_criteria or any(
        (item.route_id and item.route_id not in expected_paths)
        or not item.expected_outcome.strip()
        or not item.source_marker.strip()
        for item in plan.acceptance_coverage
    ):
        raise SitePlanValidationError(
            "PLAN_ACCEPTANCE_COVERAGE",
            "Acceptance coverage must exactly cover admitted criteria with source evidence markers.",
        )
    del site_routes


def _validate_work_graph(
    plan: SitePlan, route_ids: set[str], expected_sections: dict[str, set[str]]
) -> None:
    units = {unit.unit_id: unit for unit in plan.work_graph.units}
    if len(units) != len(plan.work_graph.units) or not units:
        raise SitePlanValidationError(
            "PLAN_WORK_UNIT_IDS", "Work-unit IDs must be unique and non-empty."
        )
    terminal = [unit for unit in units.values() if unit.terminal]
    if len(terminal) != 1 or terminal[0].kind != "integration":
        raise SitePlanValidationError(
            "PLAN_TERMINAL_UNIT", "The WorkGraph needs exactly one terminal integration unit."
        )
    owner_paths: set[str] = set()
    route_sections: dict[str, set[str]] = {}
    route_unit_ids: dict[str, list[str]] = {}
    compose_units: dict[str, list[str]] = {}
    for unit in units.values():
        if not unit.unit_id or any(dependency not in units for dependency in unit.depends_on):
            raise SitePlanValidationError(
                "PLAN_WORK_GRAPH_REFERENCE", "A WorkGraph dependency is unknown."
            )
        if unit.kind in {"route", "route_batch", "route_compose"}:
            scoped_route_ids = set(unit.route_ids)
            if unit.route_id:
                scoped_route_ids.add(unit.route_id)
            if len(scoped_route_ids) != 1 or not scoped_route_ids.issubset(route_ids):
                raise SitePlanValidationError(
                    "PLAN_WORK_UNIT_ROUTE", "A route work unit is outside the admitted scope."
                )
            route_id = next(iter(scoped_route_ids))
            if unit.kind == "route_compose":
                compose_units.setdefault(route_id, []).append(unit.unit_id)
            else:
                route_unit_ids.setdefault(route_id, []).append(unit.unit_id)
                route_sections.setdefault(route_id, set()).update(unit.section_ids)
            if unit.kind != "route_compose" and not unit.section_ids:
                raise SitePlanValidationError(
                    "PLAN_WORK_UNIT_SECTIONS", "A route work unit must own at least one section."
                )
        elif unit.route_id or unit.route_ids or unit.section_ids:
            raise SitePlanValidationError(
                "PLAN_WORK_UNIT_SCOPE", "Only route work units may own route sections."
            )
        for path in unit.owns_paths:
            if not _safe_owned_path(path) or path in owner_paths:
                raise SitePlanValidationError(
                    "PLAN_FILE_OWNERSHIP",
                    "Future work-unit file ownership must be safe and disjoint.",
                )
            owner_paths.add(path)
    if set(route_sections) != route_ids or any(
        sections != expected_sections[route_id] for route_id, sections in route_sections.items()
    ):
        raise SitePlanValidationError(
            "PLAN_ROUTE_WORK_UNITS",
            "Every admitted route needs exactly one route work unit or split route work units with exact section coverage.",
        )
    for route_id, work_unit_ids in route_unit_ids.items():
        if len(work_unit_ids) > 1 and route_id not in compose_units:
            raise SitePlanValidationError(
                "PLAN_ROUTE_COMPOSITION",
                "Split route batches require one route composition unit.",
            )
    for _route_id, compose_ids in compose_units.items():
        if len(compose_ids) != 1:
            raise SitePlanValidationError(
                "PLAN_ROUTE_COMPOSITION", "Each split route must have one composition unit."
            )
        compose = units[compose_ids[0]]
        if not set(route_unit_ids.get(_route_id, [])).issubset(set(compose.depends_on)):
            raise SitePlanValidationError(
                "PLAN_ROUTE_COMPOSITION",
                "A route composition unit must depend on all of its route batches.",
            )
    if set(terminal[0].depends_on) != set(units) - {terminal[0].unit_id}:
        raise SitePlanValidationError(
            "PLAN_INTEGRATION_DEPENDENCIES",
            "The terminal integration unit must depend on all prior units.",
        )
    _assert_acyclic(units)


def _assert_acyclic(units: dict[str, Any]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(unit_id: str) -> None:
        if unit_id in visiting:
            raise SitePlanValidationError("PLAN_WORK_GRAPH_CYCLE", "The WorkGraph must be acyclic.")
        if unit_id in visited:
            return
        visiting.add(unit_id)
        for dependency in units[unit_id].depends_on:
            visit(dependency)
        visiting.remove(unit_id)
        visited.add(unit_id)

    for unit_id in units:
        visit(unit_id)


def plan_summary(plan: SitePlan) -> dict[str, int | str | list[str]]:
    return {
        "plan_id": plan.plan_id,
        "route_count": len(plan.routes),
        "work_unit_count": len(plan.work_graph.units),
        "route_ids": [route.route_id for route in plan.routes],
    }
