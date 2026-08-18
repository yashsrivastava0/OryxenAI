"""Deterministic v3 execution inventory compilation.

This module translates an already-approved public scope into bindings a source
generator can actually consume.  It never changes upstream content or visual
direction: a missing required implementation has an explicit execution gap
instead of an invented asset, component, or project claim.
"""

from __future__ import annotations

import hashlib
from typing import Any

from oryxenai.agents.build_preparation.contracts import PACK_VERSION, SCHEMA_VERSION
from oryxenai.agents.build_preparation.schemas import (
    ExecutionGap,
    ExecutionSlot,
    LocalRecipe,
    ResolvedResource,
    ResourceNeed,
    RouteScope,
)


def _stable_id(prefix: str, *values: str) -> str:
    payload = "\x1f".join(values).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:20]}"


def _recipe_category(category: str, purpose: str) -> str:
    text = f"{category} {purpose}".casefold()
    if "font" in text or "typograph" in text:
        return "typography_system"
    if any(token in text for token in ("diagram", "flow", "topology", "architecture")):
        return "representative_svg_diagram"
    if any(token in text for token in ("hero", "text-led", "headline")):
        return "typographic_composition"
    if any(token in text for token in ("photo", "image", "ornament", "decorative")):
        return "ornament_omission"
    return "css_surface_pattern"


def _recipe(
    *,
    slot_id: str,
    category: str,
    purpose: str,
    source_id: str,
    fallback: str,
) -> LocalRecipe:
    recipe_id = _stable_id("recipe", slot_id)
    recipe_category = _recipe_category(category, purpose)
    description = (
        fallback.strip()
        or {
            "typography_system": "Use the configured local system typography declarations.",
            "typographic_composition": "Use a text-led composition without representative media.",
            "representative_svg_diagram": "Render a labelled representative SVG with no product claims.",
            "ornament_omission": "Omit the nonessential ornament without replacing it with stock media.",
            "css_surface_pattern": "Use a CSS-only surface or pattern within the approved visual direction.",
        }[recipe_category]
    )
    return LocalRecipe(
        recipe_id=recipe_id,
        slot_id=slot_id,
        category=recipe_category,  # type: ignore[arg-type]
        description=description,
        allowed_labels=[source_id] if source_id else [],
        forbidden_concepts=[
            "personal portrait",
            "project screenshot",
            "dashboard",
            "invented metric",
            "invented client or outcome",
        ],
        reduced_motion_state="static",
        local_path=f"resources/recipes/{recipe_id}.json",
    )


