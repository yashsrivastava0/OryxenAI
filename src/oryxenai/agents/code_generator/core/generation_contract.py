"""Deterministic per-unit generation contract compiled from trusted inputs.

The contract is the single normative bridge between what the validators
enforce mechanically and what the model is told: every rule the source and
final-source validators check is stated here with the exact data it is
checked against (verbatim copy inventory, marker tokens, interaction
attributes, slot-binding evidence, approved URL allowlist, ownership and
create/replace ground truth). It is injected both as structured JSON into
the operation context and as a rendered instruction block appended to the
operation prompt, so no validator rule exists that the model was not told
about.
"""

from __future__ import annotations

import json
import re
from typing import Any

from oryxenai.agents.code_generator.core.blueprint_compiler import canonicalize_v4_h1_owners
from oryxenai.agents.code_generator.core.content_compiler import content_ids_by_section
from oryxenai.agents.code_generator.core.development_schemas import (
    ExperienceBlueprintV4,
    SitePlan,
    WorkUnit,
)
from oryxenai.agents.code_generator.core.path_policy import semantic_segment

CONTRACT_VERSION = "code-generator-generation-contract-v4"

_TRUSTED_FILES = (
    "package.json",
    "package-lock.json",
    "vite.config.ts",
    "tsconfig.json",
    "tsconfig.app.json",
    "tsconfig.node.json",
    "index.html",
    "src/main.tsx",
    "src/app/AppRouter.tsx",
    "src/app/PreviewBridge.ts",
    "src/app/ResourceUrl.ts",
    "src/app/ErrorBoundary.tsx",
    "src/design/global.css",
)
_TRUSTED_PREFIXES = ("src/generated/", "src/content/")
_PLACEHOLDER_TERMS = ("lorem ipsum", "todo", "placeholder", "coming soon", "fake success")
_FORBIDDEN_RUNTIME = ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource")
_MAX_VERBATIM_STRINGS = 160


def _normalized_strings(value: Any) -> list[str]:
    """Mirror of the validators' string walk: whitespace-collapsed strings."""

    result: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, str) and item.strip():
            result.append(" ".join(item.split()))
        elif isinstance(item, dict):
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return result


def _public_text(projections: dict[str, dict[str, Any]]) -> set[str]:
    values = set()
    for text in _normalized_strings(projections.get("site/contract.json", {})):
        values.add(text)
    return values


def _approved_urls(public_text: set[str]) -> list[str]:
    url_re = re.compile(r"https?://[^\s\"'<>)\]}]+", re.IGNORECASE)
    urls: set[str] = set()
    for entry in public_text:
        for match in url_re.finditer(entry or ""):
            urls.add(match.group(0).rstrip(".,;:"))
    return sorted(urls)


def _executable_navigation_expectation(assignment: Any) -> str:
    """Expose navigation literals only for interactions that actually navigate."""

    if assignment is None:
        return ""
    value = str(assignment.expected_navigation).strip()
    if assignment.trigger in {"navigation", "download"} or value.startswith(
        ("#", "/", "http://", "https://", "mailto:", "tel:")
    ):
        return value
    return ""


def _storage_key(route: dict[str, Any], route_id: str) -> str:
    storage_key = str(route.get("storage_key", route_id)).replace("\\", "/").strip("/")
    if storage_key.startswith("routes/"):
        storage_key = storage_key.removeprefix("routes/")
    return storage_key


def _route_scope(unit: WorkUnit | None, projections: dict[str, dict[str, Any]]) -> list[str]:
    routes = [
        str(item.get("route_id", ""))
        for item in projections.get("site/contract.json", {}).get("routes", [])
        if isinstance(item, dict) and item.get("route_id")
    ]
    if unit is None:
        return routes
    unit_routes = set(unit.route_ids) or ({unit.route_id} if unit.route_id else set())
    return [route_id for route_id in routes if route_id in unit_routes]


