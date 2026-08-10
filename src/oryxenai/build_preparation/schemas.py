"""Versioned contracts for the pre-code build package.

The schemas deliberately model site, route, section, scene, asset, and
resource separately.  They describe approved intent and verified ingredients;
they do not prescribe an implementation template.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BuildPreparationStatus(StrEnum):
    NOT_STARTED = "not_started"
    PREPARING = "preparing"
    READY = "ready"
    NEEDS_ATTENTION = "needs_attention"


class SafeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceRef(SafeModel):
    discovery_brief_hash: str = ""
    content_hash: str = ""
    visual_direction_hash: str = ""
    route_publication_hash: str = ""
    discovery_projection_hash: str = ""
    content_projection_hash: str = ""
    visual_projection_hash: str = ""
    content_session_revision: int = 0
    visual_session_revision: int = 0
    captured_at: str = ""


class ArtifactObjectRef(SafeModel):
    storage_profile: str = ""
    bucket: str = ""
    object_key: str = ""
    etag: str = ""
    sha256: str = ""
    size_bytes: int = 0
    content_type: str = "application/zip"
    created_at: str = ""
    expires_at: str = ""
    last_verified_at: str = ""


class GatedRoute(SafeModel):
    route_id: str
    publication_status: str
    path: str = ""
    reason: str = ""


class ResourceRequirement(SafeModel):
    requirement_id: str
    kind: str
    scope: str
    route_id: str = ""
    scene_id: str = ""
    intent: str = ""
    source_refs: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    fallback: str = ""


class RouteBlueprint(SafeModel):
    route_id: str
    path: str
    title: str = ""
    purpose: str = ""
    audience_takeaway: str = ""
    priority: str = ""
    content_density: str = ""
    publication_status: str = "approved"
    section_sequence: list[str] = Field(default_factory=list)
    scenes: list[str] = Field(default_factory=list)
    packet_id: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)


class ExperienceBlueprint(SafeModel):
    schema_version: str = "1"
    blueprint_id: str
    blueprint_hash: str = ""
    source_ref: SourceRef
    preparation_input_hash: str = ""
    presentation_mode: str = ""
    public_identity: dict[str, Any] = Field(default_factory=dict)
    portfolio_goal: str = ""
    audience: str = ""
    desired_visitor_action: str = ""
    narrative_thesis: str = ""
    route_map: list[RouteBlueprint] = Field(default_factory=list)
    navigation: dict[str, Any] = Field(default_factory=dict)
    link_graph: list[dict[str, Any]] = Field(default_factory=list)
    external_links: list[dict[str, Any]] = Field(default_factory=list)
    visual_language: dict[str, Any] = Field(default_factory=dict)
    shared_visual_systems: dict[str, Any] = Field(default_factory=dict)
    navigation_direction: dict[str, Any] = Field(default_factory=dict)
    motion_system: dict[str, Any] = Field(default_factory=dict)
    interaction_system: dict[str, Any] = Field(default_factory=dict)
    accessibility_and_performance: dict[str, Any] = Field(default_factory=dict)
    responsive_philosophy: dict[str, Any] = Field(default_factory=dict)
    fixed_constraints: dict[str, Any] = Field(default_factory=dict)
    must_preserve: list[str] = Field(default_factory=list)
    must_not_fabricate: list[str] = Field(default_factory=list)
    preview_scenarios: list[Any] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    routes: list[RouteBlueprint] = Field(default_factory=list)
    gated_routes: list[GatedRoute] = Field(default_factory=list)
    resource_requirements: list[ResourceRequirement] = Field(default_factory=list)
    custom_implementation_opportunities: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ResourceManifestEntry(SafeModel):
    manifest_resource_id: str
    requirement_ids: list[str] = Field(default_factory=list)
    usages: list[dict[str, Any]] = Field(default_factory=list)
    disposition: str
    provider: str = ""
    provider_asset_id: str = ""
    source_reference: str = ""
    source_version: str = ""
    content_hash: str = ""
    size_bytes: int = 0
    pack_path: str = ""
    reason: str = ""
    dependencies: list[str] = Field(default_factory=list)
    dependencies_allowed: bool = True
    editable: bool = True
    responsive_concerns: list[str] = Field(default_factory=list)
    motion_concerns: list[str] = Field(default_factory=list)
    reduced_motion_concerns: list[str] = Field(default_factory=list)
    license: str = ""
    provenance: dict[str, Any] = Field(default_factory=dict)
    attribution_required: bool = False
    fallback: str = ""
    warnings: list[str] = Field(default_factory=list)


class ResourceManifest(SafeModel):
    schema_version: str = "1"
    manifest_hash: str = ""
    policy_hash: str = ""
    catalogue_hash: str = ""
    entries: list[ResourceManifestEntry] = Field(default_factory=list)
    deduplication: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class GlobalExperienceContext(SafeModel):
    public_identity: dict[str, Any] = Field(default_factory=dict)
    portfolio_goal: str = ""
    audience: str = ""
    desired_visitor_action: str = ""
    narrative_thesis: str = ""
    presentation_mode: str = ""
    route_graph: list[dict[str, Any]] = Field(default_factory=list)
    navigation: dict[str, Any] = Field(default_factory=dict)
    visual_language: dict[str, Any] = Field(default_factory=dict)
    shared_visual_systems: dict[str, Any] = Field(default_factory=dict)
    typography: dict[str, Any] = Field(default_factory=dict)
    color_surface_system: dict[str, Any] = Field(default_factory=dict)
    grid_spacing_character: dict[str, Any] = Field(default_factory=dict)
    motion_system: dict[str, Any] = Field(default_factory=dict)
    interaction_system: dict[str, Any] = Field(default_factory=dict)
    responsive_philosophy: dict[str, Any] = Field(default_factory=dict)
    accessibility: dict[str, Any] = Field(default_factory=dict)
    reduced_motion_policy: str = ""
    performance_expectations: dict[str, Any] = Field(default_factory=dict)
    shared_resources: list[str] = Field(default_factory=list)
    fixed_dependencies: dict[str, Any] = Field(default_factory=dict)
    security_deployment_constraints: dict[str, Any] = Field(default_factory=dict)
    must_preserve: list[str] = Field(default_factory=list)
    must_not_fabricate: list[str] = Field(default_factory=list)


class PageBuildPacket(SafeModel):
    packet_id: str
    packet_hash: str = ""
    route_id: str
    path: str
    purpose: str = ""
    audience_takeaway: str = ""
    public_copy: list[dict[str, Any]] = Field(default_factory=list)
    public_entities: list[dict[str, Any]] = Field(default_factory=list)
    section_sequence: list[str] = Field(default_factory=list)
    scene_sequence: list[str] = Field(default_factory=list)
    scenes: list[dict[str, Any]] = Field(default_factory=list)
    layout_intent: dict[str, Any] = Field(default_factory=dict)
    responsive_transformations: dict[str, Any] = Field(default_factory=dict)
    mobile_simplifications: list[str] = Field(default_factory=list)
    touch_behavior: dict[str, Any] = Field(default_factory=dict)
    layer_behavior: dict[str, Any] = Field(default_factory=dict)
    selected_resources: list[str] = Field(default_factory=list)
    selected_assets: list[str] = Field(default_factory=list)
    adaptation_intent: list[str] = Field(default_factory=list)
    motion_behavior: dict[str, Any] = Field(default_factory=dict)
    reduced_motion_fallback: str = ""
    interaction_states: dict[str, Any] = Field(default_factory=dict)
    links: list[dict[str, Any]] = Field(default_factory=list)
    shared_dependencies: list[str] = Field(default_factory=list)
    custom_implementation_opportunities: list[dict[str, Any]] = Field(default_factory=list)
    failure_safe_static_states: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class PortfolioBuildContext(SafeModel):
    schema_version: str = "1"
    context_hash: str = ""
    blueprint_hash: str = ""
    manifest_hash: str = ""
    global_context: GlobalExperienceContext
    page_packets: list[dict[str, Any]] = Field(default_factory=list)
    packet_hashes: dict[str, str] = Field(default_factory=dict)


class BuildPreparationState(SafeModel):
    status: BuildPreparationStatus = BuildPreparationStatus.NOT_STARTED
    preparation_id: str = ""
    model_profile: str = ""
    run_id: str = ""
    job_id: str = ""
    attempt: int = 0
    max_attempts: int = 3
    source_ref: SourceRef = Field(default_factory=SourceRef)
    preparation_input_hash: str = ""
    policy_hash: str = ""
    target_contract_hash: str = ""
    bundle_ref: ArtifactObjectRef | None = None
    stale: bool = False
    stale_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    latest_error: dict[str, Any] | None = None
    started_at: str | None = None
    completed_at: str | None = None
