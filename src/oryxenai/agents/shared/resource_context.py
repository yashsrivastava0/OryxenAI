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

    schema_version: str = "resource-context-packet-v1"
    approved_content: dict[str, Any] = Field(default_factory=dict)
    visual_direction: dict[str, Any] = Field(default_factory=dict)
    routes: list[dict[str, Any]] = Field(default_factory=list)
    image_roles: list[dict[str, Any]] = Field(default_factory=list)
    component_roles: list[dict[str, Any]] = Field(default_factory=list)
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
    return ResourceContextPacket(
        approved_content=dict(content_architect),
        visual_direction=visual,
        routes=[
            item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item)
            for item in routes
        ],
        image_roles=image_roles,
        component_roles=component_roles,
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
    )