def build_generation_contract(
    *,
    unit: WorkUnit | None,
    plan: SitePlan,
    projections: dict[str, dict[str, Any]],
    operation: str,
    owned_paths: list[str],
) -> dict[str, Any]:
    site = projections.get("site/contract.json", {})
    scope = _route_scope(unit, projections)
    routes_by_id = {
        str(item.get("route_id", "")): item
        for item in site.get("routes", [])
        if isinstance(item, dict)
    }
    content_by_route = {
        str(item.get("route_id", "")): item
        for item in site.get("public_content", [])
        if isinstance(item, dict)
    }
    blueprint = plan.experience_blueprint
    v4_blueprint = blueprint if isinstance(blueprint, ExperienceBlueprintV4) else None
    v4 = v4_blueprint is not None
    v4_section_selectors = (
        {
            (region.route_id, region.section_id): region.section_selector
            for region in v4_blueprint.section_regions
        }
        if v4_blueprint is not None
        else {}
    )
    v4_interactions = (
        {
            assignment.interaction_id: assignment
            for assignment in v4_blueprint.interaction_assignments
        }
        if v4_blueprint is not None
        else {}
    )
    v4_route_shells = {}
    if v4_blueprint is not None:
        canonical_blueprint = canonicalize_v4_h1_owners(v4_blueprint)
        v4_route_shells = {shell.route_id: shell for shell in canonical_blueprint.route_shells}
    content_keys = content_ids_by_section(
        [item for item in site.get("public_content", []) if isinstance(item, dict)],
        [item for item in site.get("facts", []) if isinstance(item, dict)],
    )

    route_contracts: list[dict[str, Any]] = []
    for route_id in scope:
        route = routes_by_id.get(route_id, {})
        storage_key = _storage_key(route, route_id)
        if v4:
            storage_key = semantic_segment(storage_key or route_id)
        owned_tsx = [
            path
            for path in (unit.owns_paths if unit is not None else [])
            if path.endswith(".tsx") and "*" not in path
        ]
        owner_by_section = (
            dict(zip(unit.section_ids, owned_tsx, strict=False))
            if unit is not None and unit.kind == "route_batch"
            else {}
        )
        anchor_file = owned_tsx[0] if owned_tsx else f"src/routes/{storage_key}/index.tsx"
        content_pack = content_by_route.get(route_id, {})
        assigned_sections = set(unit.section_ids) if unit is not None else set()
        sections: list[dict[str, Any]] = []
        verbatim: list[str] = []
        for section in content_pack.get("sections", []) if isinstance(content_pack, dict) else []:
            if not isinstance(section, dict):
                continue
            section_id = str(section.get("section_id", ""))
            if assigned_sections and section_id not in assigned_sections:
                continue
            approved_content_ids = (
                []
                if unit is not None and unit.kind == "route_compose"
                else content_keys.get((route_id, section_id), [])
            )
            prose = [
                text
                for text in _normalized_strings(section.get("content", {}))
                # Prose filter mirrors final_source_validation exactly:
                # multi-word strings of six or more characters.
                if " " in text and len(text) >= 6
            ]
            if section_id:
                sections.append(
                    {
                        "section_id": section_id,
                        "section_selector": v4_section_selectors.get((route_id, section_id), ""),
                        "owner_file": owner_by_section.get(section_id, ""),
                        "content_ids": list(approved_content_ids),
                        "verbatim_strings": [] if v4 else prose,
                    }
                )
            if not v4 and (unit is None or unit.kind != "route_compose"):
                verbatim.extend(prose)
        route_contracts.append(
            {
                "route_id": route_id,
                "route_path": str(route.get("path", "")),
                "anchor_file": anchor_file,
                "section_owner_files": list(owned_tsx)
                if unit is not None and unit.kind == "route_batch"
                else [],
                "section_ids": [item["section_id"] for item in sections],
                "sections": sections,
                "verbatim_copy": [] if v4 else sorted(set(verbatim))[:_MAX_VERBATIM_STRINGS],
                "section_anchors_required": unit is None or unit.kind != "route_compose",
                # Route batches own the executable approved-content references.
                # A V4 composer owns only the route shell and must render those
                # completed batches, so asking it to report every route content
                # key would make its honest per-unit coverage impossible: the
                # composer WorkUnit intentionally has no section ownership.
                "content_keys_required": v4 and (unit is None or unit.kind != "route_compose"),
                "verbatim_in_anchor": (unit is None or unit.kind != "route_compose") and not v4,
                "route_shell": (
                    v4_route_shells[route_id].model_dump(mode="json")
                    if route_id in v4_route_shells
                    else {}
                ),
            }
        )

    markers = [
        {
            "route_id": coverage.route_id,
            "criterion_id": coverage.criterion_id,
            "source_marker": coverage.source_marker,
        }
        for coverage in plan.acceptance_coverage
        if (coverage.route_id in scope or not scope)
        and (unit is None or coverage.criterion_id in unit.criterion_ids)
    ]
    interactions: list[dict[str, Any]] = []
    for interaction in plan.interactions:
        if not (interaction.route_id in scope or not scope) or (
            unit is not None and interaction.interaction_id not in unit.interaction_ids
        ):
            continue
        assignment = v4_interactions.get(interaction.interaction_id)
        interactions.append(
            {
                "route_id": interaction.route_id,
                "interaction_id": interaction.interaction_id,
                "attribute": f'data-interaction-id="{interaction.interaction_id}"',
                "literal_marker": assignment.literal_marker if assignment is not None else "",
                "target_selector": assignment.target_selector if assignment is not None else "",
                "outcome_selector": assignment.outcome_selector if assignment is not None else "",
                "trigger": assignment.trigger if assignment is not None else "",
                "expected_navigation": (_executable_navigation_expectation(assignment)),
                "expected_state_attribute": (
                    assignment.expected_state_attribute if assignment is not None else ""
                ),
                "expected_state_value": (
                    assignment.expected_state_value if assignment is not None else ""
                ),
                "state_transition": assignment.state_transition if assignment is not None else "",
                "keyboard_behavior": (
                    assignment.keyboard_behavior if assignment is not None else ""
                ),
                "focus_behavior": assignment.focus_behavior if assignment is not None else "",
            }
        )

    execution = projections.get("execution/contract.json", {})
    slots: list[dict[str, Any]] = []
    if isinstance(execution, dict):
        for slot in execution.get("slots", []):
            if not isinstance(slot, dict):
                continue
            if scope and str(slot.get("route_id", "")) and str(slot.get("route_id")) not in scope:
                continue
            if unit is not None and (
                not unit.resource_slot_ids
                or str(slot.get("resource_slot_id", "")) not in unit.resource_slot_ids
            ):
                continue
            resolution = slot.get("resolution", {})
            local_paths = (
                [str(item) for item in resolution.get("local_paths", [])]
                if isinstance(resolution, dict)
                else []
            )
            package_name = str(resolution.get("package_name", "")) if resolution else ""
            slots.append(
                {
                    "slot_id": str(slot.get("resource_slot_id", "")),
                    "route_id": str(slot.get("route_id", "")),
                    "required": bool(slot.get("required")),
                    "category": str(slot.get("category", "")),
                    "resolution_type": str(resolution.get("resolution_type", "")),
                    "local_paths": local_paths,
                    "package_name": package_name,
                    "expected_exports": [
                        str(item) for item in resolution.get("expected_exports", []) if str(item)
                    ],
                }
            )

    visual = projections.get("design/visual-direction.json", {})
    # V4 binds every rendered value to the approved site/content contract.
    # A visual-direction pack is implementation guidance and cannot introduce
    # factual source authority. Older packs retain their legacy literal
    # preservation behavior, but elevating visual prose in V4 can create an
    # impossible contract when upstream snapshots disagree about identity.
    must_preserve = (
        []
        if v4
        else _normalized_strings(
            (visual.get("global", {}) or {}).get("must_preserve", [])
            if isinstance(visual, dict)
            else []
        )
    )
    unit_route_ids = (
        list(unit.route_ids) or ([unit.route_id] if unit.route_id else [])
        if unit is not None
        else []
    )
    required_coverage = (
        {
            "content_ids": [
                content_id
                for section_id in unit.section_ids
                for route_id in unit_route_ids
                for content_id in content_keys.get((route_id, section_id), [])
            ],
            "criterion_ids": list(unit.criterion_ids),
            "resource_slot_ids": list(unit.resource_slot_ids),
            "interaction_ids": list(unit.interaction_ids),
        }
        if v4 and unit is not None
        else None
    )
    planned_placements = (
        {item.resource_slot_id: item for item in v4_blueprint.resource_placements}
        if v4_blueprint is not None
        else {}
    )
    planned_slot_ids = set(planned_placements)
    materialized = projections.get("generated/resource-assets.json", {})
    planned_image_assets = [
        {
            "resource_id": str(asset.get("resource_id", "")),
            "route_id": str(asset.get("route_id", "")),
            "section_ids": [str(item) for item in asset.get("section_ids", [])],
            "sizes": str(asset.get("sizes", "100vw")),
            "loading": str(asset.get("loading", "lazy")),
            "fit": str(asset.get("fit", "cover")),
            "focal_position": str(asset.get("focal_position", "center")),
            "alt_policy": str(asset.get("alt_policy", "contextual_description")),
            "manifest_source_count": len(asset.get("sources", [])),
            "element_marker": planned_placements[str(asset.get("resource_id", ""))].element_marker,
            "element_selector": planned_placements[
                str(asset.get("resource_id", ""))
            ].element_selector,
        }
        for asset in (
            materialized.get("image_assets", []) if isinstance(materialized, dict) else []
        )
        if isinstance(asset, dict)
        and str(asset.get("resource_id", "")) in planned_slot_ids
        and (not scope or str(asset.get("route_id", "")) in scope)
        and (unit is None or str(asset.get("resource_id", "")) in set(unit.resource_slot_ids))
    ]
    motion_beats = (
        [
            item.model_dump(mode="json")
            for item in v4_blueprint.motion_beats
            if (item.route_id in scope or not scope)
            and (
                unit is None or (unit.kind == "route_batch" and item.section_id in unit.section_ids)
            )
        ]
        if v4_blueprint is not None
        else []
    )
    distinctive_moves = (
        [
            item.model_dump(mode="json")
            for item in v4_blueprint.distinctive_moves
            if (item.route_id in scope or not scope)
            and (
                unit is None or (unit.kind == "route_batch" and item.section_id in unit.section_ids)
            )
        ]
        if v4_blueprint is not None
        else []
    )

    return {
        "contract_version": CONTRACT_VERSION,
        "operation": operation,
        "unit": (
            {
                "unit_id": unit.unit_id,
                "kind": unit.kind,
                "route_ids": list(unit.route_ids) or ([unit.route_id] if unit.route_id else []),
                "section_ids": list(unit.section_ids),
            }
            if unit is not None
            else None
        ),
        "path_rules": {
            "owned_paths": owned_paths,
            "trusted_files_never_modify": list(_TRUSTED_FILES),
            "trusted_prefixes_never_modify": list(_TRUSTED_PREFIXES),
        },
        "runtime_shell": {
            "router_file": "src/app/AppRouter.tsx",
            "local_resource_helper": "src/app/ResourceUrl.ts#publicResourceUrl",
            "local_route_helper": "src/app/ResourceUrl.ts#publicRouteUrl",
            "required_behaviors": [
                "Render the component selected by src/generated/route-registry.ts for the current pathname.",
                'Render a visible <h1>Page not found</h1> for an unknown pathname; do not substitute route content such as "Projects".',
            ],
        },
        "routes": route_contracts,
        "acceptance_markers": markers,
        "interactions": interactions,
        # Echo contract for _validate_v4_generation_coverage. Keep these exact
        # ordered arrays beside the other mechanically enforced values instead
        # of asking the model to infer a work unit's partition from route-wide
        # criteria or the nested content inventory.
        "required_coverage": required_coverage,
        # Recipes are design guidance, not concrete resource bindings. Only a
        # required local/package resolution creates a source-level hard gate.
        "required_slot_bindings": [
            slot for slot in slots if slot["required"] and slot["resolution_type"] != "local_recipe"
        ],
        "optional_slot_bindings": [slot for slot in slots if not slot["required"]],
        "planned_image_assets": planned_image_assets,
        "motion_beats": motion_beats,
        "distinctive_moves": distinctive_moves,
        "must_preserve_text": must_preserve,
        "network_policy": {
            "approved_urls": _approved_urls(_public_text(projections)),
            "forbidden_runtime_calls": list(_FORBIDDEN_RUNTIME),
        },
        "text_policy": {
            "placeholder_terms_forbidden": list(_PLACEHOLDER_TERMS),
            "ungrounded_copy_rule": (
                "JSX text spans of five or more words must appear (case-insensitive "
                "substring, either direction) inside the approved public content; "
                "spans under five words are permitted as connective micro-labels."
            ),
        },
    }


