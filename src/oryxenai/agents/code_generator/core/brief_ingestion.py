"""Strict Build Preparation Markdown-brief admission for Code Generator.

Build Preparation owns two human-readable Markdown documents.  Code Generator
stores those documents verbatim in one immutable local envelope, validates the
small fenced JSON indexes, and compiles only the compatibility projections its
existing deterministic planner/build pipeline consumes.  This module never
downloads a resource and never recreates the retired ZIP-pack boundary.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

BRIEF_ENVELOPE_VERSION = "code-generator-brief-envelope-v1"
BRIEF_CONTRACT_VERSION = "build-preparation-brief-v1"
CONTENT_FILENAME = "content-and-narrative-brief.md"
VISUAL_FILENAME = "visual-and-build-brief.md"

_CONTENT_TAG = "build-preparation-content-index"
_VISUAL_TAG = "build-preparation-visual-index"
_SECTION_TAG = "section-content"
_TAGGED_JSON = re.compile(
    r"^```json[ \t]+(?P<tag>[a-z0-9-]+)[ \t]*\r?\n"
    r"(?P<body>.*?)^```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
_SECTION_HEADING = re.compile(r"^###[ \t]+(?P<section>[^\r\n]+?)[ \t]*$", re.MULTILINE)
_ROUTE_HEADING = re.compile(
    r"^##[ \t]+Route:[ \t]*(?P<path>\S+)[ \t]+\((?P<route>[^)]+)\)[ \t]*$",
    re.MULTILINE,
)
_HTTPS_RESOURCE_HOSTS = {
    "pixabay": {"pixabay.com", "www.pixabay.com", "cdn.pixabay.com"},
    "pexels": {"pexels.com", "www.pexels.com", "images.pexels.com"},
    "fontsource": {"cdn.jsdelivr.net"},
    "magicui": {"magicui.design", "www.magicui.design"},
    "shadcn": {"ui.shadcn.com"},
}


class BriefContractError(ValueError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def make_brief_envelope(content_markdown: str, visual_markdown: str) -> bytes:
    """Serialize both verbatim briefs into a deterministic immutable envelope."""

    payload = {
        "schema_version": BRIEF_ENVELOPE_VERSION,
        "content_brief_markdown": _nonempty_text(content_markdown, "content brief"),
        "visual_brief_markdown": _nonempty_text(visual_markdown, "visual brief"),
    }
    # Validate before anything is persisted so malformed uploads never become
    # admitted source references.
    compile_briefs(payload["content_brief_markdown"], payload["visual_brief_markdown"])
    return canonical_json(payload)


def parse_brief_envelope(data: bytes) -> tuple[str, str]:
    try:
        payload = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BriefContractError(
            "BRIEF_ENVELOPE_INVALID", "The brief envelope is not valid UTF-8 JSON."
        ) from exc
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "content_brief_markdown",
        "visual_brief_markdown",
    }:
        raise BriefContractError(
            "BRIEF_ENVELOPE_SHAPE_INVALID",
            "The brief envelope must contain only its version and the two Markdown briefs.",
        )
    if payload.get("schema_version") != BRIEF_ENVELOPE_VERSION:
        raise BriefContractError(
            "BRIEF_ENVELOPE_VERSION_UNSUPPORTED",
            "The brief envelope version is not supported by this Code Generator.",
        )
    return (
        _nonempty_text(payload.get("content_brief_markdown"), "content brief"),
        _nonempty_text(payload.get("visual_brief_markdown"), "visual brief"),
    )


def compile_brief_envelope(
    data: bytes,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    content_markdown, visual_markdown = parse_brief_envelope(data)
    return compile_briefs(content_markdown, visual_markdown)


def compile_briefs(
    content_markdown: str, visual_markdown: str
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    """Validate both contracts and compile the existing deterministic inputs."""

    # Uploads arrive as bytes and therefore preserve Windows CRLF line endings,
    # while ``Path.read_text`` normalizes them on some platforms.  Parse a
    # canonical LF view so fenced JSON and headings have identical semantics
    # regardless of transport, but retain the verbatim documents for their
    # provenance hashes and immutable envelope storage.
    content_source = content_markdown
    visual_source = visual_markdown
    content_markdown = _normalize_markdown(content_markdown)
    visual_markdown = _normalize_markdown(visual_markdown)

    content_index = _tagged_index(content_markdown, _CONTENT_TAG)
    visual_index = _tagged_index(visual_markdown, _VISUAL_TAG)
    _validate_indexes(content_index, visual_index)

    routes = [item for item in content_index["routes"] if isinstance(item, dict)]
    section_content = _section_content(content_markdown, routes)
    route_purposes = _route_purposes(content_markdown)
    navigation = _navigation_contract(content_index, routes)
    public_content: list[dict[str, Any]] = []
    site_routes: list[dict[str, Any]] = []
    criteria: list[dict[str, str]] = []
    for route in routes:
        route_id = str(route["route_id"])
        section_ids = [str(item) for item in route["sections"]]
        public_sections: list[dict[str, Any]] = []
        for position, section_id in enumerate(section_ids):
            item = section_content[section_id]
            public_sections.append(
                {
                    "section_id": section_id,
                    "purpose": item["purpose"],
                    "content": item["content"],
                    "claim_ids": [],
                    "priority": "primary" if position < 2 else "supporting",
                }
            )
            criteria.append(
                {
                    "criterion_id": f"criterion:{section_id}",
                    "route_id": route_id,
                    "section_id": section_id,
                    "text": item["purpose"] or f"Render approved section {section_id}.",
                }
            )
        site_routes.append(
            {
                "route_id": route_id,
                "path": str(route["path"]),
                "title": str(route["title"]),
                "purpose": route_purposes.get(route_id, str(route["title"])),
                "storage_key": f"routes/{_semantic_id(route_id)}",
                "section_sequence": section_ids,
                "sections": [{"section_id": section_id} for section_id in section_ids],
            }
        )
        public_content.append({"route_id": route_id, "sections": public_sections})

    content_hash = sha256_bytes(content_source.encode("utf-8"))
    visual_hash = sha256_bytes(visual_source.encode("utf-8"))
    contract_hash = sha256_bytes(
        canonical_json(
            {
                "content_index": content_index,
                "visual_index": visual_index,
                "content_brief_sha256": content_hash,
                "visual_brief_sha256": visual_hash,
            }
        )
    )
    target_id = str(visual_index["target_contract"])
    visual_prose = _visual_prose(visual_markdown)
    slots, resource_needs, decisions = _resource_contracts(visual_index, routes)
    site_contract = {
        "schema_version": BRIEF_CONTRACT_VERSION,
        "routes": site_routes,
        "public_content": public_content,
        "facts": [],
        "criteria": criteria,
        "runtime_requirements": [
            {"runtime_id": "runtime:offline", "key": "offline", "value": True},
            {
                "runtime_id": "runtime:closed-navigation",
                "key": "closed_navigation",
                "value": True,
            },
        ],
        "freedoms": [
            {
                "freedom_id": "freedom:composition",
                "key": "composition",
                "value": "Code Generator may adapt visual suggestions without changing approved copy.",
            }
        ],
        "navigation_contract": navigation,
        "public_content_manifest": {
            "nav": [
                {
                    "label": _navigation_label(item["destination_id"], routes),
                    "target": item["destination_id"],
                    "href": item["href"],
                }
                for item in navigation["resolved_destinations"]
            ]
        },
        "source": {
            "run_id": str(content_index["run_id"]),
            "content_architect_content_hash": str(
                content_index.get("content_architect_content_hash", "")
            ),
            "content_brief_sha256": content_hash,
        },
    }
    visual_projection = {
        "schema_version": BRIEF_CONTRACT_VERSION,
        "navigation_contract": navigation,
        "global": {
            "visual_language": {"approved_brief": visual_prose},
            "shared_visual_systems": {
                "quality_floor": (
                    "Create an art-directed editorial portfolio with deliberate hierarchy, "
                    "distinct section compositions, refined typography, coherent image treatment, "
                    "and generous responsive spacing; reject generic repeated card grids."
                )
            },
            "navigation_direction": navigation,
            "motion_system": {
                "global_character": (
                    "Purposeful entrance and viewport reveals, tactile focus/hover states, and one "
                    "coherent scroll narrative; transform/opacity only where practical."
                ),
                "reduced_motion": (
                    "Every animated state has an immediate static equivalent under "
                    "prefers-reduced-motion: reduce."
                ),
            },
            "interaction_system": {
                "requirements": (
                    "Keyboard, touch, and pointer states must expose the same content and outcomes."
                )
            },
            "accessibility_and_performance": {
                "requirements": (
                    "Semantic landmarks, visible focus, readable contrast, responsive image sizing, "
                    "lazy below-fold media, no horizontal overflow, and no runtime network assets."
                )
            },
            "must_preserve": ["Approved copy and closed navigation destinations"],
            "must_not_fabricate": [
                "Project evidence, metrics, testimonials, clients, pages, or navigation destinations"
            ],
            "compiler_handoff": {"offline_runtime": True, "target": target_id},
        },
        "routes": [
            {
                "route_id": str(route["route_id"]),
                "path": str(route["path"]),
                "acceptance_criteria": [
                    criterion["text"]
                    for criterion in criteria
                    if criterion["route_id"] == str(route["route_id"])
                ],
                "direction": {
                    "approved_brief": visual_prose,
                    "responsive_summary": (
                        "Preserve hierarchy and narrative order; collapse complex compositions into "
                        "a readable single flow without losing controls or imagery."
                    ),
                },
            }
            for route in routes
        ],
        "assets": [],
        "resources": decisions,
    }
    execution_contract = {
        "schema_version": BRIEF_CONTRACT_VERSION,
        "slots": slots,
        "execution_gaps": [
            {
                "slot_id": str(slot["resource_slot_id"]),
                "reason": "No primary candidate was selected; use the declared semantic fallback.",
            }
            for slot in slots
            if slot["resolution"]["resolution_type"] == "execution_gap"
        ],
        "policy": {
            "runtime_network_fetch_allowed": False,
            "suggestions_are_optional": True,
            "allowed_resolution_types": ["deferred_materialized", "execution_gap"],
        },
    }
    projections: dict[str, dict[str, Any]] = {
        "site/contract.json": site_contract,
        "design/visual-direction.json": visual_projection,
        "resources/projection.json": {
            "schema_version": BRIEF_CONTRACT_VERSION,
            "resources": decisions,
            "resource_needs": resource_needs,
        },
        "execution/contract.json": execution_contract,
        "resources/ledger.json": {
            "schema_version": BRIEF_CONTRACT_VERSION,
            "policy": {
                "runtime_network_fetch_allowed": False,
                "unlisted_resource_ids_are_forbidden": True,
            },
            "resource_decisions": decisions,
            "slots": [
                {
                    "resource_slot_id": slot["resource_slot_id"],
                    "resolution_type": slot["resolution"]["resolution_type"],
                }
                for slot in slots
            ],
        },
        "provenance/targets.json": {
            "schema_version": BRIEF_CONTRACT_VERSION,
            "target": {
                "target_id": target_id,
                "allowed_dependencies": [
                    "react",
                    "react-dom",
                    *[str(item) for item in visual_index.get("recommended_dependencies", [])],
                ],
                "forbidden_runtime_capabilities": ["remote-fonts", "remote-runtime-assets"],
            },
        },
        "provenance/approvals.json": {
            "schema_version": BRIEF_CONTRACT_VERSION,
            "content_architect_content_hash": str(
                content_index.get("content_architect_content_hash", "")
            ),
            "source_projection_hash": contract_hash,
            "approved": True,
        },
        "handoff-report.json": {
            "schema_version": BRIEF_CONTRACT_VERSION,
            "handoff_eligible": True,
            "status": "ready_for_handoff",
            "issues": [],
        },
        "resources/recipes/manifest.json": {
            "schema_version": BRIEF_CONTRACT_VERSION,
            "recipes": [],
        },
    }
    projection_hashes = {
        name: sha256_bytes(canonical_json(value)) for name, value in sorted(projections.items())
    }
    receipt = {
        "receipt_id": f"brief-{contract_hash[:20]}",
        "admitted_identity": contract_hash,
        "source_sha256": sha256_bytes(
            canonical_json(
                {
                    "schema_version": BRIEF_ENVELOPE_VERSION,
                    "content_brief_markdown": content_source,
                    "visual_brief_markdown": visual_source,
                }
            )
        ),
        "content_brief_sha256": content_hash,
        "visual_brief_sha256": visual_hash,
        "contract_hash": contract_hash,
        "projection_hashes": projection_hashes,
        "route_ids": [str(item["route_id"]) for item in routes],
        "target_id": target_id,
        "source_version": BRIEF_CONTRACT_VERSION,
        "schema_version": BRIEF_ENVELOPE_VERSION,
    }
    summary = {
        "run_id": str(content_index["run_id"]),
        "route_count": len(routes),
        "section_count": sum(len(item["sections"]) for item in routes),
        "resource_count": len(visual_index.get("resources", [])),
        "component_count": len(visual_index.get("components", [])),
        "content_brief_sha256": content_hash,
        "visual_brief_sha256": visual_hash,
        "contract_hash": contract_hash,
        "target_contract": target_id,
        "navigation_closed": True,
    }
    return receipt, projections, summary


def _normalize_markdown(markdown: str) -> str:
    """Return the parser view shared by LF and CRLF Markdown uploads."""

    return markdown.replace("\r\n", "\n").replace("\r", "\n")


def _tagged_index(markdown: str, required_tag: str) -> dict[str, Any]:
    matches = [
        match for match in _TAGGED_JSON.finditer(markdown) if match.group("tag") == required_tag
    ]
    if len(matches) != 1:
        raise BriefContractError(
            "BRIEF_INDEX_CARDINALITY",
            f"The Markdown brief must contain exactly one {required_tag} JSON fence.",
            details={"tag": required_tag, "observed": len(matches)},
        )
    try:
        value = json.loads(matches[0].group("body"))
    except json.JSONDecodeError as exc:
        raise BriefContractError(
            "BRIEF_INDEX_INVALID_JSON", f"The {required_tag} fence is not valid JSON."
        ) from exc
    if not isinstance(value, dict):
        raise BriefContractError(
            "BRIEF_INDEX_INVALID_SHAPE", f"The {required_tag} fence must be a JSON object."
        )
    return value


def _validate_indexes(content: dict[str, Any], visual: dict[str, Any]) -> None:
    if content.get("kind") != "content_index" or visual.get("kind") != "visual_index":
        raise BriefContractError(
            "BRIEF_INDEX_KIND_INVALID", "The two brief indexes have invalid kind discriminators."
        )
    run_id = str(content.get("run_id", "")).strip()
    if not run_id or run_id != str(visual.get("run_id", "")).strip():
        raise BriefContractError(
            "BRIEF_RUN_ID_MISMATCH", "Content and visual briefs must identify the same build run."
        )
    routes = content.get("routes")
    if not isinstance(routes, list) or not routes:
        raise BriefContractError("BRIEF_ROUTES_EMPTY", "The content brief has no routes.")
    route_ids: list[str] = []
    section_ids: list[str] = []
    paths: list[str] = []
    for route in routes:
        if not isinstance(route, dict):
            raise BriefContractError("BRIEF_ROUTE_INVALID", "A route index entry is malformed.")
        route_id = str(route.get("route_id", "")).strip()
        path = str(route.get("path", "")).strip()
        title = str(route.get("title", "")).strip()
        sections = route.get("sections")
        if (
            not route_id
            or not title
            or not _safe_route_path(path)
            or not isinstance(sections, list)
            or not sections
        ):
            raise BriefContractError(
                "BRIEF_ROUTE_INVALID", "Every route needs an ID, safe path, title, and sections."
            )
        route_ids.append(route_id)
        paths.append(path)
        for section in sections:
            section_id = str(section).strip()
            if not section_id or not section_id.startswith(f"{route_id}:"):
                raise BriefContractError(
                    "BRIEF_SECTION_SCOPE_INVALID",
                    "Every section ID must be non-empty and namespaced by its route ID.",
                )
            section_ids.append(section_id)
    if len(route_ids) != len(set(route_ids)) or len(paths) != len(set(paths)):
        raise BriefContractError("BRIEF_ROUTE_DUPLICATE", "Route IDs and paths must be unique.")
    if len(section_ids) != len(set(section_ids)):
        raise BriefContractError("BRIEF_SECTION_DUPLICATE", "Section IDs must be unique.")
    visual_routes = visual.get("routes")
    if not isinstance(visual_routes, list) or {str(item) for item in visual_routes} != set(
        route_ids
    ):
        raise BriefContractError(
            "BRIEF_VISUAL_ROUTE_MISMATCH", "Visual brief routes must exactly match content routes."
        )
    navigation = content.get("navigation_contract")
    expected_destinations = [*route_ids, *section_ids]
    if not isinstance(navigation, dict) or navigation.get("closed") is not True:
        raise BriefContractError(
            "BRIEF_NAVIGATION_NOT_CLOSED", "Code Generator requires a closed navigation contract."
        )
    allowed = navigation.get("allowed_destinations")
    if (
        not isinstance(allowed, list)
        or len(allowed) != len({str(item) for item in allowed})
        or {str(item) for item in allowed} != set(expected_destinations)
    ):
        raise BriefContractError(
            "BRIEF_NAVIGATION_SCOPE_INVALID",
            "Closed navigation destinations must exactly equal the indexed routes and sections.",
        )
    target = str(visual.get("target_contract", "")).strip()
    if target != "react-vite-v1":
        raise BriefContractError(
            "BRIEF_TARGET_UNSUPPORTED", "Only the configured React/Vite target is supported."
        )
    for collection, candidates_key, primary_key in (
        (visual.get("resources", []), "candidates", "primary_candidate_index"),
        (visual.get("components", []), "suggestions", "primary_suggestion_index"),
    ):
        if not isinstance(collection, list):
            raise BriefContractError("BRIEF_RESOURCES_INVALID", "Resource indexes must be arrays.")
        for item in collection:
            if not isinstance(item, dict) or not str(item.get("role_id", "")).strip():
                raise BriefContractError(
                    "BRIEF_RESOURCE_INVALID", "Every resource entry needs a stable role ID."
                )
            candidates = item.get(candidates_key)
            primary = item.get(primary_key)
            if not isinstance(candidates, list) or (
                primary is not None
                and (not isinstance(primary, int) or primary < 0 or primary >= len(candidates))
            ):
                raise BriefContractError(
                    "BRIEF_PRIMARY_CANDIDATE_INVALID",
                    "A primary resource index is outside its candidate list.",
                )
            if primary is not None:
                candidate = candidates[primary]
                if not isinstance(candidate, dict):
                    raise BriefContractError(
                        "BRIEF_RESOURCE_INVALID", "The selected resource candidate is malformed."
                    )
                provider = str(candidate.get("provider", "")).casefold()
                url = str(candidate.get("url") or candidate.get("item_url") or "")
                _trusted_https_url(provider, url)
                additional = candidate.get("additional_urls", {})
                if isinstance(additional, dict):
                    for extra_url in additional.values():
                        _trusted_https_url(provider, str(extra_url))


def _section_content(markdown: str, routes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    expected = [str(section) for route in routes for section in route["sections"]]
    matches = list(_SECTION_HEADING.finditer(markdown))
    result: dict[str, dict[str, Any]] = {}
    for index, match in enumerate(matches):
        section_id = match.group("section").strip()
        if section_id not in expected:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        fragment = markdown[match.end() : end]
        blocks = [
            item for item in _TAGGED_JSON.finditer(fragment) if item.group("tag") == _SECTION_TAG
        ]
        if len(blocks) != 1:
            raise BriefContractError(
                "BRIEF_SECTION_CONTENT_CARDINALITY",
                f"Section {section_id} must contain exactly one section-content JSON fence.",
            )
        try:
            content = json.loads(blocks[0].group("body"))
        except json.JSONDecodeError as exc:
            raise BriefContractError(
                "BRIEF_SECTION_CONTENT_INVALID", f"Section {section_id} contains invalid JSON."
            ) from exc
        if not isinstance(content, dict) or not content:
            raise BriefContractError(
                "BRIEF_SECTION_CONTENT_INVALID",
                f"Section {section_id} content must be a non-empty JSON object.",
            )
        purpose_match = re.search(r"\*([^*\r\n]+)\*", fragment[: blocks[0].start()])
        result[section_id] = {
            "purpose": purpose_match.group(1).strip() if purpose_match else "",
            "content": content,
        }
    if set(result) != set(expected):
        missing = sorted(set(expected) - set(result))
        raise BriefContractError(
            "BRIEF_SECTION_CONTENT_COVERAGE",
            "The Markdown body must contain exactly one content block for every indexed section.",
            details={"missing": ",".join(missing)},
        )
    return result


def _route_purposes(markdown: str) -> dict[str, str]:
    matches = list(_ROUTE_HEADING.finditer(markdown))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        fragment = markdown[match.end() : end]
        purpose = re.search(r"\*Purpose:[ \t]*(?P<value>[^*]+)\*", fragment)
        result[match.group("route").strip()] = purpose.group("value").strip() if purpose else ""
    return result


def _navigation_contract(
    content_index: dict[str, Any], routes: list[dict[str, Any]]
) -> dict[str, Any]:
    allowed = [str(item) for item in content_index["navigation_contract"]["allowed_destinations"]]
    route_by_id = {str(route["route_id"]): route for route in routes}
    section_to_route = {
        str(section): str(route["route_id"]) for route in routes for section in route["sections"]
    }
    resolved: list[dict[str, str]] = []
    for destination in allowed:
        if destination in route_by_id:
            href = str(route_by_id[destination]["path"])
            kind = "route"
        else:
            route_id = section_to_route[destination]
            route_path = str(route_by_id[route_id]["path"])
            anchor = _section_anchor(destination)
            href = f"#{anchor}" if route_path == "/" else f"{route_path}#{anchor}"
            kind = "section"
        resolved.append({"destination_id": destination, "kind": kind, "href": href})
    return {
        "closed": True,
        "allowed_destinations": allowed,
        "allowed_hrefs": [item["href"] for item in resolved],
        "resolved_destinations": resolved,
    }


def _resource_contracts(
    visual_index: dict[str, Any], routes: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    route_sections = {
        str(route["route_id"]): [str(item) for item in route["sections"]] for route in routes
    }
    slots: list[dict[str, Any]] = []
    needs: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    entries = [
        (item, "resource") for item in visual_index.get("resources", []) if isinstance(item, dict)
    ] + [
        (item, "component") for item in visual_index.get("components", []) if isinstance(item, dict)
    ]
    seen: set[str] = set()
    for item, entry_kind in entries:
        slot_id = str(item["role_id"])
        if slot_id in seen:
            raise BriefContractError(
                "BRIEF_RESOURCE_ROLE_DUPLICATE", "Resource and component role IDs must be unique."
            )
        seen.add(slot_id)
        route_ids = [str(value) for value in item.get("route_ids", [])]
        if not route_ids or any(route_id not in route_sections for route_id in route_ids):
            raise BriefContractError(
                "BRIEF_RESOURCE_ROUTE_INVALID", "A resource role references an unknown route."
            )
        route_id = route_ids[0]
        section_ids = _role_sections(slot_id, route_id, route_sections[route_id])
        candidates_key = "candidates" if entry_kind == "resource" else "suggestions"
        primary_key = (
            "primary_candidate_index" if entry_kind == "resource" else "primary_suggestion_index"
        )
        candidates = item.get(candidates_key, [])
        primary_index = item.get(primary_key)
        selected = (
            candidates[primary_index]
            if isinstance(primary_index, int)
            and isinstance(candidates, list)
            and primary_index < len(candidates)
            and isinstance(candidates[primary_index], dict)
            else None
        )
        category = str(item.get("category", "")) if entry_kind == "resource" else "component_source"
        purpose = str(item.get("purpose", "")).strip()
        guidance = str(item.get("guidance", "")).strip()
        resolution = _resolution(selected, category, entry_kind, guidance)
        slot = {
            "resource_slot_id": slot_id,
            "category": category,
            "route_id": route_id,
            "scene_ids": [],
            "section_ids": section_ids,
            "component_placement": purpose,
            # Brief resources are candidates and suggestions, never mandatory
            # evidence.  A failed fetch therefore degrades honestly instead of
            # blocking a complete portfolio build.
            "required": False,
            "source_ids": [str(item.get("need_id", ""))],
            "criterion_ids": [f"criterion:{section}" for section in section_ids],
            "rationale": " ".join(value for value in (purpose, guidance) if value),
            "provenance": "build_preparation_brief",
            "resolution": resolution,
        }
        slots.append(slot)
        needs.append(
            {
                "need_id": str(item.get("need_id", slot_id)),
                "role_id": slot_id,
                "category": category,
                "purpose": purpose,
                "guidance": guidance,
                "route_ids": route_ids,
                "section_ids": section_ids,
                "required": False,
                "fallback": resolution["fallback_behavior"],
            }
        )
        decisions.append(
            {
                "resource_slot_id": slot_id,
                "need_id": str(item.get("need_id", slot_id)),
                "category": category,
                "purpose": purpose,
                "guidance": guidance,
                "selected": selected or {},
                "resolution_type": resolution["resolution_type"],
            }
        )
    return slots, needs, decisions


def _resolution(
    selected: dict[str, Any] | None, category: str, entry_kind: str, guidance: str
) -> dict[str, Any]:
    fallback = (
        "Use a semantic, keyboard-accessible local component without the suggested effect."
        if entry_kind == "component"
        else "Use an art-directed local composition without external media."
    )
    if category.casefold() == "font":
        fallback = "Use the configured system sans-serif stack without a runtime font request."
    if selected is None:
        return {
            "resolution_type": "execution_gap",
            "resource_id": "",
            "provider": "",
            "provider_asset_id": "",
            "source_reference": "",
            "direct_source_url": "",
            "direct_source_urls": {},
            "license": "",
            "license_reference": "",
            "dependencies": [],
            "registry_dependencies": [],
            "expected_exports": [],
            "font_family": "",
            "font_weights": [],
            "fallback_behavior": fallback,
            "responsive_behavior": guidance or "Preserve meaning and hierarchy at every viewport.",
            "reduced_motion_behavior": "Use the immediate static state.",
        }
    provider = str(selected.get("provider", "")).casefold()
    source_url = str(selected.get("url") or selected.get("item_url") or "")
    additional_urls = {
        str(key): str(value)
        for key, value in dict(selected.get("additional_urls", {}) or {}).items()
    }
    if category.casefold() == "font":
        direct_urls = {"400-normal": source_url, **additional_urls}
        font_family = str(selected.get("title") or selected.get("provider_asset_id") or "")
        font_weights = sorted({key.split("-", 1)[0] for key in direct_urls})
        # The bytes are still fetched only during Code Generator acquisition,
        # but the workspace needs stable intended paths before planning.  The
        # FontAdapter's hash-prefixed download names end with these variant
        # names, so workspace materialization can safely remap them without
        # putting remote URLs or bytes in the Build Preparation brief.
        font_id = _semantic_id(str(selected.get("provider_asset_id") or font_family))
        local_paths = []
        for variant in sorted(direct_urls):
            if not re.fullmatch(r"[0-9]+-(?:normal|italic|oblique)", variant):
                continue
            suffix = Path(urlsplit(str(direct_urls[variant])).path).suffix.casefold()
            if suffix not in {".woff", ".woff2"}:
                suffix = ".woff2"
            local_paths.append(f"resources/fonts/{font_id}/{variant}{suffix}")
    else:
        direct_urls = additional_urls
        font_family = ""
        font_weights = []
        local_paths = []
    dependencies = [str(value) for value in selected.get("dependencies", []) if str(value)]
    registry_dependencies = [
        str(value) for value in selected.get("registry_dependencies", []) if str(value)
    ]
    return {
        "resolution_type": "deferred_materialized",
        "resource_id": str(selected.get("provider_asset_id") or selected.get("name") or ""),
        "provider": provider,
        "provider_asset_id": str(selected.get("provider_asset_id") or selected.get("name") or ""),
        "source_reference": source_url,
        "direct_source_url": source_url,
        "direct_source_urls": direct_urls,
        "license": str(selected.get("license", "")),
        "license_reference": str(selected.get("license_reference", "")),
        "release_pin": sha256_bytes(canonical_json(selected))[:16],
        "dependencies": dependencies,
        "registry_dependencies": registry_dependencies,
        "expected_exports": [],
        "font_family": font_family,
        "font_weights": font_weights,
        "local_paths": local_paths,
        "fallback_behavior": fallback,
        "responsive_behavior": guidance or "Preserve meaning and hierarchy at every viewport.",
        "reduced_motion_behavior": "Remove transforms and reveal the final static state immediately.",
    }


def _role_sections(role_id: str, route_id: str, route_sections: list[str]) -> list[str]:
    matches = [section for section in route_sections if f":{section}:" in f":{role_id}:"]
    if matches:
        return matches
    return list(route_sections) if "font" in role_id.casefold() else []


def _visual_prose(markdown: str) -> str:
    # The reference tables duplicate structured indexes and consume planner
    # context without adding direction.  Keep the authored design guidance and
    # strip only the machine fence plus duplicated appendix.
    without_index = _TAGGED_JSON.sub(
        lambda match: "" if match.group("tag") == _VISUAL_TAG else match.group(0), markdown
    )
    appendix = without_index.find("\n## Resource guidance (reference table)")
    value = without_index[:appendix] if appendix >= 0 else without_index
    return value.strip()


def _trusted_https_url(provider: str, url: str) -> None:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").casefold()
    allowed = _HTTPS_RESOURCE_HOSTS.get(provider)
    if parsed.scheme != "https" or not host or allowed is None or host not in allowed:
        raise BriefContractError(
            "BRIEF_RESOURCE_URL_UNTRUSTED",
            "A selected resource URL does not match its approved HTTPS provider host.",
            details={"provider": provider, "host": host},
        )


def _safe_route_path(value: str) -> bool:
    return (
        bool(value)
        and value.startswith("/")
        and "\\" not in value
        and "//" not in value
        and ".." not in value.split("/")
        and "?" not in value
        and "#" not in value
        and not any(ord(char) < 32 for char in value)
    )


def _section_anchor(section_id: str) -> str:
    return _semantic_id(section_id.split(":", 1)[-1])


def _semantic_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9-]+", "-", value.casefold()).strip("-")
    if not normalized:
        raise BriefContractError("BRIEF_ID_INVALID", "A brief identifier is not CSS-safe.")
    return normalized


def _navigation_label(destination: str, routes: list[dict[str, Any]]) -> str:
    route = next((item for item in routes if str(item["route_id"]) == destination), None)
    if route is not None:
        return str(route["title"])
    return destination.split(":", 1)[-1].replace("-", " ").title()


def _nonempty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BriefContractError("BRIEF_MISSING", f"The {label} is empty or missing.")
    return value


__all__ = [
    "BRIEF_CONTRACT_VERSION",
    "BRIEF_ENVELOPE_VERSION",
    "CONTENT_FILENAME",
    "VISUAL_FILENAME",
    "BriefContractError",
    "compile_brief_envelope",
    "compile_briefs",
    "make_brief_envelope",
    "parse_brief_envelope",
    "sha256_bytes",
]
