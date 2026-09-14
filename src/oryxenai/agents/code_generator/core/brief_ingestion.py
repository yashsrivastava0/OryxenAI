"""Strict Build Preparation Markdown-brief admission for Code Generator.

Build Preparation owns two human-readable Markdown documents.  Code Generator
stores those documents verbatim in one immutable local envelope, validates the
small fenced JSON indexes, and compiles only the compatibility projections its
existing deterministic planner/build pipeline consumes.  This module never
downloads a resource and never recreates the retired ZIP-pack boundary.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, NoReturn, cast
from urllib.parse import urlsplit

BRIEF_ENVELOPE_VERSION = "code-generator-brief-envelope-v1"
# Projection schema retained for compatibility with already-admitted namespaced briefs.
BRIEF_CONTRACT_VERSION = "build-preparation-brief-v1"
BRIEF_RAW_SOURCE_VERSION = "build-preparation-brief-v1"
BRIEF_NAMESPACED_SOURCE_VERSION = "build-preparation-namespaced-brief-v1"
BRIEF_RAW_SOURCE_FORMAT: Literal["raw-producer-v1"] = "raw-producer-v1"
BRIEF_NAMESPACED_SOURCE_FORMAT: Literal["namespaced-v1"] = "namespaced-v1"
BRIEF_STRUCTURE_VERSION = "bp-structure-v1"
CONTENT_FILENAME = "content-and-narrative-brief.md"
VISUAL_FILENAME = "visual-and-build-brief.md"

_VERSION_KEYS = ("contract_version", "brief_contract_version", "schema_version")
_CONTENT_INDEX_KEYS = {
    "kind",
    "run_id",
    "content_architect_content_hash",
    "navigation_contract",
    "routes",
    *_VERSION_KEYS,
}
_VISUAL_INDEX_KEYS = {
    "kind",
    "run_id",
    "visual_input_mode",
    "target_contract",
    "recommended_dependencies",
    "routes",
    "resources",
    "components",
    *_VERSION_KEYS,
}
_ROUTE_KEYS = {"route_id", "path", "title", "sections"}
_NAVIGATION_KEYS = {"closed", "allowed_destinations"}
_RESOURCE_KEYS = {
    "need_id",
    "role_id",
    "category",
    "route_ids",
    "purpose",
    "status",
    "primary_candidate_index",
    "guidance",
    "candidates",
}
_COMPONENT_KEYS = {
    "need_id",
    "role_id",
    "route_ids",
    "purpose",
    "primary_suggestion_index",
    "guidance",
    "suggestions",
}
_RESOURCE_CANDIDATE_KEYS = {
    "provider",
    "provider_asset_id",
    "url",
    "preview_url",
    "license",
    "license_reference",
    "title",
    "width",
    "height",
    "attribution",
    "additional_urls",
}
_COMPONENT_SUGGESTION_KEYS = {
    "provider",
    "name",
    "title",
    "description",
    "item_url",
}
_CONTENT_REQUIRED_KEYS = {
    "kind",
    "run_id",
    "content_architect_content_hash",
    "navigation_contract",
    "routes",
}
_VISUAL_REQUIRED_KEYS = {
    "kind",
    "run_id",
    "visual_input_mode",
    "target_contract",
    "recommended_dependencies",
    "routes",
    "resources",
    "components",
}
_RESOURCE_REQUIRED_KEYS = {
    "role_id",
    "category",
    "route_ids",
    "purpose",
    "primary_candidate_index",
    "guidance",
    "candidates",
}
_COMPONENT_REQUIRED_KEYS = {
    "role_id",
    "route_ids",
    "purpose",
    "primary_suggestion_index",
    "guidance",
    "suggestions",
}
_DECLARED_RESOURCE_REQUIRED_KEYS = _RESOURCE_REQUIRED_KEYS | {"need_id", "status"}
_DECLARED_COMPONENT_REQUIRED_KEYS = _COMPONENT_REQUIRED_KEYS | {"need_id"}
_SAFE_BRIEF_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


@dataclass(frozen=True)
class BriefSourceFormat:
    format_id: Literal["raw-producer-v1", "namespaced-v1"]
    source_version: str
    dispatch_mode: Literal["declared", "legacy_unversioned"]
    raw_sections: bool
    structural_signature: str


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


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise BriefContractError(
                "BRIEF_JSON_DUPLICATE_KEY",
                "Brief JSON objects cannot contain duplicate keys.",
                details={"duplicate_key": key},
            )
        value[key] = item
    return value


def _strict_json_loads(value: str) -> Any:
    return json.loads(value, object_pairs_hook=_strict_json_object)


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
        payload = _strict_json_loads(data.decode("utf-8-sig"))
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

    raw_content_index = _tagged_index(content_markdown, _CONTENT_TAG)
    visual_index = _tagged_index(visual_markdown, _VISUAL_TAG)
    source_format, content_index, heading_ids = _prepare_brief_indexes(
        raw_content_index, visual_index
    )

    routes = [item for item in content_index["routes"] if isinstance(item, dict)]
    section_content = _section_content(
        content_markdown,
        routes,
        heading_ids=heading_ids,
        require_route_context=source_format.raw_sections,
    )
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
    slots, resource_needs, decisions = _resource_contracts(
        visual_index,
        routes,
        source_format=source_format,
    )
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
        "source_version": source_format.source_version,
        "source_format": source_format.format_id,
        "dispatch_mode": source_format.dispatch_mode,
        "structural_signature": source_format.structural_signature,
        "schema_version": BRIEF_ENVELOPE_VERSION,
    }
    summary = {
        "run_id": str(content_index["run_id"]),
        "source_version": source_format.source_version,
        "source_format": source_format.format_id,
        "dispatch_mode": source_format.dispatch_mode,
        "structural_signature": source_format.structural_signature,
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
        value = _strict_json_loads(matches[0].group("body"))
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
    """Compatibility validator used by focused tests and external probes."""

    _prepare_brief_indexes(content, visual)


def _prepare_brief_indexes(
    content: dict[str, Any], visual: dict[str, Any]
) -> tuple[BriefSourceFormat, dict[str, Any], dict[str, dict[str, str]]]:
    """Select exactly one source format and return a strict canonical index."""

    _validate_wire_shape(content, visual)
    declared_version = _declared_source_version(content, visual)
    section_style = _section_id_style(content)

    format_id: Literal["raw-producer-v1", "namespaced-v1"]
    source_version: str
    raw_sections: bool
    dispatch_mode: Literal["declared", "legacy_unversioned"]
    if declared_version is not None:
        dispatch_mode = "declared"
        if declared_version == BRIEF_RAW_SOURCE_VERSION:
            # Before explicit dispatch existed, this value was accepted for
            # namespaced briefs too. Preserve those immutable envelopes while
            # recording their actual source format separately.
            if section_style == "raw":
                format_id = BRIEF_RAW_SOURCE_FORMAT
                raw_sections = True
            elif section_style == "namespaced":
                format_id = BRIEF_NAMESPACED_SOURCE_FORMAT
                raw_sections = False
            else:
                raise BriefContractError(
                    "BRIEF_VERSION_STRUCTURE_MISMATCH",
                    "The legacy v1 declaration requires uniformly raw or namespaced section IDs.",
                    details={
                        "declared_version": declared_version,
                        "observed_style": section_style,
                    },
                )
        elif declared_version == BRIEF_NAMESPACED_SOURCE_VERSION:
            format_id = BRIEF_NAMESPACED_SOURCE_FORMAT
            raw_sections = False
            if section_style != "namespaced":
                raise BriefContractError(
                    "BRIEF_VERSION_STRUCTURE_MISMATCH",
                    "The namespaced source version requires route-namespaced section IDs.",
                    details={
                        "declared_version": declared_version,
                        "observed_style": section_style,
                    },
                )
        else:
            raise BriefContractError(
                "BRIEF_VERSION_UNSUPPORTED",
                f"The declared brief source version {declared_version[:80]!r} is unsupported.",
            )
        source_version = declared_version
    elif section_style == "raw":
        dispatch_mode = "legacy_unversioned"
        format_id = BRIEF_RAW_SOURCE_FORMAT
        source_version = BRIEF_RAW_SOURCE_VERSION
        raw_sections = True
    elif section_style == "namespaced":
        dispatch_mode = "legacy_unversioned"
        format_id = BRIEF_NAMESPACED_SOURCE_FORMAT
        # Preserve the historical receipt value for already-admitted
        # unversioned namespaced envelopes. source_format disambiguates it.
        source_version = BRIEF_CONTRACT_VERSION
        raw_sections = False
    elif section_style == "mixed":
        raise BriefContractError(
            "BRIEF_VERSION_AMBIGUOUS",
            "Unversioned briefs cannot mix raw and route-namespaced section IDs.",
        )
    else:
        raise BriefContractError(
            "BRIEF_STRUCTURE_UNRECOGNIZED",
            "The unversioned brief structure does not match a supported source format.",
        )

    current_declared_shape = (
        format_id == BRIEF_RAW_SOURCE_FORMAT and declared_version == BRIEF_RAW_SOURCE_VERSION
    ) or declared_version == BRIEF_NAMESPACED_SOURCE_VERSION
    if current_declared_shape:
        _validate_current_producer_fields(visual)

    if raw_sections:
        canonical_content, heading_ids = _canonicalize_raw_content_index(content)
    else:
        canonical_content = copy.deepcopy(content)
        heading_ids = _canonical_heading_ids(canonical_content)
    _validate_canonical_indexes(canonical_content, visual)
    signature = _brief_structural_signature(content, visual, format_id=format_id)
    return (
        BriefSourceFormat(
            format_id=format_id,
            source_version=source_version,
            dispatch_mode=dispatch_mode,
            raw_sections=raw_sections,
            structural_signature=signature,
        ),
        canonical_content,
        heading_ids,
    )


def _validate_wire_shape(content: dict[str, Any], visual: dict[str, Any]) -> None:
    """Validate exact, non-coercing v1 wire types before format dispatch."""

    if content.get("kind") != "content_index" or visual.get("kind") != "visual_index":
        raise BriefContractError(
            "BRIEF_INDEX_KIND_INVALID", "The two brief indexes have invalid kind discriminators."
        )
    _reject_unknown_keys(content, _CONTENT_INDEX_KEYS, "content index")
    _reject_unknown_keys(visual, _VISUAL_INDEX_KEYS, "visual index")
    _require_wire_keys(content, _CONTENT_REQUIRED_KEYS, "content index")
    _require_wire_keys(visual, _VISUAL_REQUIRED_KEYS, "visual index")
    _wire_string(content["run_id"], "content run_id")
    _wire_string(
        content["content_architect_content_hash"], "content architect hash", allow_empty=True
    )
    _wire_string(visual["run_id"], "visual run_id")
    _wire_string(visual["visual_input_mode"], "visual input mode")
    _wire_string(visual["target_contract"], "target contract")
    _wire_string_list(visual["recommended_dependencies"], "recommended dependencies")
    _wire_string_list(visual["routes"], "visual routes")

    navigation = content["navigation_contract"]
    if not isinstance(navigation, dict):
        _wire_shape_error("navigation contract must be an object")
    _reject_unknown_keys(navigation, _NAVIGATION_KEYS, "navigation contract")
    _require_wire_keys(navigation, _NAVIGATION_KEYS, "navigation contract")
    if type(navigation["closed"]) is not bool:
        _wire_shape_error("navigation closed must be a boolean")
    _wire_string_list(navigation["allowed_destinations"], "navigation destinations")

    routes = content["routes"]
    if not isinstance(routes, list) or not routes:
        _wire_shape_error("content routes must be a non-empty array")
    for route in routes:
        if not isinstance(route, dict):
            _wire_shape_error("every content route must be an object")
        _reject_unknown_keys(route, _ROUTE_KEYS, "route")
        _require_wire_keys(route, _ROUTE_KEYS, "route")
        _wire_string(route["route_id"], "route_id")
        _wire_string(route["path"], "route path")
        _wire_string(route["title"], "route title")
        sections = _wire_string_list(route["sections"], "route sections")
        if not sections:
            _wire_shape_error("route sections must be a non-empty array")

    for collection_name, allowed_keys, required_keys, candidates_key, primary_key in (
        (
            "resources",
            _RESOURCE_KEYS,
            _RESOURCE_REQUIRED_KEYS,
            "candidates",
            "primary_candidate_index",
        ),
        (
            "components",
            _COMPONENT_KEYS,
            _COMPONENT_REQUIRED_KEYS,
            "suggestions",
            "primary_suggestion_index",
        ),
    ):
        collection = visual[collection_name]
        if not isinstance(collection, list):
            _wire_shape_error(f"visual {collection_name} must be an array")
        for item in collection:
            if not isinstance(item, dict):
                _wire_shape_error(f"every {collection_name[:-1]} must be an object")
            _reject_unknown_keys(item, allowed_keys, collection_name[:-1])
            _require_wire_keys(item, required_keys, collection_name[:-1])
            _wire_string(item["role_id"], f"{collection_name[:-1]} role_id")
            _wire_string(item["purpose"], f"{collection_name[:-1]} purpose", allow_empty=True)
            _wire_string(item["guidance"], f"{collection_name[:-1]} guidance", allow_empty=True)
            route_ids = _wire_string_list(item["route_ids"], f"{collection_name[:-1]} route_ids")
            if not route_ids:
                _wire_shape_error(f"{collection_name[:-1]} route_ids cannot be empty")
            if "need_id" in item:
                _wire_string(item["need_id"], f"{collection_name[:-1]} need_id")
            if "status" in item:
                _wire_string(item["status"], "resource status")
                if item["status"] not in {"candidates_found", "no_material_found"}:
                    _wire_shape_error("resource status is not a supported v1 value")
            if "category" in item:
                _wire_string(item["category"], "resource category")
            candidates = item[candidates_key]
            if not isinstance(candidates, list):
                _wire_shape_error(f"{collection_name[:-1]} {candidates_key} must be an array")
            primary = item[primary_key]
            if primary is not None and (
                type(primary) is not int or not 0 <= primary < len(candidates)
            ):
                _wire_shape_error(f"{collection_name[:-1]} primary index is invalid")
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    _wire_shape_error(f"every {collection_name[:-1]} candidate must be an object")
                if collection_name == "resources":
                    _validate_resource_candidate_wire(candidate)
                else:
                    _validate_component_suggestion_wire(candidate)


def _validate_current_producer_fields(visual: dict[str, Any]) -> None:
    """Require fields emitted by versioned current producers, not frozen legacy shapes."""

    for item in visual["resources"]:
        _require_wire_keys(item, _DECLARED_RESOURCE_REQUIRED_KEYS, "resource")
    for item in visual["components"]:
        _require_wire_keys(item, _DECLARED_COMPONENT_REQUIRED_KEYS, "component")


def _wire_shape_error(message: str) -> NoReturn:
    raise BriefContractError("BRIEF_STRUCTURE_UNRECOGNIZED", message)


def _require_wire_keys(value: dict[str, Any], required: set[str], label: str) -> None:
    missing = sorted(required - set(value))
    if missing:
        raise BriefContractError(
            "BRIEF_STRUCTURE_UNRECOGNIZED",
            f"The {label} is missing required v1 structural fields.",
            details={"missing_fields": ",".join(missing)},
        )


def _wire_string(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        _wire_shape_error(f"{label} must be a{' non-empty' if not allow_empty else ''} string")
    return value


def _wire_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        _wire_shape_error(f"{label} must be an array of strings")
    return cast(list[str], value)


def _validate_resource_candidate_wire(candidate: dict[str, Any]) -> None:
    _reject_unknown_keys(candidate, _RESOURCE_CANDIDATE_KEYS, "resource candidate")
    _require_wire_keys(candidate, _RESOURCE_CANDIDATE_KEYS, "resource candidate")
    for key in _RESOURCE_CANDIDATE_KEYS - {"width", "height", "additional_urls"}:
        _wire_string(candidate[key], f"resource candidate {key}", allow_empty=key != "provider")
    for key in ("width", "height"):
        if type(candidate[key]) is not int or candidate[key] < 0:
            _wire_shape_error(f"resource candidate {key} must be a non-negative integer")
    additional_urls = candidate["additional_urls"]
    if not isinstance(additional_urls, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in additional_urls.items()
    ):
        _wire_shape_error("resource candidate additional_urls must map strings to strings")


def _validate_component_suggestion_wire(candidate: dict[str, Any]) -> None:
    _reject_unknown_keys(candidate, _COMPONENT_SUGGESTION_KEYS, "component suggestion")
    _require_wire_keys(candidate, _COMPONENT_SUGGESTION_KEYS, "component suggestion")
    for key in _COMPONENT_SUGGESTION_KEYS:
        _wire_string(candidate[key], f"component suggestion {key}", allow_empty=key != "provider")


def _reject_unknown_keys(value: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise BriefContractError(
            "BRIEF_STRUCTURE_UNRECOGNIZED",
            f"The {label} contains fields outside the supported structural signature.",
            details={"unknown_fields": ",".join(unknown)},
        )


def _declared_source_version(content: dict[str, Any], visual: dict[str, Any]) -> str | None:
    def declaration(index: dict[str, Any], label: str) -> str | None:
        values: list[str] = []
        for key in _VERSION_KEYS:
            if key not in index:
                continue
            raw_value = index[key]
            if not isinstance(raw_value, str) or not raw_value.strip():
                raise BriefContractError(
                    "BRIEF_VERSION_INVALID",
                    f"The {label} brief contains a blank or invalid {key} declaration.",
                )
            values.append(raw_value.strip())
        if not values:
            return None
        if len(set(values)) != 1:
            raise BriefContractError(
                "BRIEF_VERSION_AMBIGUOUS",
                f"The {label} brief contains conflicting source-version aliases.",
            )
        return values[0]

    content_version = declaration(content, "content")
    visual_version = declaration(visual, "visual")
    if (content_version is None) != (visual_version is None):
        raise BriefContractError(
            "BRIEF_VERSION_AMBIGUOUS",
            "Content and visual briefs must both declare the same source version or both omit it.",
        )
    if content_version != visual_version:
        raise BriefContractError(
            "BRIEF_VERSION_AMBIGUOUS",
            "Content and visual briefs declare different source versions.",
        )
    return content_version


def _section_id_style(content: dict[str, Any]) -> str:
    observed: set[str] = set()
    routes = content.get("routes")
    if not isinstance(routes, list):
        return "unknown"
    for route in routes:
        if not isinstance(route, dict):
            continue
        route_id = str(route.get("route_id", "")).strip()
        sections = route.get("sections")
        if not isinstance(sections, list):
            continue
        for raw_section in sections:
            if not isinstance(raw_section, str):
                return "invalid"
            section_id = raw_section.strip()
            if _SAFE_BRIEF_ID.fullmatch(section_id):
                observed.add("raw")
                continue
            prefix = f"{route_id}:"
            if (
                _SAFE_BRIEF_ID.fullmatch(route_id)
                and section_id.startswith(prefix)
                and _SAFE_BRIEF_ID.fullmatch(section_id[len(prefix) :])
            ):
                observed.add("namespaced")
                continue
            return "invalid"
    if not observed:
        return "unknown"
    return next(iter(observed)) if len(observed) == 1 else "mixed"


def _canonicalize_raw_content_index(
    content: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    canonical = copy.deepcopy(content)
    routes = canonical.get("routes")
    if not isinstance(routes, list):
        return canonical, {}
    route_ids = {
        str(route.get("route_id", "")).strip() for route in routes if isinstance(route, dict)
    }
    raw_to_canonical: dict[str, dict[str, str]] = {}
    for route in routes:
        if not isinstance(route, dict):
            continue
        route_id = str(route.get("route_id", "")).strip()
        sections = route.get("sections")
        if not isinstance(sections, list):
            continue
        canonical_sections: list[str] = []
        for raw_section in sections:
            section_id = str(raw_section).strip()
            if section_id in route_ids:
                raise BriefContractError(
                    "BRIEF_SECTION_ROUTE_COLLISION",
                    "Raw producer section IDs must be disjoint from route IDs.",
                )
            route_mappings = raw_to_canonical.setdefault(section_id, {})
            if route_id in route_mappings:
                raise BriefContractError(
                    "BRIEF_SECTION_DUPLICATE",
                    "Raw producer section IDs must be unique within each route.",
                )
            canonical_id = f"{route_id}:{section_id}"
            route_mappings[route_id] = canonical_id
            canonical_sections.append(canonical_id)
        route["sections"] = canonical_sections
    navigation = canonical.get("navigation_contract")
    if isinstance(navigation, dict) and isinstance(navigation.get("allowed_destinations"), list):
        canonical_destinations: list[str] = []
        for raw_destination in navigation["allowed_destinations"]:
            destination = str(raw_destination)
            destination_mappings = raw_to_canonical.get(destination)
            if destination_mappings is None:
                canonical_destinations.append(destination)
            else:
                canonical_destinations.extend(destination_mappings.values())
        navigation["allowed_destinations"] = canonical_destinations
    return canonical, raw_to_canonical


def _canonical_heading_ids(content: dict[str, Any]) -> dict[str, dict[str, str]]:
    routes = content.get("routes")
    if not isinstance(routes, list):
        return {}
    return {
        str(section): {str(route["route_id"]): str(section)}
        for route in routes
        if isinstance(route, dict) and isinstance(route.get("sections"), list)
        for section in route["sections"]
    }


def _brief_structural_signature(
    content: dict[str, Any],
    visual: dict[str, Any],
    *,
    format_id: str,
) -> str:
    def keys(value: Any) -> list[str]:
        return (
            sorted(key for key in value if key not in _VERSION_KEYS)
            if isinstance(value, dict)
            else []
        )

    def entry_shapes(collection: Any, candidate_key: str, primary_key: str) -> list[dict[str, Any]]:
        if not isinstance(collection, list):
            return []
        return [
            {
                "keys": keys(item),
                "role_id": str(item.get("role_id", "")),
                "route_ids": [str(value) for value in item.get("route_ids", [])]
                if isinstance(item.get("route_ids"), list)
                else [],
                "candidate_count": len(item.get(candidate_key, []))
                if isinstance(item.get(candidate_key), list)
                else -1,
                "primary_selected": isinstance(item.get(primary_key), int),
            }
            for item in collection
            if isinstance(item, dict)
        ]

    routes = content.get("routes")
    route_shapes = (
        [
            {
                "keys": keys(route),
                "route_id": str(route.get("route_id", "")),
                "path": str(route.get("path", "")),
                "sections": [str(value) for value in route.get("sections", [])]
                if isinstance(route.get("sections"), list)
                else [],
            }
            for route in routes
            if isinstance(route, dict)
        ]
        if isinstance(routes, list)
        else []
    )
    navigation = content.get("navigation_contract")
    payload = {
        "signature_version": BRIEF_STRUCTURE_VERSION,
        "source_format": format_id,
        "content_index_keys": keys(content),
        "visual_index_keys": keys(visual),
        "routes": route_shapes,
        "navigation": {
            "keys": keys(navigation),
            "closed": navigation.get("closed") if isinstance(navigation, dict) else None,
            "allowed_destinations": [
                str(value) for value in navigation.get("allowed_destinations", [])
            ]
            if isinstance(navigation, dict)
            and isinstance(navigation.get("allowed_destinations"), list)
            else [],
        },
        "visual_routes": [str(value) for value in visual.get("routes", [])]
        if isinstance(visual.get("routes"), list)
        else [],
        "target_contract": str(visual.get("target_contract", "")),
        "resources": entry_shapes(visual.get("resources"), "candidates", "primary_candidate_index"),
        "components": entry_shapes(
            visual.get("components"), "suggestions", "primary_suggestion_index"
        ),
    }
    return f"{BRIEF_STRUCTURE_VERSION}:{sha256_bytes(canonical_json(payload))}"


def _validate_canonical_indexes(content: dict[str, Any], visual: dict[str, Any]) -> None:
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
    for route_index, route in enumerate(routes):
        if not isinstance(route, dict):
            raise BriefContractError(
                "BRIEF_ROUTE_INVALID", f"Route {route_index} is not a JSON object."
            )
        route_id = str(route.get("route_id", "")).strip()
        path = str(route.get("path", "")).strip()
        title = str(route.get("title", "")).strip()
        sections = route.get("sections")
        section_values = sections if isinstance(sections, list) else []
        missing: list[str] = []
        if not _SAFE_BRIEF_ID.fullmatch(route_id):
            missing.append("route_id")
        if not title:
            missing.append("title")
        if not _safe_route_path(path):
            missing.append("safe path")
        if not section_values:
            missing.append("approved sections")
        if missing:
            route_label = route_id or f"route[{route_index}]"
            raise BriefContractError(
                "BRIEF_ROUTE_INVALID",
                f"{route_label} is missing or has invalid {', '.join(missing)}.",
            )
        route_ids.append(route_id)
        paths.append(path)
        for section in section_values:
            section_id = str(section).strip()
            prefix = f"{route_id}:"
            local_id = section_id[len(prefix) :] if section_id.startswith(prefix) else ""
            if (
                not section_id
                or not section_id.startswith(prefix)
                or not _SAFE_BRIEF_ID.fullmatch(local_id)
            ):
                raise BriefContractError(
                    "BRIEF_SECTION_SCOPE_INVALID",
                    "Every section ID must be non-empty, route-namespaced, and structurally safe.",
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


def _section_content(
    markdown: str,
    routes: list[dict[str, Any]],
    *,
    heading_ids: dict[str, dict[str, str]] | None = None,
    require_route_context: bool = False,
) -> dict[str, dict[str, Any]]:
    expected = [str(section) for route in routes for section in route["sections"]]
    source_to_canonical = heading_ids or {
        str(section): {str(route["route_id"]): str(section)}
        for route in routes
        for section in route["sections"]
    }
    matches = list(_SECTION_HEADING.finditer(markdown))
    route_matches = list(_ROUTE_HEADING.finditer(markdown))
    route_cursor = -1
    result: dict[str, dict[str, Any]] = {}
    for index, match in enumerate(matches):
        while (
            route_cursor + 1 < len(route_matches)
            and route_matches[route_cursor + 1].start() < match.start()
        ):
            route_cursor += 1
        active_route_id = (
            route_matches[route_cursor].group("route").strip() if route_cursor >= 0 else ""
        )
        source_section_id = match.group("section").strip()
        route_mappings = source_to_canonical.get(source_section_id)
        if route_mappings is None:
            continue
        if require_route_context:
            canonical_section_id = route_mappings.get(active_route_id)
            if canonical_section_id is None:
                raise BriefContractError(
                    "BRIEF_SECTION_HEADING_SCOPE_INVALID",
                    "Every raw section-content heading must appear under its indexed route.",
                    details={
                        "route_id": active_route_id,
                        "section_id": source_section_id,
                    },
                )
        elif len(route_mappings) == 1:
            canonical_section_id = next(iter(route_mappings.values()))
        else:
            raise BriefContractError(
                "BRIEF_SECTION_HEADING_SCOPE_INVALID",
                "A section-content heading is ambiguous without route context.",
                details={"section_id": source_section_id},
            )
        if canonical_section_id in result:
            raise BriefContractError(
                "BRIEF_SECTION_CONTENT_CARDINALITY",
                f"Section {source_section_id} must appear exactly once in its indexed route.",
            )
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        fragment = markdown[match.end() : end]
        blocks = [
            item for item in _TAGGED_JSON.finditer(fragment) if item.group("tag") == _SECTION_TAG
        ]
        if len(blocks) != 1:
            raise BriefContractError(
                "BRIEF_SECTION_CONTENT_CARDINALITY",
                f"Section {source_section_id} must contain exactly one section-content JSON fence.",
            )
        try:
            content = _strict_json_loads(blocks[0].group("body"))
        except json.JSONDecodeError as exc:
            raise BriefContractError(
                "BRIEF_SECTION_CONTENT_INVALID",
                f"Section {source_section_id} contains invalid JSON.",
            ) from exc
        if not isinstance(content, dict) or not content:
            raise BriefContractError(
                "BRIEF_SECTION_CONTENT_INVALID",
                f"Section {source_section_id} content must be a non-empty JSON object.",
            )
        purpose_match = re.search(r"\*([^*\r\n]+)\*", fragment[: blocks[0].start()])
        result[canonical_section_id] = {
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
    visual_index: dict[str, Any],
    routes: list[dict[str, Any]],
    *,
    source_format: BriefSourceFormat,
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
    modern_owner_projection = (
        source_format.format_id == BRIEF_RAW_SOURCE_FORMAT
        or source_format.source_version == BRIEF_NAMESPACED_SOURCE_VERSION
    )
    seen_roles: set[str] = set()
    seen_projected_slots: set[str] = set()
    seen_projected_needs: set[str] = set()
    for item, entry_kind in entries:
        base_slot_id = str(item["role_id"])
        if base_slot_id in seen_roles:
            raise BriefContractError(
                "BRIEF_RESOURCE_ROLE_DUPLICATE", "Resource and component role IDs must be unique."
            )
        seen_roles.add(base_slot_id)
        route_ids = [str(value) for value in item.get("route_ids", [])]
        if not route_ids or any(route_id not in route_sections for route_id in route_ids):
            raise BriefContractError(
                "BRIEF_RESOURCE_ROUTE_INVALID", "A resource role references an unknown route."
            )
        if len(route_ids) != len(set(route_ids)):
            raise BriefContractError(
                "BRIEF_RESOURCE_ROUTE_DUPLICATE",
                "A resource role cannot name the same route more than once.",
            )
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
        source_need_id = str(item.get("need_id", ""))
        base_need_id = source_need_id or base_slot_id
        expand_owners = modern_owner_projection and len(route_ids) > 1
        owner_route_ids = route_ids if expand_owners else route_ids[:1]
        for route_id in owner_route_ids:
            slot_id = f"{base_slot_id}@{route_id}" if expand_owners else base_slot_id
            need_id = f"{base_need_id}@{route_id}" if expand_owners else base_need_id
            if modern_owner_projection and (
                slot_id in seen_projected_slots or need_id in seen_projected_needs
            ):
                identifier_kind = (
                    "resource_slot_id" if slot_id in seen_projected_slots else "need_id"
                )
                identifier = slot_id if identifier_kind == "resource_slot_id" else need_id
                raise BriefContractError(
                    "BRIEF_RESOURCE_ID_COLLISION",
                    "Projected resource slot and need IDs must be unique after route expansion.",
                    details={"identifier_kind": identifier_kind, "identifier": identifier},
                )
            if modern_owner_projection:
                seen_projected_slots.add(slot_id)
                seen_projected_needs.add(need_id)
            section_ids = _role_sections(
                base_slot_id,
                route_id,
                route_sections[route_id],
                source_format=source_format.format_id,
            )
            slot = {
                "resource_slot_id": slot_id,
                "category": category,
                "route_id": route_id,
                "scene_ids": [],
                "section_ids": section_ids,
                "component_placement": purpose,
                # Brief resources are candidates and suggestions, never mandatory
                # evidence. A failed fetch therefore degrades honestly instead of
                # blocking a complete portfolio build.
                "required": False,
                "source_ids": [source_need_id],
                "criterion_ids": [f"criterion:{section}" for section in section_ids],
                "rationale": " ".join(value for value in (purpose, guidance) if value),
                "provenance": "build_preparation_brief",
                "resolution": resolution,
            }
            slots.append(slot)
            needs.append(
                {
                    "need_id": need_id,
                    "role_id": slot_id,
                    "category": category,
                    "purpose": purpose,
                    "guidance": guidance,
                    "route_ids": [route_id] if modern_owner_projection else route_ids,
                    "section_ids": section_ids,
                    "required": False,
                    "fallback": resolution["fallback_behavior"],
                }
            )
            decisions.append(
                {
                    "resource_slot_id": slot_id,
                    "need_id": need_id,
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
        # but the workspace needs stable intended paths before planning. The
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
        # Build Preparation candidate links do not carry dependency authority.
        # Component dependencies are derived from the pinned fetched registry
        # response at materialization time, never from uploaded brief JSON.
        "dependencies": [],
        "registry_dependencies": [],
        "expected_exports": [],
        "font_family": font_family,
        "font_weights": font_weights,
        "local_paths": local_paths,
        "fallback_behavior": fallback,
        "responsive_behavior": guidance or "Preserve meaning and hierarchy at every viewport.",
        "reduced_motion_behavior": "Remove transforms and reveal the final static state immediately.",
    }


def _role_sections(
    role_id: str,
    route_id: str,
    route_sections: list[str],
    *,
    source_format: Literal["raw-producer-v1", "namespaced-v1"],
) -> list[str]:
    matches: list[str] = []
    for section in route_sections:
        if source_format == BRIEF_RAW_SOURCE_FORMAT:
            prefix = f"{route_id}:"
            role_section = section[len(prefix) :] if section.startswith(prefix) else section
        else:
            # Preserve the original namespaced-v1 projection behavior. Older
            # immutable admissions matched the complete namespaced section ID;
            # changing that under a stable admitted identity would drift plans.
            role_section = section
        if f":{role_section}:" in f":{role_id}:":
            matches.append(section)
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
    "BRIEF_NAMESPACED_SOURCE_FORMAT",
    "BRIEF_NAMESPACED_SOURCE_VERSION",
    "BRIEF_RAW_SOURCE_FORMAT",
    "BRIEF_RAW_SOURCE_VERSION",
    "BRIEF_STRUCTURE_VERSION",
    "CONTENT_FILENAME",
    "VISUAL_FILENAME",
    "BriefContractError",
    "compile_brief_envelope",
    "compile_briefs",
    "make_brief_envelope",
    "parse_brief_envelope",
    "sha256_bytes",
]