def render_contract_instructions(contract: dict[str, Any]) -> str:
    """Render the contract as a compact normative block appended to prompts."""

    lines: list[str] = []
    lines.append("<generation-contract>")
    lines.append(
        "These rules are enforced mechanically on your output. Follow them exactly; "
        "each check is a literal string/structural match, not a judgment call."
    )

    path_rules = contract.get("path_rules", {})
    lines.append("")
    lines.append("FILE OPERATIONS")
    lines.append(
        f"- You may only create or replace files under: {', '.join(path_rules.get('owned_paths', [])) or '(none)'}"
    )
    trusted = ", ".join(
        [
            *path_rules.get("trusted_files_never_modify", []),
            *path_rules.get("trusted_prefixes_never_modify", []),
        ]
    )
    lines.append(f"- NEVER write to trusted/pipeline-owned files: {trusted}.")
    lines.append(
        '- operation="create" only for paths NOT in the context\'s existing_files; '
        'operation="replace" only for paths that ARE in existing_files. '
        "existing_files is the ground truth for what exists."
    )
    lines.append(
        "- One file max 256 KiB, UTF-8 (no null bytes), no duplicate paths, no hidden (dot) path parts."
    )

    shell = contract.get("runtime_shell", {})
    if shell:
        lines.append("")
        lines.append(f"RUNTIME SHELL CONTRACT: {shell.get('router_file', '')}")
        if shell.get("local_resource_helper"):
            lines.append(
                "- Resolve browser-served local media through "
                f"{shell.get('local_resource_helper')}; never hardcode a root-relative asset URL."
            )
        if shell.get("local_route_helper"):
            lines.append(
                "- Resolve same-site route href values through "
                f"{shell.get('local_route_helper')} so links work at root and nested preview bases."
            )
        for behavior in shell.get("required_behaviors", []):
            lines.append(f"- {behavior}")

    for route in contract.get("routes", []):
        lines.append("")
        anchor = route.get("anchor_file", "")
        lines.append(f"VERIFICATION ANCHOR: {anchor}")
        if route.get("section_anchors_required", True):
            lines.append(
                "This is a split batch. Every listed owned section file is machine-checked "
                "after your change and must contain its own section contract. The first "
                "file is only the deterministic validation starting point."
            )
        else:
            lines.append(
                "This exact route-composition file is machine-checked after your change. "
                "It MUST itself contain, as literal substrings:"
            )
        lines.append(f'- the route_id string "{route.get("route_id", "")}"')
        section_ids = route.get("section_ids", [])
        if section_ids and route.get("section_anchors_required", True):
            lines.append(
                "- this is a split route batch: each listed owned TSX file is one "
                "independent default-exported section component; each must contain "
                'exactly one route-scoped data-content-id="<section_id>" identity and '
                "must separately implement its exact blueprint section_selector. "
                "Never derive the DOM selector from the content identity or aggregate sections: "
                f"{', '.join(section_ids)}"
            )
            for section in route.get("sections", []):
                lines.append(
                    "- section identity: "
                    f"{section.get('section_id')} -> selector "
                    f"{section.get('section_selector') or '(not supplied)'} -> owner "
                    f"{section.get('owner_file') or '(not supplied)'}"
                )
        route_shell = route.get("route_shell", {})
        if section_ids and route.get("section_anchors_required", True) and route_shell:
            h1_owner = str(route_shell.get("h1_owner", ""))
            if h1_owner in section_ids:
                lines.append(
                    f"- this batch owns the canonical page heading section {h1_owner}; "
                    "that section's owned TSX file must render exactly one visible <h1>, "
                    "and every other owned section must render no h1"
                )
            elif h1_owner:
                lines.append(
                    f"- this batch does not own the canonical page heading section {h1_owner}; "
                    "render no h1 in any owned file"
                )
        if section_ids and not route.get("section_anchors_required", True) and route_shell:
            lines.append(
                "- the trusted RouteShell owns the navigation landmark, but this composer "
                "must supply its navigation prop with one compact <nav> anchor for every "
                "approved section selector below; use literal href values so the source "
                "audit can prove the complete single-page navigation"
            )
            for section in route.get("sections", []):
                selector = str(section.get("section_selector", ""))
                if selector.startswith("#"):
                    lines.append(
                        f'  - {section.get("section_id")}: href="{selector}"; '
                        "use a truthful label of at most three words derived from the section id"
                    )
        markers = [
            item["source_marker"]
            for item in contract.get("acceptance_markers", [])
            if item.get("route_id") == route.get("route_id")
        ]
        if markers:
            lines.append(f"- every source marker token: {', '.join(markers)}")
        route_interactions = [
            item
            for item in contract.get("interactions", [])
            if item.get("route_id") == route.get("route_id")
        ]
        if route_interactions:
            lines.append(
                "- implement each interaction on its actual executable target with both "
                "literal markers on the same JSX opening tag:"
            )
            for item in route_interactions:
                lines.append(
                    f"  - {item.get('interaction_id')}: standard {item.get('attribute')}; "
                    f"blueprint {item.get('literal_marker') or '(none)'}; target "
                    f"{item.get('target_selector') or '(none)'}; outcome "
                    f"{item.get('outcome_selector') or '(none)'}; trigger "
                    f"{item.get('trigger') or '(none)'}; navigation "
                    f"{item.get('expected_navigation') or '(none)'}; state "
                    f"{item.get('expected_state_attribute') or '(none)'}="
                    f"{item.get('expected_state_value') or '(none)'}"
                )
                lines.append(
                    f"    transition: {item.get('state_transition') or '(none)'}; "
                    f"keyboard: {item.get('keyboard_behavior') or '(none)'}; "
                    f"focus: {item.get('focus_behavior') or '(none)'}"
                )
            lines.append(
                "- Do not satisfy an interaction by marking a duplicate navigation link or "
                "another proxy element. Do not use data-interaction-id={...}, helper props, "
                "generated maps, or a shared component to hide either required literal marker."
            )
            lines.append(
                '- A state value described as "true or false" is a boolean range: bind the '
                "state attribute to live boolean state (or a literal boolean). Do not render "
                "those words or invent a data-navigation attribute. Non-navigation triggers "
                "such as disclosures remain on the current route."
            )
        if route.get("verbatim_in_anchor", True):
            lines.append(
                "- every verbatim copy string listed for this route below (embed the copy "
                "directly in this file's JSX; do not merely import it, do not paraphrase, "
                "do not fix grammar or split sentences)"
            )
            for section in route.get("sections", []):
                lines.append(f"  [{section.get('section_id')}]")
                for text in section.get("verbatim_strings", []):
                    lines.append(f"    - {text}")
        elif route.get("content_keys_required"):
            lines.append(
                "- render every approved content key through the trusted typed content module "
                'with a direct contentValue("literal-key") call; do not hide keys behind '
                "aliases or lookups and do not retype approved prose in route source"
            )
            for section in route.get("sections", []):
                lines.append(f"  [{section.get('section_id')}] content keys")
                for content_id in section.get("content_ids", []):
                    lines.append(
                        f'    - {content_id} (literal key and executable contentValue("..."))'
                    )
        elif section_ids:
            lines.append(
                "- import and render the completed section batches in approved order; "
                "their section anchors and verbatim copy remain in those owned modules"
            )

    lines.append("")
    lines.append("COPY POLICY")
    if any(route.get("content_keys_required") for route in contract.get("routes", [])):
        lines.append(
            "- V4 visible copy comes only from the trusted generated-content module. "
            "Use the literal approved content key with contentValue(...); never retype or paraphrase prose."
        )
    else:
        lines.append(
            "- All visible copy comes verbatim from site_contract.public_content. Never "
            "author new sentences of visible text."
        )
    lines.append(f"- {contract.get('text_policy', {}).get('ungrounded_copy_rule', '')}")
    placeholders = ", ".join(contract.get("text_policy", {}).get("placeholder_terms_forbidden", []))
    lines.append(f"- These substrings must not appear anywhere (case-insensitive): {placeholders}.")
    lines.append("- No process.env access in .ts/.tsx files.")

    network = contract.get("network_policy", {})
    approved = network.get("approved_urls", [])
    lines.append("")
    lines.append("NETWORK POLICY (offline site)")
    if approved:
        lines.append(
            "- The ONLY permitted remote URLs are these approved links, allowed solely "
            "as href/src values or plain data literals (they are content, not fetches):"
        )
        for url in approved:
            lines.append(f"    {url}")
    else:
        lines.append("- No remote URLs are approved for this run; none may appear.")
    lines.append(
        "- No other http(s):// or protocol-relative URL anywhere; never call "
        + ", ".join(network.get("forbidden_runtime_calls", []))
        + "."
    )

    planned_images = contract.get("planned_image_assets", [])
    if planned_images:
        lines.append("")
        lines.append("PLANNED LOCAL IMAGE BINDINGS")
        lines.append(
            "Every binding below is a planner-selected placement and must render through "
            "the trusted LocalImage component. It resolves the exact responsive source paths, "
            "dimensions, and formats from the immutable generated resource manifest. Copy the "
            "short resourceId, sizes, loading, fit, focal position, and alt policy exactly. "
            "Omit the sources prop: never transcribe rendition paths or hashes into generated "
            "source and never use acquisition-ledger paths containing a run id."
        )
        for asset in planned_images:
            lines.append(
                f"- resourceId={asset.get('resource_id')}; route={asset.get('route_id')}; "
                f"sections={json.dumps(asset.get('section_ids', []), ensure_ascii=False)}; "
                f"wrapperMarker={asset.get('element_marker')}; "
                f"wrapperSelector={asset.get('element_selector')}; "
                f"sizes={json.dumps(asset.get('sizes', ''), ensure_ascii=False)}; "
                f"loading={asset.get('loading')}; fit={asset.get('fit')}; "
                f"focalPosition={json.dumps(asset.get('focal_position', ''), ensure_ascii=False)}; "
                f"altPolicy={asset.get('alt_policy')}; "
                f"manifestSourceCount={asset.get('manifest_source_count', 0)}"
            )
            if asset.get("alt_policy") == "decorative":
                lines.append('  Use alt="" exactly because this placement is decorative.')
            else:
                lines.append(
                    "  Use a concise non-empty alt grounded in approved content; do not use the "
                    "policy name as alt text."
                )
            lines.append(
                "  Put wrapperMarker literally on the rendered element matched by "
                "wrapperSelector; a comment or unrelated element does not satisfy placement."
            )

    distinctive_moves = contract.get("distinctive_moves", [])
    if distinctive_moves:
        lines.append("")
        lines.append("DISTINCTIVE COMPOSITION MOVES")
        lines.append(
            "Implement each move in its owned section, not as a route comment. Put the exact "
            "runtime marker on the rendered element and make both named selectors expose the "
            "required CSS relationship at every listed viewport."
        )
        lines.append(
            "The required declarations must appear in a literal CSS rule whose selector is "
            "exactly the listed source selector, or that selector qualified by the same "
            "runtime-marker attribute. Put the runtime marker on the same JSX/HTML element "
            "matched by source. A rule on an ancestor or descendant such as `source child` "
            "does not satisfy the move."
        )
        for move in distinctive_moves:
            lines.append(
                f"- {move.get('move_id')}: marker {move.get('runtime_marker')}; "
                f"source {move.get('source_selector')}; target {move.get('target_selector')}; "
                f"relationship {move.get('relationship')}; ratio "
                f"{move.get('minimum_ratio')}..{move.get('maximum_ratio')}; viewports "
                f"{json.dumps(move.get('viewports', []))}; CSS properties "
                f"{json.dumps(move.get('required_css_properties', []))}"
            )

    motion_beats = contract.get("motion_beats", [])
    if motion_beats:
        lines.append("")
        lines.append("EXECUTABLE MOTION BEATS")
        lines.append(
            "Implement every beat as real state change using the exact target marker, target "
            "selector, before/after values, duration range, and easing. A viewport beat must "
            "start from IntersectionObserver-driven state or a CSS view timeline, not merely "
            "when the stylesheet loads. Keep the default/no-JS content readable and add an "
            "explicit prefers-reduced-motion rule that renders the complete final state."
        )
        lines.append(
            "For a viewport beat whose before opacity is 0, the unguarded target selector must "
            "default to opacity: 1. Only place opacity: 0 under the exact progressive selector "
            '[data-motion-ready="true"], and set that attribute with '
            'setAttribute("data-motion-ready", "true") only after confirming '
            "IntersectionObserver support."
        )
        for beat in motion_beats:
            lines.append(
                f"- {beat.get('motion_id')}: marker {beat.get('target_marker')}; target "
                f"{beat.get('target_selector')}; trigger {beat.get('trigger')} at "
                f"{beat.get('trigger_selector')}; duration {beat.get('duration_min_ms')}.."
                f"{beat.get('duration_max_ms')}ms; easing {beat.get('easing')}; properties "
                f"{json.dumps(beat.get('changed_properties', []), ensure_ascii=False, separators=(',', ':'))}; "
                f"reduced motion: {beat.get('reduced_motion_replacement')}"
            )

    required_slots = contract.get("required_slot_bindings", [])
    if required_slots:
        lines.append("")
        lines.append("REQUIRED RESOURCE-SLOT BINDINGS")
        lines.append(
            "Each required slot must be bound by executable source usage. Comments, "
            "slot IDs, manifest text, and prose do not count. Browser-served image/media "
            "slots with a planned LocalImage binding render that trusted component with the "
            "exact resourceId and no sources prop; other local media use publicResourceUrl. "
            "Font slots use the importable generated resource path from CSS; component slots "
            "import and render the local module; package slots import the declared package/export."
        )
        for slot in required_slots:
            lines.append(
                f"- {slot.get('slot_id')} (route {slot.get('route_id') or 'site-wide'}): "
                f"category={slot.get('category', '')}, resolution={slot.get('resolution_type', '')}, "
                f"local paths={', '.join(slot.get('local_paths', [])) or '(none)'}, "
                f"package={slot.get('package_name', '') or '(none)'}, "
                f"exports={', '.join(slot.get('expected_exports', [])) or '(none)'}"
            )

    required_coverage = contract.get("required_coverage")
    if isinstance(required_coverage, dict):
        lines.append("")
        lines.append("V4 SOURCE ENVELOPE COVERAGE")
        lines.append(
            "Copy each complete ordered array below exactly into the matching returned "
            "field. Preserve order and return [] for an empty list; never substitute "
            "route-wide IDs for this unit's assigned partition."
        )
        for field in (
            "content_ids",
            "criterion_ids",
            "resource_slot_ids",
            "interaction_ids",
        ):
            lines.append(
                f"- {field} = {json.dumps(required_coverage.get(field, []), ensure_ascii=False)}"
            )
        lines.append(
            "- A coverage-only repair still requires the complete corrected rejected file "
            "bodies. result=changes with files=[] is invalid because rejected source has "
            "not been accepted into the repository."
        )
        lines.append(
            "- Every content_ids entry assigned to a route batch must also appear as a "
            'direct executable contentValue("literal-id") call in its section owner. '
            "Bind approved non-visible metadata such as kind values to a meaningful data-* "
            "attribute instead of omitting it."
        )

    preserve = contract.get("must_preserve_text", [])
    if preserve:
        lines.append("")
        lines.append("MUST-PRESERVE TEXT (visual contract)")
        lines.append("Each of these strings must appear literally somewhere in the source tree:")
        for text in preserve:
            lines.append(f"- {text}")

    lines.append("")
    lines.append("SELF-CHECK (perform before returning)")
    lines.append(
        "1. Re-read your anchor file and confirm every literal listed above is present "
        "by exact string match. 2. Confirm create/replace matches existing_files. "
        "3. Confirm no unapproved URL and no forbidden runtime call. "
        "4. Fill self_check honestly."
    )
    lines.append("</generation-contract>")
    return "\n".join(lines)


__all__ = [
    "CONTRACT_VERSION",
    "build_generation_contract",
    "render_contract_instructions",
]
