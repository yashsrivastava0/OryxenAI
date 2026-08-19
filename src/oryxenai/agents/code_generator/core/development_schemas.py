"""Strict contracts for the standalone Code Generator development workflow."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DevelopmentRunStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    ADMITTING = "admitting"
    PLANNING = "planning"
    PLANNED = "planned"
    ACQUIRING = "acquiring"
    ACQUIRED = "acquired"
    GENERATING_FOUNDATION = "generating_foundation"
    GENERATING_ROUTES = "generating_routes"
    INTEGRATING = "integrating"
    SOURCE_READY = "source_ready"
    BUILDING = "building"
    SMOKE_TESTING = "smoke_testing"
    REPAIRING = "repairing"
    READY = "ready"
    NEEDS_ATTENTION = "needs_attention"


class SafeIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    next_action: str = ""
    details: dict[str, str | int | float | bool] = Field(default_factory=dict)


class AdmittedInputReference(BaseModel):
    """Safe pointer to a workspace-owned immutable input copy."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal[
        "fixture",
        "upload",
        "build_preparation_mirror",
        "build_preparation_artifact",
    ]
    source_id: str
    original_filename: str
    mime_type: str = "application/zip"
    source_sha256: str
    stored_relative_path: str
    size_bytes: int


class InputReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: str
    admitted_identity: str
    pack_sha256: str
    manifest_hash: str
    projection_hashes: dict[str, str]
    route_ids: list[str]
    target_id: str
    pack_version: str
    schema_version: str


class ContextReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: str
    context_hash: str
    stored_relative_path: str
    route_ids: list[str]
    section_count: int
    resource_slot_count: int


class PlannerCallReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: str
    context_hash: str
    plan_hash: str
    profile: str
    response_id: str = ""
    model: str = ""
    usage: dict[str, int] = Field(default_factory=dict)
    finish_reason: str = ""
    prompt_receipt: dict[str, Any] = Field(default_factory=dict)


class RequestBasis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_receipt_hash: str
    site_plan_hash: str
    checkpoint_hash: str = ""


class RequestOrigin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: Literal["initial_gap", "generation", "repair"] = "initial_gap"
    work_unit_id: str
    role: Literal[
        "resource_scout",
        "foundation_builder",
        "route_builder",
        "integrator",
        "repairer",
    ] = "resource_scout"
    origin_kind: Literal["initial_gap", "emergent_generation", "diagnostic_repair"] = "initial_gap"


class ResourcePlacement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route_id: str = ""
    section_id: str = ""
    scene_id: str = ""
    component_id: str = ""
    purpose: str


class ResourceQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    positive_terms: list[str] = Field(default_factory=list)
    negative_terms: list[str] = Field(default_factory=list)
    forbidden_subjects: list[str] = Field(default_factory=list)
    style_mood: str = ""
    theme_colors: list[str] = Field(default_factory=list)
    orientation: str = ""
    aspect_ratio: str = ""
    category: str = ""
    colors: list[str] = Field(default_factory=list)
    editors_choice: bool = False


class ResourceTechnicalConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_types: list[str] = Field(default_factory=list)
    minimum_dimensions: str = ""
    aspect_ratio: str = ""
    max_bytes: int = 0
    font_weights: list[str] = Field(default_factory=list)
    required_exports: list[str] = Field(default_factory=list)


class ResourceSourceConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed_source_kinds: list[str] = Field(default_factory=list)
    upstream_source_policy: str = ""
    attribution_allowed: bool = True
    vendoring_required: bool = True


class ResourceFallback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[
        "system_font_stack",
        "lucide_default",
        "generated_local",
        "simple_dom",
        "discard_ornament",
        "none",
    ]
    implementation: str


class ResourceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["acquire-resource-request-v1"] = "acquire-resource-request-v1"
    request_id: str
    based_on: RequestBasis
    origin: RequestOrigin
    category: Literal[
        "image",
        "texture",
        "font",
        "icon",
        "illustration",
        "component_source",
        "style_primitive",
    ]
    placement: ResourcePlacement
    why_existing_is_insufficient: str
    query: ResourceQuery
    technical_constraints: ResourceTechnicalConstraints
    source_constraints: ResourceSourceConstraints
    requiredness: Literal["required", "preferred"]
    fallback: ResourceFallback
    affected_work_unit_ids: list[str] = Field(default_factory=list)
    request_hash: str = ""

    @model_validator(mode="after")
    def stamp_request_hash(self) -> ResourceRequest:
        payload = self.model_dump(mode="json", exclude={"request_hash", "request_id"})
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.request_hash and self.request_hash != digest:
            raise ValueError("request_hash does not match the canonical request")
        self.request_hash = digest
        return self


class ResourceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    provider_key: str
    provider_resource_id: str
    category: str
    title: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    technical_metadata: dict[str, Any] = Field(default_factory=dict)
    canonical_source: str
    licence: str
    attribution: str = ""
    vendoring_policy: str = ""
    dependency_metadata: dict[str, list[str]] = Field(default_factory=dict)


class LocalMaterialFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_path: str
    media_type: str
    size: int
    sha256: str
    inspection: dict[str, str | int | float | bool] = Field(default_factory=dict)


class ResourceReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["acquire-resource-receipt-v1"] = "acquire-resource-receipt-v1"
    request_hash: str
    disposition: Literal["admitted", "fallback", "rejected"]
    selected_candidate_id: str = ""
    provider_key: str = ""
    canonical_source: str = ""
    licence: str = ""
    attribution: str = ""
    original_hash: str = ""
    materialized_files: list[LocalMaterialFile] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    satisfied_placements: list[str] = Field(default_factory=list)
    fallback: dict[str, str] = Field(default_factory=dict)
    policy_version: str = "code-generator-acquisition-v1"
    acquired_at: str = ""


class ResourceBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    binding_id: str
    request_id_or_pack_need_id: str
    local_paths: list[str] = Field(default_factory=list)
    placement_ids: list[str] = Field(default_factory=list)
    disposition: Literal["admitted", "fallback", "rejected"]


class PlanDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["plan-delta-v1"] = "plan-delta-v1"
    delta_id: str
    based_on_plan_hash: str
    binding_changes: list[ResourceBinding] = Field(default_factory=list)
    placement_detail_changes: dict[str, str] = Field(default_factory=dict)
    added_vendor_paths: list[str] = Field(default_factory=list)
    delta_hash: str = ""

    @model_validator(mode="after")
    def stamp_delta_hash(self) -> PlanDelta:
        payload = self.model_dump(mode="json", exclude={"delta_hash"})
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.delta_hash and self.delta_hash != digest:
            raise ValueError("delta_hash does not match the canonical delta")
        self.delta_hash = digest
        return self


class ResourceLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["acquire-resource-ledger-v1"] = "acquire-resource-ledger-v1"
    based_on_input_and_plan: dict[str, str]
    requests: list[ResourceRequest] = Field(default_factory=list)
    receipts: list[ResourceReceipt] = Field(default_factory=list)
    active_bindings: list[ResourceBinding] = Field(default_factory=list)
    plan_deltas: list[PlanDelta] = Field(default_factory=list)
    ledger_hash: str = ""

    @model_validator(mode="after")
    def stamp_ledger_hash(self) -> ResourceLedger:
        payload = self.model_dump(mode="json", exclude={"ledger_hash"})
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.ledger_hash and self.ledger_hash != digest:
            raise ValueError("ledger_hash does not match the canonical ledger")
        self.ledger_hash = digest
        return self


class DependencyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["acquire-dependency-request-v1"] = "acquire-dependency-request-v1"
    request_id: str
    requesting_resource_receipt_hash: str
    package_name: str
    required_api_or_exports: list[str] = Field(default_factory=list)
    compatibility_constraints: str = ""
    reason_existing_stack_is_insufficient: str
    fallback_component_strategy: str
    request_hash: str = ""

    @model_validator(mode="after")
    def stamp_request_hash(self) -> DependencyRequest:
        payload = self.model_dump(mode="json", exclude={"request_hash", "request_id"})
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.request_hash and self.request_hash != digest:
            raise ValueError("request_hash does not match the canonical dependency request")
        self.request_hash = digest
        return self


class DependencyReceiptBasis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    toolchain_profile: str
    scaffold_manifest_hash: str = ""
    prior_manifest_hash: str
    prior_lock_hash: str
    resource_receipt_hash: str


class DependencyReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["acquire-dependency-receipt-v1"] = "acquire-dependency-receipt-v1"
    based_on: DependencyReceiptBasis
    decision: Literal["admitted", "existing", "rejected_fallback"]
    package_name: str = ""
    resolved_version: str = ""
    transitive_summary: dict[str, str] = Field(default_factory=dict)
    licence_result: str = ""
    vulnerability_policy_result: str = ""
    install_script_result: str = ""
    manifest_hash: str = ""
    lock_hash: str = ""
    cache_receipt: dict[str, str] = Field(default_factory=dict)
    fallback: dict[str, str] = Field(default_factory=dict)


class DependencyLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipts: list[DependencyReceipt] = Field(default_factory=list)
    dependency_ledger_hash: str = ""

    @model_validator(mode="after")
    def stamp_dependency_ledger_hash(self) -> DependencyLedger:
        payload = self.model_dump(mode="json", exclude={"dependency_ledger_hash"})
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.dependency_ledger_hash and self.dependency_ledger_hash != digest:
            raise ValueError("dependency_ledger_hash does not match the canonical ledger")
        self.dependency_ledger_hash = digest
        return self


class AcquireCallReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: str
    attempt_hash: str
    profile: str = ""
    response_id: str = ""
    model: str = ""
    usage: dict[str, int] = Field(default_factory=dict)
    finish_reason: str = ""
    total_request_count: int = 0
    admitted_count: int = 0
    fallback_count: int = 0
    rejected_count: int = 0
    request_rounds: int = 0
    plan_deltas: list[PlanDelta] = Field(default_factory=list)


class AcquisitionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_count: int = 0
    admitted_resource_count: int = 0
    fallback_resource_count: int = 0
    rejected_resource_count: int = 0
    dependency_decisions: dict[str, str] = Field(default_factory=dict)
    node_modules_recreated: bool = False
    ledger_hash: str = ""
    dependency_ledger_hash: str = ""
    attempts: int = 0


class RoutePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route_id: str
    path: str
    section_ids: list[str]
    responsive_outcome: str
    reduced_motion_outcome: str
    interaction_outcome: str
    purpose: str = ""
    section_order: list[str] = Field(default_factory=list)
    content_bindings: list[str] = Field(default_factory=list)
    fact_ids: list[str] = Field(default_factory=list)
    criterion_ids: list[str] = Field(default_factory=list)
    composition: RouteComposition = Field(default_factory=lambda: RouteComposition())
    responsive_behavior: ResponsiveBehavior = Field(default_factory=lambda: ResponsiveBehavior())
    interaction_ids: list[str] = Field(default_factory=list)
    planned_resource_slots: list[str] = Field(default_factory=list)


class WorkUnit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_id: str
    kind: Literal["foundation", "route", "route_batch", "route_compose", "integration"]
    route_id: str = ""
    route_ids: list[str] = Field(default_factory=list)
    owns_paths: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    section_ids: list[str] = Field(default_factory=list)
    required_shared_exports: list[str] = Field(default_factory=list)
    resource_slot_ids: list[str] = Field(default_factory=list)
    criterion_ids: list[str] = Field(default_factory=list)
    context_estimate: int = 0
    output_estimate: int = 0
    terminal: bool = False


class WorkGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    units: list[WorkUnit]
    terminal_integration_unit: str = ""


class RouteComposition(BaseModel):
    """Observable layout choices for one route, not free-form design prose."""

    model_config = ConfigDict(extra="forbid")

    hierarchy: str = ""
    layout_strategy: str = ""
    visual_anchor: str = ""
    evidence_treatment: str = ""
    section_transitions: str = ""
    avoid: list[str] = Field(default_factory=list)


class ResponsiveBehavior(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mobile_strategy: str = ""
    breakpoint_strategy: str = ""
    overflow_strategy: str = ""
    touch_target_strategy: str = ""


class CreativeConcept(BaseModel):
    """One content-specific visual concept considered before planning source."""

    model_config = ConfigDict(extra="forbid")

    concept_id: str
    thesis: str
    typography_direction: str
    composition_direction: str
    color_direction: str
    motion_direction: str
    resource_fit: list[str] = Field(default_factory=list)
    distinguishing_moves: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class CreativeDirectionSetV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-creative-direction-v2"] = (
        "code-generator-creative-direction-v2"
    )
    candidates: list[CreativeConcept]
    recommended_concept_id: str
    recommendation_basis: str

    @model_validator(mode="after")
    def validate_candidates(self) -> CreativeDirectionSetV2:
        ids = [item.concept_id for item in self.candidates]
        if len(ids) != 2 or len(set(ids)) != 2:
            raise ValueError("creative direction requires exactly two distinct candidates")
        if self.recommended_concept_id not in ids:
            raise ValueError("recommended concept must reference a candidate")
        if not all(
            item.thesis.strip()
            and item.typography_direction.strip()
            and item.composition_direction.strip()
            and item.distinguishing_moves
            for item in self.candidates
        ):
            raise ValueError("creative candidates must be concrete and distinguishable")
        return self


class ResponsiveState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    viewport: Literal["mobile", "tablet", "desktop"]
    layout_mode: str
    column_count: int = Field(ge=1, le=12)
    content_order: list[str] = Field(default_factory=list)
    gutter_px: int = Field(ge=0, le=160)
    gap_px: int = Field(ge=0, le=240)


class LayoutRegion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region_id: str
    route_id: str
    section_id: str
    composition_intent: str
    min_height_strategy: str
    max_measure_ch: int = Field(default=72, ge=20, le=120)
    responsive_states: list[ResponsiveState]
    allowed_overlap_with: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_responsive_states(self) -> LayoutRegion:
        if {item.viewport for item in self.responsive_states} != {
            "mobile",
            "tablet",
            "desktop",
        }:
            raise ValueError("layout regions require mobile, tablet, and desktop states")
        return self


class TypographyBindingV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_slot_id: str
    family: str
    weights: list[int]
    body_size_min_rem: float = Field(gt=0)
    body_size_max_rem: float = Field(gt=0)
    heading_scale_ratio: float = Field(gt=1, le=2.5)
    body_line_height: float = Field(ge=1, le=2.2)


class DesignTokenSystemV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    colors: dict[str, str]
    spacing_rem: list[float]
    radii_rem: list[float] = Field(default_factory=list)
    typography: TypographyBindingV2
    container_max_px: int = Field(ge=720, le=2400)


class MotionBeatV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motion_id: str
    route_id: str
    section_id: str = ""
    trigger: Literal["load", "viewport", "hover", "focus", "activate"]
    target_region_id: str
    properties: list[str]
    duration_ms: int = Field(ge=0, le=2000)
    easing: str
    stagger_ms: int = Field(default=0, ge=0, le=500)
    reduced_motion_replacement: str


