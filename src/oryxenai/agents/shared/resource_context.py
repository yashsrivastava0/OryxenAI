"""One typed context packet shared by resource orchestration layers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResourceContextPacket(BaseModel):
    """Closed context passed to query, candidate, and build-context stages.

    The packet contains approved/assumed intent and provider capabilities, but
    never grants the model authority to invent a provider asset, source URL,
    source code, bytes, budget, or handoff decision.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "resource-context-packet-v2"
    approved_content: dict[str, Any] = Field(default_factory=dict)
    visual_direction: dict[str, Any] = Field(default_factory=dict)
    routes: list[dict[str, Any]] = Field(default_factory=list)
    image_roles: list[dict[str, Any]] = Field(default_factory=list)
    component_roles: list[dict[str, Any]] = Field(default_factory=list)
    component_intents: list[dict[str, Any]] = Field(default_factory=list)
    canonical_provider_terms: dict[str, list[str]] = Field(default_factory=dict)
    resource_needs: list[dict[str, Any]] = Field(default_factory=list)
    candidate_resources: list[dict[str, Any]] = Field(default_factory=list)
    selections: list[dict[str, Any]] = Field(default_factory=list)
    forbidden_concepts: list[str] = Field(default_factory=list)
    accessibility_requirements: dict[str, Any] = Field(default_factory=dict)
    provider_capabilities: dict[str, Any] = Field(default_factory=dict)
    dependency_limits: dict[str, Any] = Field(default_factory=dict)
    existing_resources: list[dict[str, Any]] = Field(default_factory=list)
    output_fields: list[str] = Field(default_factory=list)
    authority: dict[str, Any] = Field(default_factory=dict)
    query_history: list[dict[str, Any]] = Field(default_factory=list)
    provider_attempts: list[dict[str, Any]] = Field(default_factory=list)
    materialization_constraints: dict[str, Any] = Field(default_factory=dict)
    previous_attempt_analysis: dict[str, Any] = Field(default_factory=dict)
    quality_boundary: dict[str, Any] = Field(default_factory=dict)
    approved_route_context: list[dict[str, Any]] = Field(default_factory=list)
    approved_section_context: list[dict[str, Any]] = Field(default_factory=list)
    approved_scene_context: list[dict[str, Any]] = Field(default_factory=list)
    public_content_context: list[dict[str, Any]] = Field(default_factory=list)
    interaction_context: list[dict[str, Any]] = Field(default_factory=list)
    responsive_context: dict[str, Any] = Field(default_factory=dict)
    reduced_motion_context: dict[str, Any] = Field(default_factory=dict)
    semantic_subject_terms: list[str] = Field(default_factory=list)


