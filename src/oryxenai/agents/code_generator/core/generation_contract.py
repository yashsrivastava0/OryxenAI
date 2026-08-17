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

import re
from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import SitePlan, WorkUnit

CONTRACT_VERSION = "code-generator-generation-contract-v1"

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

    route_contracts: list[dict[str, Any]] = []
    for route_id in scope:
        route = routes_by_id.get(route_id, {})
        storage_key = _storage_key(route, route_id)
        anchor_file = f"src/routes/{storage_key}/index.tsx"
        content_pack = content_by_route.get(route_id, {})
        sections: list[dict[str, Any]] = []
        verbatim: list[str] = []
        for section in content_pack.get("sections", []) if isinstance(content_pack, dict) else []:
            if not isinstance(section, dict):
                continue
            section_id = str(section.get("section_id", ""))
            prose = [
                text
                for text in _normalized_strings(section.get("content", {}))
                # Prose filter mirrors final_source_validation exactly:
                # multi-word strings of six or more characters.
                if " " in text and len(text) >= 6
            ]
            if section_id:
                sections.append({"section_id": section_id, "verbatim_strings": prose})
            verbatim.extend(prose)
        route_contracts.append(
            {
                "route_id": route_id,
                "route_path": str(route.get("path", "")),
                "anchor_file": anchor_file,
                "section_ids": [item["section_id"] for item in sections],
                "sections": sections,
                "verbatim_copy": sorted(set(verbatim))[:_MAX_VERBATIM_STRINGS],
            }
        )

    markers = [
        {
            "route_id": coverage.route_id,
            "criterion_id": coverage.criterion_id,
            "source_marker": coverage.source_marker,
        }
        for coverage in plan.acceptance_coverage
        if coverage.route_id in scope or not scope
    ]
    interactions = [
        {
            "route_id": interaction.route_id,
            "interaction_id": interaction.interaction_id,
            "attribute": f'data-interaction-id="{interaction.interaction_id}"',
        }
        for interaction in plan.interactions
        if interaction.route_id in scope or not scope
    ]

    execution = projections.get("execution/contract.json", {})
    slots: list[dict[str, Any]] = []
    if isinstance(execution, dict):
        for slot in execution.get("slots", []):
            if not isinstance(slot, dict):
                continue
            if scope and str(slot.get("route_id", "")) and str(slot.get("route_id")) not in scope:
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
    must_preserve = _normalized_strings(
        (visual.get("global", {}) or {}).get("must_preserve", [])
        if isinstance(visual, dict)
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
            "required_behaviors": [
                "Render the component selected by src/generated/route-registry.ts for the current pathname.",
                'Render a visible <h1>Page not found</h1> for an unknown pathname; do not substitute route content such as "Projects".',
            ],
        },
        "routes": route_contracts,
        "acceptance_markers": markers,
        "interactions": interactions,
        # Recipes are design guidance, not concrete resource bindings. Only a
        # required local/package resolution creates a source-level hard gate.
        "required_slot_bindings": [
            slot for slot in slots if slot["required"] and slot["resolution_type"] != "local_recipe"
        ],
        "optional_slot_bindings": [slot for slot in slots if not slot["required"]],
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
        for behavior in shell.get("required_behaviors", []):
            lines.append(f"- {behavior}")

    for route in contract.get("routes", []):
        lines.append("")
        anchor = route.get("anchor_file", "")
        lines.append(f"VERIFICATION ANCHOR: {anchor}")
        lines.append(
            "This exact file is machine-checked after your change. It MUST itself contain, "
            "as literal substrings:"
        )
        lines.append(f'- the route_id string "{route.get("route_id", "")}"')
        section_ids = route.get("section_ids", [])
        if section_ids:
            lines.append(
                "- every section_id twice: as a literal string AND as a wrapper "
                'attribute data-content-id="<section_id>" on that section\'s '
                f'containing element (e.g. <section data-content-id="home:hero">): {", ".join(section_ids)}'
            )
        markers = [
            item["source_marker"]
            for item in contract.get("acceptance_markers", [])
            if item.get("route_id") == route.get("route_id")
        ]
        if markers:
            lines.append(f"- every source marker token: {', '.join(markers)}")
        attributes = [
            item["attribute"]
            for item in contract.get("interactions", [])
            if item.get("route_id") == route.get("route_id")
        ]
        if attributes:
            lines.append(f"- one attribute per interaction: {' '.join(attributes)}")
            lines.append(
                "- Write every interaction attribute literally in this index.tsx file. "
                "Do not use data-interaction-id={...}, helper props, generated maps, "
                "or a shared component to hide the required literal attribute."
            )
        lines.append(
            "- every verbatim copy string listed for this route below (embed the copy "
            "directly in this file's JSX; do not merely import it, do not paraphrase, "
            "do not fix grammar or split sentences)"
        )
        for section in route.get("sections", []):
            lines.append(f"  [{section.get('section_id')}]")
            for text in section.get("verbatim_strings", []):
                lines.append(f"    - {text}")

    lines.append("")
    lines.append("COPY POLICY")
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

    required_slots = contract.get("required_slot_bindings", [])
    if required_slots:
        lines.append("")
        lines.append("REQUIRED RESOURCE-SLOT BINDINGS")
        lines.append(
            "Each required slot must be bound by executable source usage. Comments, "
            "slot IDs, manifest text, and prose do not count. Image/media slots "
            "must use their local /resources/pack URL in JSX/CSS; component slots "
            "must import and render the local module; package slots must import the "
            "declared package/export."
        )
        for slot in required_slots:
            lines.append(
                f"- {slot.get('slot_id')} (route {slot.get('route_id') or 'site-wide'}): "
                f"category={slot.get('category', '')}, resolution={slot.get('resolution_type', '')}, "
                f"local paths={', '.join(slot.get('local_paths', [])) or '(none)'}, "
                f"package={slot.get('package_name', '') or '(none)'}, "
                f"exports={', '.join(slot.get('expected_exports', [])) or '(none)'}"
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