class ResourceUsagePlanV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_slot_id: str
    route_id: str
    section_id: str
    region_id: str
    purpose: str
    alt_policy: Literal["decorative", "approved_text", "contextual_description"]
    crop_strategy: str = ""
    loading: Literal["eager", "lazy"] = "lazy"


class ExperienceBlueprintV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-experience-blueprint-v2"] = (
        "code-generator-experience-blueprint-v2"
    )
    selected_concept_id: str
    narrative_arc: str
    tokens: DesignTokenSystemV2
    layout_regions: list[LayoutRegion]
    resource_usage: list[ResourceUsagePlanV2] = Field(default_factory=list)
    motion_beats: list[MotionBeatV2] = Field(default_factory=list)
    anti_patterns: list[str] = Field(default_factory=list)


class ExecutionBindingV2(BaseModel):
    """Compiled executable placement for one resolved pack or acquired slot."""

    model_config = ConfigDict(extra="forbid")

    resource_slot_id: str
    route_id: str
    section_ids: list[str] = Field(default_factory=list)
    category: str
    purpose: str
    resolution_type: str
    local_paths: list[str] = Field(default_factory=list)
    package_name: str = ""
    expected_exports: list[str] = Field(default_factory=list)
    font_family: str = ""
    font_weights: list[str] = Field(default_factory=list)
    required: bool = False
    provenance: dict[str, str] = Field(default_factory=dict)
    responsive_behavior: str = ""
    reduced_motion_behavior: str = ""
    fallback_behavior: str = ""


class CreativeThesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thesis: str = ""
    distinction: str = ""
    narrative_arc: str = ""
    visual_tension: str = ""
    avoid: list[str] = Field(default_factory=list)


class VisualSystem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    typography: str = ""
    color_strategy: str = ""
    spacing_rhythm: str = ""
    surface_treatment: str = ""
    density_strategy: str = ""
    motion_vocabulary: str = ""


class ShellContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    navigation: str = ""
    main_landmark: str = ""
    footer_strategy: str = ""
    focus_treatment: str = ""
    route_transition: str = ""


class SharedComponentContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: str
    purpose: str
    visual_role: str
    expected_exports: list[str] = Field(default_factory=list)
    accessibility_contract: str = ""


class InteractionContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interaction_id: str
    route_id: str = ""
    trigger: str
    outcome: str
    keyboard_behavior: str
    reduced_motion_behavior: str
    target: str = ""
    expected_url: str = ""
    accessible_name: str = ""


class ResourceInventoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_id: str
    route_id: str = ""
    purpose: str
    disposition: Literal["bound", "slot", "fallback"]
    local_reference: str = ""
    fallback: str = ""


class AcceptanceCoverageItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    route_id: str = ""
    expected_outcome: str
    source_marker: str


class ExportedSignature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    export_name: str
    kind: Literal["component", "function", "type", "constant"]


class GenerationSelfCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_complete: bool = False
    owned_paths_only: bool = False
    facts_preserved: bool = False
    resource_bindings_resolved: bool = False
    reduced_motion_preserved: bool = False
    notes: list[str] = Field(default_factory=list)


class ResourceSlot(BaseModel):
    """A declared slot only; Phase 1 cannot ask to acquire a resource."""

    model_config = ConfigDict(extra="forbid")

    slot_id: str
    route_id: str = ""
    purpose: str
    status: Literal["recorded"] = "recorded"


class SitePlan(BaseModel):
    """The planner's accepted Phase 1 output. No source-file payload exists."""

    model_config = ConfigDict(extra="forbid")

    plan_id: str
    routes: list[RoutePlan]
    shared_systems: list[str] = Field(default_factory=list)
    resource_slots: list[ResourceSlot] = Field(default_factory=list)
    # Path ownership is compiled deterministically after the model call.  The
    # field remains in the transport schema for backward compatibility.
    work_graph: WorkGraph = Field(default_factory=lambda: WorkGraph(units=[]))
    creative_thesis: CreativeThesis = Field(default_factory=CreativeThesis)
    visual_system: VisualSystem = Field(default_factory=VisualSystem)
    shell: ShellContract = Field(default_factory=ShellContract)
    shared_component_contracts: list[SharedComponentContract] = Field(default_factory=list)
    interactions: list[InteractionContract] = Field(default_factory=list)
    resource_inventory: list[ResourceInventoryItem] = Field(default_factory=list)
    acceptance_coverage: list[AcceptanceCoverageItem] = Field(default_factory=list)
    experience_blueprint: ExperienceBlueprintV2 | None = None
    execution_bindings: list[ExecutionBindingV2] = Field(default_factory=list)


class SourceFileChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    operation: Literal["create", "replace"]
    complete_utf8_content: str


class GenerationChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files: list[SourceFileChange] = Field(default_factory=list)
    exported_signatures: list[ExportedSignature] = Field(default_factory=list)
    content_coverage: list[str] = Field(default_factory=list)
    criterion_coverage: list[str] = Field(default_factory=list)
    resource_usage: list[str] = Field(default_factory=list)
    interaction_coverage: list[str] = Field(default_factory=list)
    self_check: GenerationSelfCheck = Field(default_factory=GenerationSelfCheck)