def build_resource_context_packet(
    *,
    content_architect: dict[str, Any],
    visual_design_director: dict[str, Any],
    routes: list[Any],
    resource_needs: list[Any],
    candidate_resources: list[dict[str, Any]] | None = None,
    selections: list[dict[str, Any]] | None = None,
    provider_capabilities: dict[str, Any] | None = None,
    dependency_limits: dict[str, Any] | None = None,
    query_history: list[dict[str, Any]] | None = None,
    provider_attempts: list[dict[str, Any]] | None = None,
    materialization_constraints: dict[str, Any] | None = None,
    previous_attempt_analysis: dict[str, Any] | None = None,
    quality_boundary: dict[str, Any] | None = None,
) -> ResourceContextPacket:
    needs = [
        item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item)
        for item in resource_needs
    ]
    image_roles = [
        item
        for item in needs
        if str(item.get("category", "") or "").casefold()
        in {"image", "photo", "editorial_photo", "portrait"}
    ]
    component_roles = [
        item
        for item in needs
        if str(item.get("category", "") or "").casefold()
        in {"component", "visual_component", "registry_component"}
    ]
    component_intents = [
        item.get("component_intent")
        for item in component_roles
        if isinstance(item.get("component_intent"), dict)
    ]
    canonical_provider_terms = {
        str(item.get("role_id", "")): [
            str(term) for term in item.get("provider_terms", []) if str(term).strip()
        ]
        for item in component_intents
        if str(item.get("role_id", ""))
    }
    visual = dict(visual_design_director)
    forbidden = list(visual.get("must_not_fabricate", []) or [])
    for need in needs:
        details = need.get("details")
        if not isinstance(details, dict):
            continue
        negative_concepts = details.get("negative_concepts", [])
        if isinstance(negative_concepts, list):
            forbidden.extend(negative_concepts)
    forbidden_concepts = list(
        dict.fromkeys(str(item).strip() for item in forbidden if str(item).strip())
    )
    approved_route_context = [
        {
            "route_id": item.get("route_id", ""),
            "title": item.get("title", ""),
            "purpose": item.get("purpose", ""),
            "section_ids": item.get("section_ids", []),
            "scene_ids": item.get("scene_ids", []),
        }
        for item in [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item)
            for item in routes
        ]
    ]
    public_content_context = [
        item
        for item in (content_architect.get("page_content_packs", []) or [])
        if isinstance(item, dict)
    ]
    approved_section_context = [
        {"route_id": item.get("route_id", ""), "section": section}
        for item in public_content_context
        for section in item.get("sections", []) or []
        if isinstance(section, dict)
    ]
    approved_scene_context = [
        {"route_id": page.get("route_id", ""), "scene": scene}
        for page in visual.get("pages", []) or []
        if isinstance(page, dict)
        for scene in page.get("scenes", []) or []
        if isinstance(scene, dict)
    ]
    interaction_context = [
        {
            "role_id": item.get("role_id", ""),
            "interaction_class": item.get("interaction_class", ""),
            "interaction_outcome": item.get("interaction_outcome", ""),
            "placement": item.get("placement", ""),
        }
        for item in component_intents
        if isinstance(item, dict)
    ]
    accessibility = dict(visual.get("accessibility_and_performance") or {})
    semantic_subject_terms = list(
        dict.fromkeys(
            str(value).strip()
            for value in [
                visual.get("visual_language", {}).get("style", "")
                if isinstance(visual.get("visual_language"), dict)
                else "",
                visual.get("visual_language", {}).get("palette", [])
                if isinstance(visual.get("visual_language"), dict)
                else [],
                visual.get("global_visual_language", ""),
            ]
            for value in (value if isinstance(value, list) else [value])
            if str(value).strip()
        )
    )
    return ResourceContextPacket(
        approved_content=dict(content_architect),
        visual_direction=visual,
        routes=[
            item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item)
            for item in routes
        ],
        image_roles=image_roles,
        component_roles=component_roles,
        component_intents=component_intents,
        canonical_provider_terms=canonical_provider_terms,
        resource_needs=needs,
        candidate_resources=list(candidate_resources or []),
        selections=list(selections or []),
        forbidden_concepts=forbidden_concepts,
        accessibility_requirements=dict(visual.get("accessibility_and_performance") or {}),
        provider_capabilities=dict(provider_capabilities or {}),
        dependency_limits=dict(dependency_limits or {}),
        existing_resources=list(candidate_resources or []),
        output_fields=[
            "need_id",
            "kind",
            "query",
            "provider_terms",
            "selected_resource_id",
            "why_selected",
            "fallback",
        ],
        authority={
            "approved_route_ids": [str(item.route_id) for item in routes],
            "model_may_not_invent_provider_ids_urls_source_or_bytes": True,
            "model_may_not_grant_handoff": True,
        },
        query_history=list(query_history or []),
        provider_attempts=list(provider_attempts or []),
        materialization_constraints=dict(
            materialization_constraints
            or {
                "runtime_network_assets": False,
                "source_fetched_only_after_selection": True,
                "component_source_attempt_maximum": 3,
            }
        ),
        previous_attempt_analysis=dict(previous_attempt_analysis or {}),
        quality_boundary=dict(
            quality_boundary
            or {
                "hard_failures": [
                    "unsafe_source",
                    "missing_local_path",
                    "missing_hash",
                    "missing_provenance",
                    "invalid_dependency",
                    "invalid_license",
                ],
                "warnings_only": ["subjective_visual_quality", "candidate_style_preference"],
            }
        ),
        approved_route_context=approved_route_context,
        approved_section_context=approved_section_context,
        approved_scene_context=approved_scene_context,
        public_content_context=public_content_context,
        interaction_context=interaction_context,
        responsive_context={
            key: accessibility.get(key, "")
            for key in ("responsive", "touch", "responsive_accessibility")
            if accessibility.get(key)
        },
        reduced_motion_context={
            key: accessibility.get(key, "")
            for key in ("reduced_motion", "motion", "performance_choices")
            if accessibility.get(key)
        },
        semantic_subject_terms=semantic_subject_terms,
    )
