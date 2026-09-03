"""Contracts for the Build Preparation agent.

Build Preparation compiles the approved Content Architect + Visual Design
Director output into two Markdown briefs for Code Generator: a content brief
(assembled deterministically from Content Architect's approved copy, no model
involved) and a visual brief (one bounded model call over a deterministically
compiled scope plus real, discovery-only resource candidates). Build
Preparation never downloads or verifies resource bytes -- it finds and
suggests real candidate links; Code Generator fetches bytes at generation
time.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BuildPreparationStatus(StrEnum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    READY = "ready"
    NEEDS_ATTENTION = "needs_attention"


class StageEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    stage: str
    level: Literal["info", "warning", "error"] = "info"
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class BuildPreparationSourceRef(BaseModel):
    """The two-hash source snapshot used for stale-result detection."""

    model_config = ConfigDict(extra="forbid")

    content_architect_content_hash: str = ""
    visual_design_director_direction_hash: str = ""
    input_projection_hash: str = ""
    visual_input_mode: Literal["approved_vdd", "assumed_from_content", "merged_vdd_assumptions"] = (
        "approved_vdd"
    )
    assumption_hash: str = ""
    assumptions: list[str] = Field(default_factory=list)
    producer_provenance_hash: str = ""
    content_architect_session_revision: int = 0
    visual_design_director_session_revision: int = 0
    snapshotted_at: str = ""


class RouteScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route_id: str
    path: str = ""
    title: str = ""
    purpose: str = ""
    publication_status: str = "approved"
    section_ids: list[str] = Field(default_factory=list)
    scene_ids: list[str] = Field(default_factory=list)
    asset_ids: list[str] = Field(default_factory=list)
    resource_ids: list[str] = Field(default_factory=list)


class ComponentIntent(BaseModel):
    """Typed semantic contract for one registry-backed interaction role."""

    model_config = ConfigDict(extra="forbid")

    role_id: str
    route_id: str
    scene_id: str = ""
    section_id: str = ""
    interaction_class: str
    interaction_outcome: str
    placement: str = ""
    purpose: str = ""
    provider_terms: list[str] = Field(default_factory=list)
    negative_concepts: list[str] = Field(default_factory=list)
    required: bool = False
    fallback_type: str = "semantic_local"
    responsive_behavior: str = ""
    reduced_motion_behavior: str = ""
    expected_exports: list[str] = Field(default_factory=list)
    prohibitions: list[str] = Field(default_factory=list)


class ResourceNeed(BaseModel):
    """A deterministic need, not a fetched or selected resource."""

    model_config = ConfigDict(extra="forbid")

    need_id: str
    kind: Literal["asset", "resource"]
    source_id: str
    category: str = ""
    purpose: str = ""
    route_ids: list[str] = Field(default_factory=list)
    scene_ids: list[str] = Field(default_factory=list)
    section_ids: list[str] = Field(default_factory=list)
    source_status: str = ""
    source_policy: str = ""
    importance: str = ""
    required_for_handoff: bool = False
    query_terms: list[str] = Field(default_factory=list)
    fallback: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    component_intent: ComponentIntent | None = None


class Stage0Result(BaseModel):
    """Pure, model-free output of the deterministic scope compiler."""

    model_config = ConfigDict(extra="forbid")

    scope_hash: str
    source_ref: BuildPreparationSourceRef = Field(default_factory=BuildPreparationSourceRef)
    visual_input_mode: Literal["approved_vdd", "assumed_from_content", "merged_vdd_assumptions"] = (
        "approved_vdd"
    )
    assumption_hash: str = ""
    assumptions: list[str] = Field(default_factory=list)
    resource_targets: dict[str, int] = Field(default_factory=dict)
    routes: list[RouteScope] = Field(default_factory=list)
    resource_needs: list[ResourceNeed] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    events: list[StageEvent] = Field(default_factory=list)


class ResourceQuery(BaseModel):
    """One deterministic provider query derived from a Stage 0 resource need.

    Built by plain string templating from the need's own fields -- no model
    call. Ephemeral working data: never persisted to BuildPreparationState.
    """

    model_config = ConfigDict(extra="forbid")

    need_id: str
    kind: Literal["photo", "component", "icon", "font", "custom"]
    query: str = ""
    provider_terms: list[str] = Field(default_factory=list)
    purpose: str = ""
    subject: str = ""
    style_mood: str = ""
    theme_colors: list[str] = Field(default_factory=list)
    category: str = ""
    colors: list[str] = Field(default_factory=list)
    editors_choice: bool = False
    orientation: str = ""
    aspect_ratio: str = ""
    minimum_width: int = 0
    minimum_height: int = 0
    negative_concepts: list[str] = Field(default_factory=list)
    important: bool = False
    icon_name: str = ""
    fallback: str = ""
    required_for_handoff: bool = False
    allowed_providers: list[str] = Field(default_factory=list)
    interaction_class: str = ""
    interaction_outcome: str = ""
    placement: str = ""
    expected_exports: list[str] = Field(default_factory=list)
    responsive_behavior: str = ""
    reduced_motion_behavior: str = ""


class FetchedResource(BaseModel):
    """Provider-returned metadata only -- never resource bytes.

    Ephemeral discovery-only working data: never persisted to
    BuildPreparationState. Build Preparation reduces this to a much smaller
    ResourceCandidateLink/ComponentSuggestion before it ever reaches the
    model prompt or the final brief.
    """

    model_config = ConfigDict(extra="forbid")

    resource_id: str
    need_id: str
    kind: Literal["photo", "component", "icon", "font"]
    provider: str
    provider_asset_id: str = ""
    source_reference: str = ""
    preview_url: str = ""
    hotlink_url: str = ""
    title: str = ""
    description: str = ""
    photographer: str = ""
    photographer_url: str = ""
    attribution_url: str = ""
    width: int = 0
    height: int = 0
    orientation: str = ""
    mime_type: str = ""
    image_url: str = ""
    icon_name: str = ""
    font_family: str = ""
    font_weights: list[str] = Field(default_factory=list)
    font_urls: dict[str, str] = Field(default_factory=dict)
    retrieval_metadata: dict[str, Any] = Field(default_factory=dict)
    license: str = ""
    license_reference: str = ""
    source_version: str = ""
    fallback: str = ""
    warnings: list[str] = Field(default_factory=list)


class ResourceCandidateLink(BaseModel):
    """One real, discovery-only candidate. Never a downloaded byte."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    provider_asset_id: str = ""
    url: str = ""
    preview_url: str = ""
    license: str = ""
    license_reference: str = ""
    title: str = ""
    width: int = 0
    height: int = 0
    attribution: str = ""
    additional_urls: dict[str, str] = Field(default_factory=dict)