def _local_paths(resource: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("local_path", "local_directory"):
        value = str(resource.get(key, "") or "")
        if value:
            values.append(value)
    for entry in resource.get("source_files", []) or []:
        if isinstance(entry, dict) and str(entry.get("local_path", "") or ""):
            values.append(str(entry["local_path"]))
    return sorted(set(values))


def _criteria_by_route(site: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in site.get("criteria", []) or []:
        if not isinstance(item, dict):
            continue
        route_id = str(item.get("route_id", "") or "")
        criterion_id = str(item.get("criterion_id", "") or "")
        if route_id and criterion_id:
            result.setdefault(route_id, []).append(criterion_id)
    return {route_id: sorted(ids) for route_id, ids in result.items()}


def _route_sections(site: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for route in site.get("routes", []) or []:
        if isinstance(route, dict) and route.get("route_id"):
            result[str(route["route_id"])] = [
                str(item) for item in route.get("section_sequence", []) if str(item)
            ]
    return result


def _is_visual_resource(need: ResourceNeed) -> bool:
    category = need.category.casefold()
    return category in {
        "image",
        "photo",
        "editorial_photo",
        "portrait",
        "visual_component",
        "component",
        "registry_component",
    }


def compile_execution_contract(
    *,
    routes: list[RouteScope],
    needs: list[ResourceNeed],
    materialized_resources: list[dict[str, Any]],
    site: dict[str, Any],
    visual: dict[str, Any],
    target: dict[str, Any],
) -> tuple[dict[str, Any], list[LocalRecipe], list[ExecutionSlot], list[ExecutionGap]]:
    """Return the hashable v3 execution contract and its declared recipes.

    A selected resource is useful only when it has local bytes/source or a
    permitted target-package binding.  All other known needs get a typed local
    recipe if safe; critical approved-user media without a local item is a
    fail-closed VDD execution gap.
    """
    by_need: dict[str, dict[str, Any]] = {}
    for resource in materialized_resources:
        if isinstance(resource, dict) and str(resource.get("need_id", "") or ""):
            by_need[str(resource["need_id"])] = resource
    criteria = _criteria_by_route(site)
    sections = _route_sections(site)
    allowed_dependencies = set(target.get("allowed_dependencies") or [])
    slots: list[ExecutionSlot] = []
    recipes: list[LocalRecipe] = []
    gaps: list[ExecutionGap] = []

    for need in sorted(needs, key=lambda value: value.need_id):
        slot_id = _stable_id("slot", need.need_id)
        route_id = need.route_ids[0] if need.route_ids else ""
        resource = by_need.get(need.need_id, {})
        disposition = str(resource.get("disposition", "") or "")
        source_expectations = [
            value
            for value in (
                str(resource.get("source_reference", "") or ""),
                str(resource.get("license_reference", "") or ""),
            )
            if value
        ]
        source_expectations.extend(
            f"sha256:{entry.get('sha256')}"
            for entry in resource.get("source_files", []) or []
            if isinstance(entry, dict) and str(entry.get("sha256", "") or "")
        )
        if disposition in {"local_file", "adaptable_source"} and _local_paths(resource):
            resolution = ResolvedResource(
                resolution_type="local_materialized",
                resource_id=str(resource.get("id", "") or ""),
                local_paths=_local_paths(resource),
                fallback_disposition="typed_local_recipe_when_local_material_fails",
                accessibility_treatment=(
                    "decorative media uses empty alt text; meaningful media needs supplied alt text"
                    if str(resource.get("kind", "")) == "photo"
                    else "preserve semantic labels and focus treatment in the approved route"
                ),
                font_family=str(resource.get("font_family", "") or ""),
                font_weights=[str(value) for value in resource.get("font_weights", []) or []],
                expected_exports=[
                    str(value)
                    for value in (
                        resource.get("expected_exports", [])
                        or resource.get("usage_contract", {}).get("expected_exports", [])
                    )
                    if str(value).strip()
                ],
                source_expectations=source_expectations,
                provider=str(resource.get("provider", "") or ""),
                provider_asset_id=str(resource.get("provider_asset_id", "") or ""),
                source_reference=str(resource.get("source_reference", "") or ""),
                license=str(resource.get("license", "") or ""),
                license_reference=str(resource.get("license_reference", "") or ""),
                source_hashes=[
                    str(value)
                    for value in (
                        resource.get("source_hashes", [])
                        or resource.get("usage_contract", {}).get("source_hashes", [])
                        or [
                            item.get("sha256")
                            for item in resource.get("source_files", []) or []
                            if isinstance(item, dict) and item.get("sha256")
                        ]
                    )
                    if str(value)
                ],
                release_pin=str(resource.get("source_version", "") or ""),
                dependencies=[str(value) for value in resource.get("dependencies", []) or []],
                registry_dependencies=[
                    str(value) for value in resource.get("registry_dependencies", []) or []
                ],
                import_path=str(
                    resource.get("import_path", "")
                    or resource.get("usage_contract", {}).get("import_path", "")
                    or (f"./{_local_paths(resource)[0]}" if _local_paths(resource) else "")
                ),
                responsive_behavior=str(
                    resource.get("usage_contract", {}).get("responsive_behavior", "")
                    or need.details.get("responsive_behavior", "")
                    or ""
                ),
                reduced_motion_behavior=str(
                    resource.get("usage_contract", {}).get("reduced_motion_behavior", "")
                    or need.details.get("reduced_motion_behavior", "")
                    or "static equivalent"
                ),
                fallback_behavior=str(
                    resource.get("usage_contract", {}).get("fallback", "")
                    or resource.get("fallback", "")
                    or need.fallback
                    or ""
                ),
            )
        elif disposition == "package_import":
            package_import = str(resource.get("package_import", "") or "")
            package_name, _, export_name = package_import.partition(":")
            if package_name not in allowed_dependencies or not export_name:
                recipe = _recipe(
                    slot_id=slot_id,
                    category=need.category,
                    purpose=need.purpose,
                    source_id=need.source_id,
                    fallback=need.fallback,
                )
                recipes.append(recipe)
                resolution = ResolvedResource(
                    resolution_type="local_recipe",
                    recipe_id=recipe.recipe_id,
                    fallback_disposition="package_binding_not_admitted",
                    accessibility_treatment="use a labelled semantic control or omit the icon",
                )
            else:
                resolution = ResolvedResource(
                    resolution_type="target_package_binding",
                    resource_id=str(resource.get("id", "") or ""),
                    package_name=package_name,
                    expected_exports=[export_name],
                    fallback_disposition="omit_nonessential_icon_when_binding_is_unavailable",
                    accessibility_treatment="decorative icons are aria-hidden; actionable icons have an accessible name",
                    source_expectations=source_expectations,
                    provider=str(resource.get("provider", "") or ""),
                    provider_asset_id=str(resource.get("provider_asset_id", "") or ""),
                    source_reference=str(resource.get("source_reference", "") or ""),
                    license=str(resource.get("license", "") or ""),
                    license_reference=str(resource.get("license_reference", "") or ""),
                    release_pin=str(resource.get("source_version", "") or ""),
                    dependencies=[str(value) for value in resource.get("dependencies", []) or []],
                    registry_dependencies=[
                        str(value) for value in resource.get("registry_dependencies", []) or []
                    ],
                    import_path=str(resource.get("import_path", "") or ""),
                    fallback_behavior=str(resource.get("fallback", "") or need.fallback or ""),
                )
        elif _is_visual_resource(need):
            message = f"Known visual role '{need.source_id}' has no verified local image or component source."
            gap = ExecutionGap(
                slot_id=slot_id,
                route_id=route_id,
                scene_ids=need.scene_ids,
                message=message,
                next_action=(
                    "Run live approved resource providers and materialize the real image/component, "
                    "or revise Visual Design Director to remove the requirement explicitly."
                ),
            )
            gaps.append(gap)
            resolution = ResolvedResource(
                resolution_type="execution_gap",
                fallback_disposition="blocked_pending_real_visual_resource",
                accessibility_treatment="not applicable while blocked",
            )
        elif need.source_policy == "approved_user_media" and (
            need.required_for_handoff or need.importance.casefold() == "critical"
        ):
            message = (
                f"Approved user media '{need.source_id}' is required but no verified local media or "
                "safe approved fallback was materialized."
            )
            gap = ExecutionGap(
                slot_id=slot_id,
                route_id=route_id,
                scene_ids=need.scene_ids,
                message=message,
                next_action="Revise Visual Design Director direction or provide approved local media; do not substitute stock.",
            )
            gaps.append(gap)
            resolution = ResolvedResource(
                resolution_type="execution_gap",
                fallback_disposition="blocked_pending_vdd_revision",
                accessibility_treatment="not applicable while blocked",
            )
        else:
            recipe = _recipe(
                slot_id=slot_id,
                category=need.category,
                purpose=need.purpose,
                source_id=need.source_id,
                fallback=need.fallback,
            )
            recipes.append(recipe)
            resolution = ResolvedResource(
                resolution_type="local_recipe",
                recipe_id=recipe.recipe_id,
                fallback_disposition="recipe_is_the_prepared_resolution",
                accessibility_treatment=(
                    "decorative treatment only; omit alt text and respect reduced motion"
                    if recipe.category == "ornament_omission"
                    else "use supplied labels only and a static reduced-motion equivalent"
                ),
            )
        slots.append(
            ExecutionSlot(
                resource_slot_id=slot_id,
                category=need.category or need.kind,
                route_id=route_id,
                scene_ids=sorted(set(need.scene_ids)),
                section_ids=sorted(set(need.section_ids or sections.get(route_id, []))),
                component_placement=str(need.details.get("placement", "") or need.purpose),
                required=need.required_for_handoff,
                source_ids=[need.source_id],
                criterion_ids=criteria.get(route_id, []),
                rationale=need.purpose or need.fallback,
                provenance=(
                    "build_preparation_derived"
                    if need.source_id.startswith("assumed-")
                    else "vdd_explicit"
                ),
                resolution=resolution,
            )
        )

    # Target counts are advisory reporting values.  They never manufacture a
    # gap or suppress a role; the role inventory above is authoritative.

    # Sparse but structurally valid visual direction still needs a concrete
    # implementation baseline.  These are constrained, derived mechanics,
    # never new portfolio evidence or a new creative direction.
    first_route = routes[0].route_id if routes else ""
    derived = [
        (
            "typography",
            "typography_system",
            "Configured system typography fallback with display, body, and utility weights.",
            "typography",
        ),
        (
            "hero",
            "typographic_composition",
            "Text-led hero composition using approved public copy only; no personal or project imagery.",
            "text-led-hero",
        ),
    ]
    for label, category, rationale, source_id in derived:
        slot_id = _stable_id("slot", "derived", label, first_route)
        recipe = _recipe(
            slot_id=slot_id,
            category=category,
            purpose=rationale,
            source_id=source_id,
            fallback=rationale,
        )
        recipes.append(recipe)
        slots.append(
            ExecutionSlot(
                resource_slot_id=slot_id,
                category=category,
                route_id=first_route,
                section_ids=sections.get(first_route, []),
                component_placement="site foundation" if label == "typography" else "hero scene",
                required=True,
                source_ids=[],
                criterion_ids=criteria.get(first_route, []),
                rationale=rationale,
                provenance="build_preparation_derived",
                resolution=ResolvedResource(
                    resolution_type="local_recipe",
                    recipe_id=recipe.recipe_id,
                    font_family=("system-ui, sans-serif" if label == "typography" else ""),
                    font_weights=(["400", "500", "600", "700"] if label == "typography" else []),
                    fallback_disposition="configured_system_stack",
                    accessibility_treatment="static equivalent under reduced motion",
                ),
            )
        )

    # Lucide is already a target dependency.  This is a constrained binding,
    # not a downloaded SVG or an instruction to change dependencies.
    if first_route and "lucide-react" in allowed_dependencies:
        slots.append(
            ExecutionSlot(
                resource_slot_id=_stable_id("slot", "derived", "ui-icons", first_route),
                category="icon",
                route_id=first_route,
                section_ids=sections.get(first_route, []),
                component_placement="navigation and non-evidentiary UI affordances",
                required=False,
                source_ids=[],
                criterion_ids=criteria.get(first_route, []),
                rationale="Use only bounded UI affordances; icons do not imply portfolio facts.",
                provenance="build_preparation_derived",
                resolution=ResolvedResource(
                    resolution_type="target_package_binding",
                    package_name="lucide-react",
                    expected_exports=["ArrowUpRight", "Menu", "X"],
                    fallback_disposition="use text labels when an icon is not needed",
                    accessibility_treatment="icons are aria-hidden beside text; icon-only controls need an accessible name",
                    source_expectations=["target/package.json"],
                ),
            )
        )

    # A configured visual direction may describe an abstract systems scene but
    # no actual media.  A labelled representative SVG is safe only when that
    # scene already signals a flow/topology/system concept.
    scenes_text = str(visual.get("routes", [])).casefold()
    if first_route and any(
        token in scenes_text for token in ("flow", "topology", "system", "process")
    ):
        slot_id = _stable_id("slot", "derived", "representative-diagram", first_route)
        recipe = _recipe(
            slot_id=slot_id,
            category="diagram",
            purpose="Representative abstract topology or flow diagram with no product UI or unapproved metrics.",
            source_id="representative-diagram",
            fallback="Use a CSS-only labelled flow without project-specific claims.",
        )
        recipes.append(recipe)
        slots.append(
            ExecutionSlot(
                resource_slot_id=slot_id,
                category="diagram",
                route_id=first_route,
                section_ids=sections.get(first_route, []),
                component_placement="systems or selected-work scene",
                required=False,
                source_ids=[],
                criterion_ids=criteria.get(first_route, []),
                rationale=recipe.description,
                provenance="build_preparation_derived",
                resolution=ResolvedResource(
                    resolution_type="local_recipe",
                    recipe_id=recipe.recipe_id,
                    fallback_disposition="static_css_flow",
                    accessibility_treatment="provide equivalent text labels; decorative connectors are hidden from assistive technology",
                ),
            )
        )

    slots.sort(key=lambda value: value.resource_slot_id)
    recipes.sort(key=lambda value: value.recipe_id)
    gaps.sort(key=lambda value: value.slot_id)
    contract = {
        "schema_version": SCHEMA_VERSION,
        "pack_version": PACK_VERSION,
        "slots": [slot.model_dump(mode="json") for slot in slots],
        "execution_gaps": [gap.model_dump(mode="json") for gap in gaps],
        "policy": {
            "known_resource_requirements_prepared_upstream": True,
            "runtime_network_fetch_allowed": False,
            "emergent_code_generator_acquisition_requires_receipt": True,
            "allowed_resolution_types": [
                "local_materialized",
                "target_package_binding",
                "local_recipe",
                "execution_gap",
            ],
            "visual_resource_policy": {
                "visual_slots_require_real_local_material": True,
                "generated_local_visuals_forbidden": True,
                "recipes_cannot_resolve_images_or_components": True,
            },
        },
    }
    return contract, recipes, slots, gaps
