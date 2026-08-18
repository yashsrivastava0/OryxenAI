"""Strict contracts for Build Preparation Phase 1."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from oryxenai.storage.artifacts import ArtifactReference


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
    scene_ids: list[str] = Field(default_factory=list)
    asset_ids: list[str] = Field(default_factory=list)
    resource_ids: list[str] = Field(default_factory=list)


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
    source_status: str = ""
    source_policy: str = ""
    importance: str = ""
    required_for_handoff: bool = False
    query_terms: list[str] = Field(default_factory=list)
    fallback: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class Stage0Result(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: Literal["stage_0"] = "stage_0"
    status: Literal["ready"] = "ready"
    scope_hash: str
    source_ref: BuildPreparationSourceRef = Field(default_factory=BuildPreparationSourceRef)
    routes: list[RouteScope] = Field(default_factory=list)
    resource_needs: list[ResourceNeed] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    events: list[StageEvent] = Field(default_factory=list)
    model_calls: int = 0


class ResourceQuery(BaseModel):
    """One bounded provider query derived from a deterministic resource need."""

    model_config = ConfigDict(extra="forbid")

    need_id: str
    kind: Literal["photo", "component", "icon", "font", "custom"]
    query: str = ""
    provider_terms: list[str] = Field(default_factory=list)
    orientation: str = ""
    icon_name: str = ""
    fallback: str = ""
    required_for_handoff: bool = False
    allowed_providers: list[str] = Field(default_factory=list)


class Stage1QueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: Literal["stage_1"] = "stage_1"
    status: Literal["ready"] = "ready"
    queries: list[ResourceQuery] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class FetchedResource(BaseModel):
    """Provider-returned metadata and safe registry source text.

    Image bytes are deliberately not represented here. Pexels bytes are
    downloaded only after selection; Unsplash bytes are never downloaded.
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
    download_tracking_url: str = ""
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
    source_files: dict[str, str] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    registry_dependencies: list[str] = Field(default_factory=list)
    retrieval_metadata: dict[str, Any] = Field(default_factory=dict)
    license: str = ""
    license_reference: str = ""
    source_version: str = ""
    fallback: str = ""
    warnings: list[str] = Field(default_factory=list)


class ResourceSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    need_id: str
    selected_resource_id: str | None = None
    why_selected: str = ""
    fallback: str = ""
    adaptation_notes: str = ""


class Stage2SelectionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: Literal["stage_2"] = "stage_2"
    status: Literal["ready"] = "ready"
    selections: list[ResourceSelection] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CandidateQualification(BaseModel):
    """Deterministic admission decision for one provider candidate."""

    model_config = ConfigDict(extra="forbid")

    resource_id: str
    need_id: str
    eligible: bool
    relevance_score: int = 0
    quality_score: int = 0
    policy_status: str = "not_checked"
    technical_status: str = "not_checked"
    reasons: list[str] = Field(default_factory=list)
    issue_codes: list[str] = Field(default_factory=list)


class HandoffIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    need_id: str = ""
    next_action: str = ""


class LocalRecipe(BaseModel):
    """Declarative local implementation guidance for one execution slot.

    A recipe is intentionally not model-authored source code.  It limits a
    downstream builder to a truthful, static implementation that is already
    allowed by the approved visual direction.
    """

    model_config = ConfigDict(extra="forbid")

    recipe_id: str
    slot_id: str
    category: Literal[
        "typography_system",
        "typographic_composition",
        "css_surface_pattern",
        "representative_svg_diagram",
        "ornament_omission",
    ]
    description: str
    allowed_labels: list[str] = Field(default_factory=list)
    forbidden_concepts: list[str] = Field(default_factory=list)
    reduced_motion_state: str = "static"
    local_path: str = ""


class ResolvedResource(BaseModel):
    """Exactly one concrete resolution for an execution slot."""

    model_config = ConfigDict(extra="forbid")

    resolution_type: Literal[
        "local_materialized",
        "target_package_binding",
        "local_recipe",
        "execution_gap",
    ]
    resource_id: str = ""
    local_paths: list[str] = Field(default_factory=list)
    package_name: str = ""
    expected_exports: list[str] = Field(default_factory=list)
    font_family: str = ""
    font_weights: list[str] = Field(default_factory=list)
    recipe_id: str = ""
    fallback_disposition: str = ""
    accessibility_treatment: str = ""
    source_expectations: list[str] = Field(default_factory=list)


class ExecutionSlot(BaseModel):
    """A fixed, route-scoped resource decision consumed by Code Generator."""

    model_config = ConfigDict(extra="forbid")

    resource_slot_id: str
    category: str
    route_id: str = ""
    scene_ids: list[str] = Field(default_factory=list)
    section_ids: list[str] = Field(default_factory=list)
    component_placement: str = ""
    required: bool = False
    source_ids: list[str] = Field(default_factory=list)
    criterion_ids: list[str] = Field(default_factory=list)
    rationale: str = ""
    provenance: Literal["vdd_explicit", "build_preparation_derived"]
    resolution: ResolvedResource


class ExecutionGap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot_id: str
    route_id: str = ""
    scene_ids: list[str] = Field(default_factory=list)
    code: Literal["VDD_EXECUTION_GAP"] = "VDD_EXECUTION_GAP"
    message: str
    next_action: str


