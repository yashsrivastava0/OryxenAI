"""Deterministic Markdown assembly for Build Preparation's two output briefs.

Both files together ARE the entire Build Preparation output: no ZIP, no
separate JSON pack, no object storage. Each carries exactly one
machine-readable fenced JSON block near the top -- the only structured data
either file contains -- followed by prose/tables for human and model
readability. Content Architect's approved copy is inserted here verbatim by
Python, never re-authored by a model, so the content brief is exactly as
factual as Content Architect's own approval.
"""

from __future__ import annotations

import json
from typing import Any

from oryxenai.agents.build_preparation.schemas import (
    ComponentBriefEntry,
    ResourceBriefEntry,
    RouteScope,
)

CONTENT_INDEX_TAG = "build-preparation-content-index"
VISUAL_INDEX_TAG = "build-preparation-visual-index"


def _json_block(tag: str, payload: dict[str, Any]) -> str:
    body = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
    return f"```json {tag}\n{body}\n```"


def build_content_brief(
    *,
    content_architect: dict[str, Any],
    routes: list[RouteScope],
    run_id: str,
    seo_suggestions: dict[str, str],
) -> str:
    manifest = content_architect.get("public_content_manifest")
    site_title = str(
        (manifest or {}).get("site_title", "")
        or content_architect.get("approved_brief_title", "")
        or "Portfolio"
    )
    story = content_architect.get("site_story_strategy") or {}
    allowed_destinations: list[str] = []
    for route in routes:
        if route.route_id and route.route_id not in allowed_destinations:
            allowed_destinations.append(route.route_id)
        for section_id in route.section_ids:
            if section_id and section_id not in allowed_destinations:
                allowed_destinations.append(section_id)

    index_payload = {
        "kind": "content_index",
        "run_id": run_id,
        "content_architect_content_hash": str(
            (content_architect.get("approved") or {}).get("content_hash", "")
        ),
        "navigation_contract": {
            "closed": True,
            "allowed_destinations": allowed_destinations,
        },
        "routes": [
            {
                "route_id": route.route_id,
                "path": route.path,
                "title": route.title,
                "sections": route.section_ids,
            }
            for route in routes
        ],
    }
    lines: list[str] = [f"# Content & Narrative Brief -- {site_title}", ""]
    lines.append(_json_block(CONTENT_INDEX_TAG, index_payload))
    lines.append("")
    lines.append(
        "This file is the complete, approved public content for this portfolio. "
        "Every fact below is already approved for publication -- do not add, "
        "soften, or invent anything beyond it."
    )
    lines.append("")

    if isinstance(story, dict) and story:
        lines.append("## Positioning")
        lines.append("")
        for label, key in (
            ("Positioning", "positioning"),
            ("Value proposition", "value_proposition"),
            ("Central narrative", "central_narrative_thesis"),
            ("Tone", "tone"),
            ("Primary audience", "primary_audience"),
            ("Secondary audience", "secondary_audience"),
            ("Main visitor action", "main_visitor_action"),
        ):
            value = str(story.get(key, "") or "").strip()
            if value:
                lines.append(f"- **{label}:** {value}")
        lines.append("")

    lines.append("## Navigation contract")
    lines.append("")
    lines.append(
        "The navigation_contract above is the complete, closed set of valid "
        "navigation destinations. Do not add, infer, or invent any additional "
        "page, route, or navigation item beyond it."
    )
    lines.append("")

    packs_by_route = {
        str(pack.get("route_id", "")): pack
        for pack in content_architect.get("page_content_packs", []) or []
        if isinstance(pack, dict)
    }
    for route in routes:
        lines.append(f"## Route: {route.path or '/'} ({route.route_id})")
        lines.append("")
        if route.purpose:
            lines.append(f"*Purpose: {route.purpose}*")
            lines.append("")
        pack = packs_by_route.get(route.route_id, {})
        for section in pack.get("sections", []) or []:
            if not isinstance(section, dict):
                continue
            section_id = str(section.get("section_id", ""))
            purpose = str(section.get("purpose", "") or "")
            lines.append(f"### {section_id}")
            if purpose:
                lines.append(f"*{purpose}*")
            lines.append("")
            lines.append("```json section-content")
            lines.append(
                json.dumps(
                    section.get("content", {}) or {},
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                    default=str,
                )
            )
            lines.append("```")
            lines.append("")

    claims = [
        claim
        for claim in content_architect.get("claim_grounding", []) or []
        if isinstance(claim, dict)
    ]
    if claims:
        lines.append("## Approved claims")
        lines.append("")
        for claim in claims:
            statement = str(claim.get("statement", "") or "")
            if statement:
                lines.append(f"- **{claim.get('claim_id', '')}:** {statement}")
        lines.append("")

    handoff = content_architect.get("visual_director_handoff") or {}
    never_fabricate = list(handoff.get("never_fabricate", []) or [])
    privacy = list(content_architect.get("privacy_and_confidentiality", []) or [])
    if never_fabricate or privacy:
        lines.append("## Never fabricate / privacy")
        lines.append("")
        for item in [*never_fabricate, *privacy]:
            lines.append(f"- {item}")
        lines.append("")

    if seo_suggestions:
        lines.append("## SEO (Build Preparation suggestion, not approved copy)")
        lines.append("")
        for route_id, description in seo_suggestions.items():
            lines.append(f"- **{route_id}:** {description}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_visual_brief(
    *,
    routes: list[RouteScope],
    resource_index: list[ResourceBriefEntry],
    component_index: list[ComponentBriefEntry],
    visual_brief_prose: str,
    target_contract: str,
    recommended_dependencies: list[str],
    visual_input_mode: str,
    run_id: str,
    warnings: list[str],
) -> str:
    index_payload = {
        "kind": "visual_index",
        "run_id": run_id,
        "visual_input_mode": visual_input_mode,
        "target_contract": target_contract,
        "recommended_dependencies": recommended_dependencies,
        "routes": [route.route_id for route in routes],
        "resources": [
            {
                "need_id": entry.need_id,
                "role_id": entry.role_id,
                "category": entry.category,
                "route_ids": entry.route_ids,
                "purpose": entry.purpose,
                "status": entry.status,
                "primary_candidate_index": entry.primary_candidate_index,
                "guidance": entry.guidance,
                "candidates": [candidate.model_dump(mode="json") for candidate in entry.candidates],
            }
            for entry in resource_index
        ],
        "components": [
            {
                "need_id": entry.need_id,
                "role_id": entry.role_id,
                "route_ids": entry.route_ids,
                "purpose": entry.purpose,
                "primary_suggestion_index": entry.primary_suggestion_index,
                "guidance": entry.guidance,
                "suggestions": [item.model_dump(mode="json") for item in entry.suggestions],
            }
            for entry in component_index
        ],
    }
    lines: list[str] = ["# Visual & Build Brief", ""]
    lines.append(_json_block(VISUAL_INDEX_TAG, index_payload))
    lines.append("")
    lines.append(visual_brief_prose.strip())
    lines.append("")

    if resource_index:
        lines.append("## Resource guidance (reference table)")
        lines.append("")
        lines.append("| Role | Category | Status | Primary candidate | Provider | License |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for entry in resource_index:
            primary = (
                entry.candidates[entry.primary_candidate_index]
                if entry.primary_candidate_index is not None
                and 0 <= entry.primary_candidate_index < len(entry.candidates)
                else None
            )
            lines.append(
                f"| {entry.role_id} | {entry.category} | {entry.status} | "
                f"{primary.url if primary else '(none)'} | "
                f"{primary.provider if primary else '-'} | "
                f"{primary.license if primary else '-'} |"
            )
        lines.append("")

    if component_index:
        lines.append("## Component suggestions (reference table)")
        lines.append("")
        lines.append("| Role | Primary suggestion | Provider | Reference |")
        lines.append("| --- | --- | --- | --- |")
        for component_entry in component_index:
            suggestion = (
                component_entry.suggestions[component_entry.primary_suggestion_index]
                if component_entry.primary_suggestion_index is not None
                and 0 <= component_entry.primary_suggestion_index < len(component_entry.suggestions)
                else None
            )
            lines.append(
                f"| {component_entry.role_id} | {suggestion.name if suggestion else '(none)'} | "
                f"{suggestion.provider if suggestion else '-'} | "
                f"{suggestion.item_url if suggestion else '-'} |"
            )
        lines.append("")

    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    lines.append(
        "Code Generator has final authority to adapt, replace, combine, or "
        "ignore any suggestion in this brief."
    )
    return "\n".join(lines).strip() + "\n"