class ComponentSuggestion(BaseModel):
    """One real, currently-discoverable component -- a suggestion, not fetched source."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    name: str = ""
    title: str = ""
    description: str = ""
    item_url: str = ""


class ResourceBriefEntry(BaseModel):
    """One resource role as it will appear in the visual brief's resource table."""

    model_config = ConfigDict(extra="forbid")

    need_id: str
    role_id: str
    category: str
    route_ids: list[str] = Field(default_factory=list)
    purpose: str = ""
    status: Literal["candidates_found", "no_material_found"] = "no_material_found"
    candidates: list[ResourceCandidateLink] = Field(default_factory=list)
    primary_candidate_index: int | None = None
    guidance: str = ""


class ComponentBriefEntry(BaseModel):
    """One component-pattern role as it will appear in the visual brief."""

    model_config = ConfigDict(extra="forbid")

    need_id: str
    role_id: str
    route_ids: list[str] = Field(default_factory=list)
    purpose: str = ""
    suggestions: list[ComponentSuggestion] = Field(default_factory=list)
    primary_suggestion_index: int | None = None
    guidance: str = ""


class ResourceGuidance(BaseModel):
    """Model-authored pick + note for one resource role.

    The model may only pick an index into the candidate list it was actually
    given for this role -- it can never invent a URL. ``None`` means none of
    the given candidates fit; the role stays "no material found" for Code
    Generator to resolve at generation time.
    """

    model_config = ConfigDict(extra="forbid")

    need_id: str
    primary_candidate_index: int | None = None
    note: str = ""


class ComponentGuidance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    need_id: str
    primary_suggestion_index: int | None = None
    note: str = ""


class VisualBriefOutput(BaseModel):
    """The single bounded model call's structured output.

    The model never re-states approved copy, resource URLs, or route
    structure -- only prose synthesis, layout/motion guidance, and bounded
    index picks over candidates it was actually given.
    """

    model_config = ConfigDict(extra="forbid")

    stage: Literal["compose_visual_brief"] = "compose_visual_brief"
    status: Literal["ready"] = "ready"
    visual_brief_prose: str
    resource_guidance: list[ResourceGuidance] = Field(default_factory=list)
    component_guidance: list[ComponentGuidance] = Field(default_factory=list)
    seo_suggestions: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    assistant_summary: str = ""


class BuildPreparationState(BaseModel):
    """Persisted at portfolio_sessions.current_state['build_preparation']."""

    model_config = ConfigDict(extra="forbid")

    status: BuildPreparationStatus = BuildPreparationStatus.NOT_STARTED
    model_profile: str = ""
    source_ref: BuildPreparationSourceRef = Field(default_factory=BuildPreparationSourceRef)
    version: str = "build-preparation-brief-v1"
    current_stage: str = "not_started"
    run_id: str = ""
    job_id: str = ""
    scope_hash: str = ""
    routes: list[RouteScope] = Field(default_factory=list)
    resource_needs: list[ResourceNeed] = Field(default_factory=list)
    resource_index: list[ResourceBriefEntry] = Field(default_factory=list)
    component_index: list[ComponentBriefEntry] = Field(default_factory=list)
    content_brief_markdown: str = ""
    visual_brief_markdown: str = ""
    content_brief_hash: str = ""
    visual_brief_hash: str = ""
    target_contract: str = "react-vite-v1"
    recommended_dependencies: list[str] = Field(default_factory=list)
    debug_mirror_path: str = ""
    model_calls: int = 0
    provider_calls: int = 0
    warnings: list[str] = Field(default_factory=list)
    events: list[StageEvent] = Field(default_factory=list)
    latest_error: dict[str, Any] | None = None
    attempt: int = 0
    max_attempts: int = 3
    started_at: str | None = None
    completed_at: str | None = None