class HandoffQualityReport(BaseModel):
    """The Code Generator admission record for a packaged build context."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "build-preparation-handoff-v3"
    pack_version: str = "build-preparation-pack-v3"
    projection_hashes: dict[str, str] = Field(default_factory=dict)
    readiness: dict[str, int] = Field(default_factory=dict)
    execution_gaps: list[ExecutionGap] = Field(default_factory=list)
    handoff_eligible: bool = False
    upstream_approval_verified: bool = False
    status: Literal["ready_for_handoff", "needs_attention"] = "needs_attention"
    summary: str = ""
    required_need_ids: list[str] = Field(default_factory=list)
    selected_resource_ids: list[str] = Field(default_factory=list)
    materialized_resource_ids: list[str] = Field(default_factory=list)
    qualifications: list[CandidateQualification] = Field(default_factory=list)
    issues: list[HandoffIssue] = Field(default_factory=list)
    model_review: dict[str, Any] = Field(default_factory=dict)


class RouteBuildContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route_id: str
    path: str = ""
    brief_markdown: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    resource_ids: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    free_to_change: list[str] = Field(default_factory=list)


class BuildContextDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overview_markdown: str = ""
    routes: list[RouteBuildContext] = Field(default_factory=list)
    runtime_requirements: dict[str, Any] = Field(default_factory=dict)
    fixed_facts: list[str] = Field(default_factory=list)
    freedoms: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Stage3BuildContextResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: Literal["stage_3"] = "stage_3"
    status: Literal["ready"] = "ready"
    context: BuildContextDraft


class Stage4IntegratedContextResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: Literal["stage_4"] = "stage_4"
    status: Literal["ready"] = "ready"
    context: BuildContextDraft


class Stage5HandoffReview(BaseModel):
    """Structured model review that supplements deterministic admission checks."""

    model_config = ConfigDict(extra="forbid")

    stage: Literal["stage_5"] = "stage_5"
    status: Literal["ready"] = "ready"
    summary: str = ""
    warnings: list[str] = Field(default_factory=list)


class MaterializedFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative_path: str
    kind: Literal["text", "image", "font", "metadata"]
    size_bytes: int = 0
    sha256: str = ""


class MaterializationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root_path: str
    relative_root: str
    files: list[MaterializedFile] = Field(default_factory=list)
    resource_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    licenses: list[dict[str, Any]] = Field(default_factory=list)
    manifest_path: str = ""
    resource_plan_path: str = ""
    # Same per-resource entries written to resources/manifest.json (id,
    # provider, inspection_level, local_path/hotlink_url, warnings), exposed
    # here so a caller can see exactly what was fetched without unzipping.
    resources: list[dict[str, Any]] = Field(default_factory=list)
    handoff_report_path: str = ""
    pack_version: str = "build-preparation-pack-v3"
    projection_hashes: dict[str, str] = Field(default_factory=dict)
    execution_slots: list[ExecutionSlot] = Field(default_factory=list)
    local_recipes: list[LocalRecipe] = Field(default_factory=list)
    execution_gaps: list[ExecutionGap] = Field(default_factory=list)
    execution_contract_path: str = ""
    resource_ledger_path: str = ""


class PackageResult(BaseModel):
    """The verified Phase 3 archive and its local development mirror."""

    model_config = ConfigDict(extra="forbid")

    pack_version: str = "build-preparation-pack-v3"
    archive_sha256: str
    archive_size_bytes: int
    file_count: int
    manifest_path: str = "manifest.json"
    expires_at: str
    artifact: ArtifactReference | None = None
    mirror_root: str = ""
    mirror_relative_root: str = ""
    local_archive_path: str = ""
    local_archive_relative_path: str = ""


class BuildPreparationState(BaseModel):
    """Persisted at portfolio_sessions.current_state['build_preparation']."""

    model_config = ConfigDict(extra="forbid")

    status: BuildPreparationStatus = BuildPreparationStatus.NOT_STARTED
    model_profile: str = ""
    source_ref: BuildPreparationSourceRef = Field(default_factory=BuildPreparationSourceRef)
    version: str = "build-preparation-pack-v3"
    current_stage: str = "not_started"
    run_id: str = ""
    job_id: str = ""
    scope_hash: str = ""
    routes: list[RouteScope] = Field(default_factory=list)
    resource_needs: list[ResourceNeed] = Field(default_factory=list)
    query_plan: Stage1QueryPlan | None = None
    fetched_candidates: list[FetchedResource] = Field(default_factory=list)
    selection_plan: Stage2SelectionPlan | None = None
    build_context: BuildContextDraft | None = None
    materialization: MaterializationResult | None = None
    package: PackageResult | None = None
    handoff_report: HandoffQualityReport | None = None
    model_calls: int = 0
    provider_calls: int = 0
    warnings: list[str] = Field(default_factory=list)
    events: list[StageEvent] = Field(default_factory=list)
    latest_error: dict[str, Any] | None = None
    attempt: int = 0
    max_attempts: int = 3
    started_at: str | None = None
    completed_at: str | None = None
    manifest_path: str = ""
