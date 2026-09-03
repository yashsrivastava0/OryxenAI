"""Deterministic resource research: query construction + candidate reduction.

No model call, no byte downloads. Turns Stage 0's ResourceNeed list into real,
provider-discovered candidates (via providers.py's discovery-only functions),
then reduces each candidate to the small, hallucination-proof shape
(ResourceCandidateLink / ComponentSuggestion) the model is later allowed to
pick from only by index -- it can never invent a URL that reaches this list.

A need whose category is a pure layout/diagram pattern (hero_pattern,
background_system, diagram_primitive -- Visual Design Director's own local
catalogue suggestions) is not a fetchable resource at all; it is skipped here
and instead surfaces as prose guidance directly from Stage 0's need data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from oryxenai.agents.build_preparation.providers import ProviderLookup
from oryxenai.agents.build_preparation.schemas import (
    ComponentBriefEntry,
    ComponentSuggestion,
    FetchedResource,
    ResourceBriefEntry,
    ResourceCandidateLink,
    ResourceNeed,
    ResourceQuery,
)

_LAYOUT_PATTERN_CATEGORIES = frozenset(
    {"hero_pattern", "background_system", "diagram_primitive", "timeline_pattern"}
)
_COMPONENT_CATEGORIES = frozenset({"visual_component", "component", "registry_component"})
_IMAGE_CATEGORIES = frozenset({"image", "photo", "editorial_photo", "portrait"})
_FONT_CATEGORIES = frozenset({"font", "typography", "type_system"})


def classify_need(need: ResourceNeed) -> str:
    """Return the provider-query kind, or "custom" for a non-fetchable need."""
    category = (need.category or "").casefold()
    if category in _FONT_CATEGORIES:
        return "font"
    if category in _COMPONENT_CATEGORIES:
        return "component"
    if category in _LAYOUT_PATTERN_CATEGORIES:
        return "custom"
    if "icon" in category:
        return "icon"
    if need.kind == "asset" or category in _IMAGE_CATEGORIES:
        return "photo"
    return "custom"


def build_query(need: ResourceNeed) -> ResourceQuery:
    """Deterministically template a provider query from a Stage 0 need."""
    kind = classify_need(need)
    details = need.details or {}
    query_text = " ".join(need.query_terms) or need.purpose or need.category
    return ResourceQuery(
        need_id=need.need_id,
        kind=kind,  # type: ignore[arg-type]
        query=query_text,
        provider_terms=need.query_terms[:5],
        purpose=need.purpose,
        subject=str(details.get("style_mood", "") or "") or query_text,
        style_mood=str(details.get("style_mood", "") or ""),
        theme_colors=[str(item) for item in details.get("theme_colors", []) or [] if str(item)],
        category=need.category,
        orientation=str(details.get("orientation", "") or ""),
        minimum_width=int(details.get("minimum_width", 0) or 0),
        minimum_height=int(details.get("minimum_height", 0) or 0),
        negative_concepts=[
            str(item) for item in details.get("negative_concepts", []) or [] if str(item)
        ],
        important=bool(need.required_for_handoff),
        icon_name=(need.query_terms[0] if kind == "icon" and need.query_terms else ""),
        fallback=need.fallback or "Use an explicit custom implementation.",
        required_for_handoff=bool(need.required_for_handoff),
        allowed_providers=["fontsource"] if kind == "font" else [],
        interaction_class=str(details.get("interaction_class", "") or ""),
        interaction_outcome=str(details.get("interaction_outcome", "") or ""),
        placement=str(details.get("placement", "") or ""),
        expected_exports=[str(item) for item in details.get("expected_exports", []) or []],
        responsive_behavior=str(details.get("responsive_behavior", "") or ""),
        reduced_motion_behavior=str(details.get("reduced_motion_behavior", "") or ""),
    )


def _candidate_link(item: FetchedResource) -> ResourceCandidateLink:
    additional: dict[str, str] = {}
    if item.kind == "font" and item.font_urls:
        primary_key = "400-normal" if "400-normal" in item.font_urls else next(iter(item.font_urls))
        url = item.font_urls[primary_key]
        additional = {key: value for key, value in item.font_urls.items() if key != primary_key}
    else:
        url = item.image_url or item.hotlink_url or item.preview_url or item.source_reference
    return ResourceCandidateLink(
        provider=item.provider,
        provider_asset_id=item.provider_asset_id,
        url=url,
        preview_url=item.preview_url,
        license=item.license,
        license_reference=item.license_reference,
        title=item.title or item.font_family,
        width=item.width,
        height=item.height,
        attribution=item.photographer or item.attribution_url,
        additional_urls=additional,
    )


def _component_suggestion(item: FetchedResource) -> ComponentSuggestion:
    return ComponentSuggestion(
        provider=item.provider,
        name=item.provider_asset_id,
        title=item.title,
        description=item.description,
        item_url=item.source_reference,
    )


@dataclass
class DiscoveryResult:
    resource_index: list[ResourceBriefEntry] = field(default_factory=list)
    component_index: list[ComponentBriefEntry] = field(default_factory=list)
    provider_calls: int = 0
    provider_receipts: list[dict[str, Any]] = field(default_factory=list)
    candidates_by_need: dict[str, list[FetchedResource]] = field(default_factory=dict)


async def discover_resources(
    needs: list[ResourceNeed],
    settings: Any,
    *,
    live_providers: bool,
    max_candidates_per_role: int = 3,
) -> DiscoveryResult:
    lookup = ProviderLookup(settings=settings, live=live_providers)
    resource_index: list[ResourceBriefEntry] = []
    component_index: list[ComponentBriefEntry] = []
    candidates_by_need: dict[str, list[FetchedResource]] = {}
    for need in needs:
        query = build_query(need)
        if query.kind == "custom":
            continue
        found = (await lookup.lookup([query]))[:max_candidates_per_role]
        candidates_by_need[need.need_id] = found
        if query.kind == "component":
            component_index.append(
                ComponentBriefEntry(
                    need_id=need.need_id,
                    role_id=need.source_id,
                    route_ids=need.route_ids,
                    purpose=need.purpose,
                    suggestions=[_component_suggestion(item) for item in found],
                )
            )
        else:
            resource_index.append(
                ResourceBriefEntry(
                    need_id=need.need_id,
                    role_id=need.source_id,
                    category=need.category or query.kind,
                    route_ids=need.route_ids,
                    purpose=need.purpose,
                    status="candidates_found" if found else "no_material_found",
                    candidates=[_candidate_link(item) for item in found],
                )
            )
    return DiscoveryResult(
        resource_index=resource_index,
        component_index=component_index,
        provider_calls=lookup.calls_made,
        provider_receipts=lookup.provider_receipts,
        candidates_by_need=candidates_by_need,
    )