class GenerationRequests(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_requests: list[ResourceRequest] = Field(default_factory=list)
    dependency_requests: list[DependencyRequest] = Field(default_factory=list)


class GenerationCannotComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    safe_reason: str
    missing_authority_or_capability: str = ""


class GenerationAccepted(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    verified_contracts: list[str] = Field(default_factory=list)


class GenerationResult(BaseModel):
    """Strict, tagged result returned by foundation/route/repair operations."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-generation-result-v1"] = (
        "code-generator-generation-result-v1"
    )
    operation_id: str
    based_on_context_receipt: str
    mode: Literal["changes", "requests", "accepted", "cannot_complete"]
    changes: GenerationChanges | None = None
    requests: GenerationRequests | None = None
    accepted: GenerationAccepted | None = None
    cannot_complete: GenerationCannotComplete | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_tagged_payload(cls, data: Any) -> Any:
        """Strict output schemas require every declared property, so models
        routinely fill more than one payload field. The mode tag decides which
        payload is real; the others are transport artifacts and are dropped
        instead of failing the whole response."""
        if not isinstance(data, dict):
            return data
        present = [
            key
            for key in ("changes", "requests", "accepted", "cannot_complete")
            if data.get(key) is not None
        ]
        mode = data.get("mode")
        valid_modes = {"changes", "requests", "accepted", "cannot_complete"}
        if mode in valid_modes and data.get(mode) is None:
            # The tag points at an empty payload; adopt the one present one.
            if len(present) == 1:
                mode = present[0]
                data["mode"] = mode
        elif mode not in valid_modes and len(present) == 1:
            mode = present[0]
            data["mode"] = mode
        if mode in valid_modes:
            for key in ("changes", "requests", "accepted", "cannot_complete"):
                if key != mode:
                    data[key] = None
        return data

    @model_validator(mode="after")
    def validate_tagged_payload(self) -> GenerationResult:
        payloads = {
            "changes": self.changes,
            "requests": self.requests,
            "accepted": self.accepted,
            "cannot_complete": self.cannot_complete,
        }
        if payloads[self.mode] is None:
            raise ValueError(f"mode={self.mode} requires its matching payload")
        if self.mode == "changes" and (self.changes is None or not self.changes.files):
            raise ValueError("changes mode requires at least one file")
        if self.mode == "requests" and (
            self.requests is None
            or not (self.requests.resource_requests or self.requests.dependency_requests)
        ):
            raise ValueError("requests mode requires a resource or dependency request")
        return self


class IntegrationFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    severity: Literal["blocking", "advisory"]
    route_id: str = ""
    section_id: str = ""
    owner_work_unit_id: str
    code: str
    evidence: str
    requested_outcome: str


class IntegrationReviewV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-integration-review-v1"] = (
        "code-generator-integration-review-v1"
    )
    status: Literal["accepted", "findings"]
    findings: list[IntegrationFinding] = Field(default_factory=list)
    distinctiveness_score: int = Field(ge=1, le=5)
    composition_score: int = Field(ge=1, le=5)
    typography_score: int = Field(ge=1, le=5)
    resource_fit_score: int = Field(ge=1, le=5)
    motion_score: int = Field(ge=1, le=5)

    @model_validator(mode="after")
    def validate_status(self) -> IntegrationReviewV1:
        if self.status == "accepted" and self.findings:
            raise ValueError("accepted integration review cannot contain findings")
        scores = (
            self.distinctiveness_score,
            self.composition_score,
            self.typography_score,
            self.resource_fit_score,
            self.motion_score,
        )
        if self.status == "accepted" and min(scores) < 4:
            raise ValueError(
                "accepted integration review requires every quality score to be at least 4"
            )
        if self.status == "findings" and not self.findings:
            raise ValueError("findings integration review requires findings")
        return self


class GenerationContextReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-context-v1"] = "code-generator-context-v1"
    receipt_id: str
    operation_id: str
    role_profile: str
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    output_schema_hash: str
    ordered_input_hashes: list[str] = Field(default_factory=list)
    owned_paths: list[str] = Field(default_factory=list)
    context_hash: str
    context_estimate: int = 0
    output_ceiling: int = 0
    stored_relative_path: str = ""


class GenerationCallReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-call-v1"] = "code-generator-call-v1"
    receipt_id: str
    operation_id: str
    idempotency_key: str
    context_receipt_hash: str
    result_hash: str
    profile: str
    response_id: str = ""
    model: str = ""
    usage: dict[str, int] = Field(default_factory=dict)
    finish_reason: str = ""


class SourceCheckpoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-source-checkpoint-v1"] = (
        "code-generator-source-checkpoint-v1"
    )
    checkpoint_id: str
    parent_checkpoint_hash: str = ""
    checkpoint_hash: str
    stored_relative_path: str
    manifest_path: str = ""
    source_manifest_hash: str
    file_count: int
    total_bytes: int
    work_unit_id: str
    accepted_at: str


class SourceDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnostic_id: str
    group: Literal["source_contract", "typecheck"]
    code: str
    severity: Literal["blocking", "advisory"] = "blocking"
    owner: Literal["generator", "infrastructure", "upstream"] = "generator"
    phase: str
    work_unit_id: str = ""
    route_id: str = ""
    command: str = ""
    normalized_message: str
    file: str = ""
    symbol: str = ""
    expected: str = ""
    observed: str = ""
    fingerprint: str


class GenerationWorkUnitProjection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_id: str
    kind: str
    status: str
    route_ids: list[str] = Field(default_factory=list)
    section_ids: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    owned_paths: list[str] = Field(default_factory=list)
    checkpoint_before: str = ""
    checkpoint_after: str = ""
    call_receipt_id: str = ""
    request_round: int = 0
    repair_round: int = 0
    diagnostics: list[str] = Field(default_factory=list)


class GenerationProjection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-generation-projection-v1"] = (
        "code-generator-generation-projection-v1"
    )
    generation_id: str
    input_receipt_hash: str
    site_plan_hash: str
    resource_ledger_hash: str = ""
    dependency_ledger_hash: str = ""
    phase: str
    active_work_unit_id: str = ""
    work_units: list[GenerationWorkUnitProjection] = Field(default_factory=list)
    accepted_checkpoint: SourceCheckpoint | None = None
    context_receipts: list[GenerationContextReceipt] = Field(default_factory=list)
    call_receipts: list[GenerationCallReceipt] = Field(default_factory=list)
    diagnostics: list[SourceDiagnostic] = Field(default_factory=list)
    repair_rounds: int = 0
    repair_budget_used: int = 0
    repair_fingerprint_counts: dict[str, int] = Field(default_factory=dict)
    repair_strategies: list[str] = Field(default_factory=list)
    request_rounds: int = 0
    source_ready: bool = False
    source_file_count: int = 0
    source_total_bytes: int = 0
    issues: list[SafeIssue] = Field(default_factory=list)


class CandidateIdentity(BaseModel):
    """Immutable identity tying every Phase 4 fact to one source attempt."""

    model_config = ConfigDict(extra="forbid")

    input_receipt_hash: str
    site_plan_hash: str
    work_graph_hash: str
    resource_ledger_hash: str = ""
    dependency_ledger_hash: str = ""
    source_checkpoint_hash: str
    source_manifest_hash: str
    scaffold_toolchain_profile_hash: str
    verification_profile_hash: str
    identity_hash: str = ""

    @model_validator(mode="after")
    def stamp_identity_hash(self) -> CandidateIdentity:
        payload = self.model_dump(mode="json", exclude={"identity_hash"})
        computed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.identity_hash and self.identity_hash != computed:
            raise ValueError("identity_hash does not match the candidate identity")
        self.identity_hash = computed
        return self


class VerificationProfile(BaseModel):
    """Trusted, configuration-derived final verification profile."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    schema_version: Literal["code-generator-verification-profile-v1"] = (
        "code-generator-verification-profile-v1"
    )
    source_check_ids: list[str] = Field(default_factory=list)
    build_check_ids: list[str] = Field(default_factory=list)
    runtime_check_ids: list[str] = Field(default_factory=list)
    browser_name: str = "chromium"
    browser_executable: str = ""
    viewport_profiles: dict[str, dict[str, int]] = Field(default_factory=dict)
    geometry_thresholds: dict[str, float] = Field(default_factory=dict)
    build_command: list[str] = Field(default_factory=lambda: ["npm", "run", "build"])
    typecheck_command: list[str] = Field(default_factory=lambda: ["npm", "run", "typecheck"])
    profile_hash: str = ""

    @model_validator(mode="after")
    def stamp_profile_hash(self) -> VerificationProfile:
        payload = self.model_dump(mode="json", exclude={"profile_hash"})
        computed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.profile_hash and self.profile_hash != computed:
            raise ValueError("profile_hash does not match the verification profile")
        self.profile_hash = computed
        return self


class VerificationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    action: Literal[
        "load",
        "navigate",
        "back",
        "forward",
        "click",
        "assert_link",
        "focus",
        "press",
        "assert_content",
        "assert_accessible",
        "assert_overflow",
        "assert_geometry",
    ]
    target: str = ""
    expected_url: str = ""
    expected_content_ids: list[str] = Field(default_factory=list)
    expected_text: list[str] = Field(default_factory=list)
    expected_accessible_name: str = ""
    expected_accessible_state: dict[str, bool | str] = Field(default_factory=dict)
    expected_focus: str = ""
    expected_outcome: str = ""


class VerificationJourney(BaseModel):
    model_config = ConfigDict(extra="forbid")

    journey_id: str
    route_id: str = ""
    start_path: str
    viewport_profile: str = "desktop"
    motion_profile: Literal["no-preference", "reduce"] = "no-preference"
    steps: list[VerificationStep] = Field(default_factory=list)


class VerificationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-verification-plan-v1"] = (
        "code-generator-verification-plan-v1"
    )
    based_on_candidate_identity: str
    source_checks: list[str] = Field(default_factory=list)
    build_checks: list[str] = Field(default_factory=list)
    runtime_journeys: list[VerificationJourney] = Field(default_factory=list)
    expected_local_resources: list[str] = Field(default_factory=list)
    expected_check_ids: list[str] = Field(default_factory=list)
    plan_hash: str = ""

    @model_validator(mode="after")
    def stamp_plan_hash(self) -> VerificationPlan:
        payload = self.model_dump(mode="json", exclude={"plan_hash"})
        computed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.plan_hash and self.plan_hash != computed:
            raise ValueError("plan_hash does not match the verification plan")
        self.plan_hash = computed
        return self


class BuildManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    media_type: str
    size_bytes: int
    sha256: str
    references: list[str] = Field(default_factory=list)


class BuildManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-build-manifest-v1"] = "code-generator-build-manifest-v1"
    candidate_identity_hash: str
    entry_paths: list[str] = Field(default_factory=list)
    entries: list[BuildManifestEntry] = Field(default_factory=list)
    total_bytes: int = 0
    build_hash: str = ""

    @model_validator(mode="after")
    def stamp_build_hash(self) -> BuildManifest:
        payload = self.model_dump(mode="json", exclude={"build_hash"})
        computed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.build_hash and self.build_hash != computed:
            raise ValueError("build_hash does not match the build manifest")
        self.build_hash = computed
        return self


class Diagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnostic_id: str
    group: Literal["source_contract", "type_build_artifact", "dom_runtime"]
    code: str
    severity: Literal["blocking", "advisory"] = "blocking"
    owner: Literal["generator", "infrastructure", "upstream"] = "generator"
    phase: str
    work_unit_id: str = ""
    route_id: str = ""
    interaction_id: str = ""
    command: str = ""
    normalized_message: str
    file: str = ""
    symbol: str = ""
    import_chain: list[str] = Field(default_factory=list)
    expected: str = ""
    observed: str = ""
    relevant_receipt_hashes: list[str] = Field(default_factory=list)
    fingerprint: str


class DiagnosticBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-diagnostic-bundle-v1"] = (
        "code-generator-diagnostic-bundle-v1"
    )
    based_on_checkpoint: str
    failed_group: Literal["source_contract", "type_build_artifact", "dom_runtime"]
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)
    affected_plan_slice: dict[str, Any] = Field(default_factory=dict)
    affected_resource_bindings: list[dict[str, Any]] = Field(default_factory=list)
    dependency_signatures: list[dict[str, Any]] = Field(default_factory=list)
    implicated_source_files: list[str] = Field(default_factory=list)
    bounded_related_source: dict[str, str] = Field(default_factory=dict)
    shared_api_signatures: list[dict[str, Any]] = Field(default_factory=list)
    prior_repair_strategies: list[str] = Field(default_factory=list)
    required_checks_after_change: list[str] = Field(default_factory=list)


class GateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_id: Literal["source_contract", "type_build_artifact", "dom_runtime"]
    status: Literal["passed", "failed", "skipped"]
    candidate_identity_hash: str
    build_hash: str = ""
    expected_check_ids: list[str] = Field(default_factory=list)
    executed_check_ids: list[str] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    evidence_hash: str = ""


class RuntimeEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    journey_id: str
    route_id: str = ""
    start_path: str
    final_url: str = ""
    title: str = ""
    content_ids: list[str] = Field(default_factory=list)
    requests: list[dict[str, str | int | bool]] = Field(default_factory=list)
    console_errors: list[str] = Field(default_factory=list)
    page_errors: list[str] = Field(default_factory=list)
    csp_violations: list[str] = Field(default_factory=list)
    focus_results: list[dict[str, str | bool]] = Field(default_factory=list)
    overflow_results: list[dict[str, str | int | bool]] = Field(default_factory=list)
    geometry_results: list[dict[str, Any]] = Field(default_factory=list)
    passed: bool


class RepairReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-repair-receipt-v1"] = "code-generator-repair-receipt-v1"
    generation_id: str
    diagnostic_fingerprints: list[str]
    strategy_summary: str
    based_on_checkpoint: str
    context_receipt: str
    allowed_paths: list[str] = Field(default_factory=list)
    resource_or_dependency_receipts: list[str] = Field(default_factory=list)
    changed_file_hashes: dict[str, str] = Field(default_factory=dict)
    corrected_checkpoint: str
    checks_rerun: list[str] = Field(default_factory=list)
    accepted_at: str
    receipt_hash: str = ""

    @model_validator(mode="after")
    def stamp_receipt_hash(self) -> RepairReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_hash"})
        computed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.receipt_hash and self.receipt_hash != computed:
            raise ValueError("receipt_hash does not match the repair receipt")
        self.receipt_hash = computed
        return self


class CandidateArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    candidate_identity_hash: str
    build_hash: str
    key: str
    sha256: str
    size_bytes: int
    content_type: str = "application/zip"
    route_ids: list[str] = Field(default_factory=list)
    created_at: str
    expires_at: str


class PromotionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-promotion-receipt-v1"] = (
        "code-generator-promotion-receipt-v1"
    )
    promotion_id: str
    run_id: str
    candidate_id: str
    candidate_identity_hash: str
    build_hash: str
    artifact_sha256: str
    verification_report_hash: str
    previous_pointer_etag: str = ""
    active_pointer_etag: str = ""
    promoted_at: str
    receipt_hash: str = ""

    @model_validator(mode="after")
    def stamp_receipt_hash(self) -> PromotionReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_hash"})
        computed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.receipt_hash and self.receipt_hash != computed:
            raise ValueError("receipt_hash does not match the promotion receipt")
        self.receipt_hash = computed
        return self


class PendingPromotion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    promotion_id: str
    candidate: CandidateArtifact
    verification_report_hash: str
    expected_revision: int
    previous_pointer_etag: str = ""
    created_at: str


class ActivePreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str
    url: str
    candidate_id: str
    candidate_identity_hash: str
    build_hash: str
    receipt_key: str
    receipt_hash: str
    pointer_etag: str
    route_ids: list[str] = Field(default_factory=list)
    promoted_at: str


class TerminalFailureReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-terminal-failure-v1"] = (
        "code-generator-terminal-failure-v1"
    )
    generation_id: str
    terminal_code: str
    owner: Literal["generator", "infrastructure", "upstream"]
    phase: str
    input_plan_source_build_hashes: dict[str, str] = Field(default_factory=dict)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    fingerprint_occurrences: dict[str, int] = Field(default_factory=dict)
    resource_dependency_failures: list[SafeIssue] = Field(default_factory=list)
    accepted_checkpoint: str = ""
    repair_receipts: list[str] = Field(default_factory=list)
    active_preview_preserved: bool = True
    safe_user_summary: str
    recommended_next_action: str


class VerificationProjection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-verification-projection-v1"] = (
        "code-generator-verification-projection-v1"
    )
    generation_id: str
    candidate_identity: CandidateIdentity
    verification_profile: VerificationProfile
    verification_plan: VerificationPlan | None = None
    phase: str
    active_gate: str = ""
    build_manifest: BuildManifest | None = None
    build_hash: str = ""
    gate_results: list[GateResult] = Field(default_factory=list)
    runtime_evidence: list[RuntimeEvidence] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    diagnostic_bundle: DiagnosticBundle | None = None
    repair_receipts: list[RepairReceipt] = Field(default_factory=list)
    candidate_artifact: CandidateArtifact | None = None
    terminal_failure: TerminalFailureReport | None = None
    repair_rounds: int = 0
    status: Literal[
        "queued", "building", "smoke_testing", "repairing", "ready", "needs_attention"
    ] = "queued"
    verification_report_hash: str = ""


class DevelopmentEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int
    event_type: str
    level: Literal["info", "warning", "error"] = "info"
    message: str
    details: dict[str, str | int | float | bool] = Field(default_factory=dict)
    created_at: str


class DevelopmentRunProjection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: DevelopmentRunStatus
    revision: int
    current_attempt: int = 0
    run_mode: Literal["development", "session"] = "development"
    portfolio_session_id: str = ""
    auto_advance: bool = True
    coordinator_stage: str = "plan"
    pipeline_contract_version: str = "code-generator-v3"
    trace_id: str = ""
    active_attempt_id: str = ""
    retry_status: str = ""
    stage_durations_ms: dict[str, float] = Field(default_factory=dict)
    worker_storage_readiness: dict[str, str | bool] = Field(default_factory=dict)
    advisories: list[SafeIssue] = Field(default_factory=list)
    selected_pack_receipt: dict[str, Any] | None = None
    build_preparation_source_ref: dict[str, Any] | None = None
    artifact_reference: dict[str, Any] | None = None
    artifact_receipt: dict[str, Any] | None = None
    preflight_receipt: dict[str, Any] | None = None
    creative_direction: dict[str, Any] | None = None
    integration_review: dict[str, Any] | None = None
    job_id: str = ""
    input: AdmittedInputReference
    input_receipt: InputReceipt | None = None
    context_receipt: ContextReceipt | None = None
    planner_receipt: PlannerCallReceipt | None = None
    plan_summary: dict[str, int | str | list[str]] = Field(default_factory=dict)
    acquire_receipt: AcquireCallReceipt | None = None
    resource_ledger: ResourceLedger | None = None
    dependency_ledger: DependencyLedger | None = None
    acquire_summary: AcquisitionSummary | None = None
    plan_delta_count: int = 0
    generation_job_id: str = ""
    generation: GenerationProjection | None = None
    source_checkpoint: SourceCheckpoint | None = None
    source_summary: dict[str, int | str | bool] = Field(default_factory=dict)
    verification_job_id: str = ""
    verification: VerificationProjection | None = None
    candidate_artifact: CandidateArtifact | None = None
    pending_promotion: PendingPromotion | None = None
    active_preview: ActivePreview | None = None
    terminal_failure: TerminalFailureReport | None = None
    issues: list[SafeIssue] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class FixtureRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_id: str


class BuildPreparationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Mirror pack directory name, or "best" for deterministic ranking.
    pack: str = "best"
