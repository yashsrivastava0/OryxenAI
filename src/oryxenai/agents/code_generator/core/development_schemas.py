"""Strict contracts for the standalone Code Generator development workflow."""

from __future__ import annotations

import hashlib
import json
import math
import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)


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
    PREVIEW_PENDING = "preview_pending"
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
    attempt: int = 1
    retry_class: str = ""
    duration_ms: float = Field(default=0.0, ge=0)
    cached_tokens: int = Field(default=0, ge=0)
    operation: str = "code_generator.plan"
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
    storage_key: str = ""
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
    interaction_ids: list[str] = Field(default_factory=list)
    owns_route_shell: bool = False
    isolated_workspace_key: str = ""
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


class TypedTokenGroupV3(BaseModel):
    """One portfolio-authored semantic token group.

    Values are intentionally concrete.  The compiler rejects hidden fallback
    values so the scaffold cannot quietly reintroduce a house palette.
    """

    model_config = ConfigDict(extra="forbid")

    group_id: Literal["color", "typography", "spacing", "shape", "motion"]
    values: dict[str, str | int | float]

    @model_validator(mode="after")
    def validate_values(self) -> TypedTokenGroupV3:
        if not self.values or any(not str(key).strip() for key in self.values):
            raise ValueError("typed token groups require named concrete values")
        for value in self.values.values():
            if isinstance(value, str) and "var(" in value and "," in value:
                raise ValueError("token values may not contain CSS fallback expressions")
        return self


class DesignTokenSystemV3(DesignTokenSystemV2):
    model_config = ConfigDict(extra="forbid")

    token_groups: list[TypedTokenGroupV3]

    @model_validator(mode="after")
    def validate_groups(self) -> DesignTokenSystemV3:
        groups = [item.group_id for item in self.token_groups]
        if len(groups) != len(set(groups)):
            raise ValueError("typed token group IDs must be unique")
        required = {"color", "typography", "spacing", "shape", "motion"}
        if set(groups) != required:
            raise ValueError(
                "v3 tokens require color, typography, spacing, shape, and motion groups"
            )
        return self


class RouteShellV3(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route_id: str
    navigation_owner: str
    main_owner: str
    footer_owner: str
    h1_owner: str
    section_order: list[str]


class DistinctiveMoveV3(BaseModel):
    model_config = ConfigDict(extra="forbid")

    move_id: str
    route_id: str
    thesis: str
    implementation_constraint: str
    anti_pattern_avoided: str = ""


class InteractionAssignmentV3(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interaction_id: str
    route_id: str
    owner_work_unit_id: str
    source_marker: str
    accessible_outcome: str


class ResourcePlacementV3(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_slot_id: str
    route_id: str
    section_id: str
    region_id: str
    purpose: str
    executable_path: str = ""


class MotionBeatV3(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motion_id: str
    route_id: str
    section_id: str
    region_id: str
    trigger: Literal["load", "viewport", "hover", "focus", "activate"]
    properties: list[str]
    duration_ms: int = Field(ge=0, le=2000)
    easing: str
    reduced_motion_replacement: str


class ExperienceBlueprintV3(BaseModel):
    """Design-neutral blueprint with explicit ownership and placement."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-experience-blueprint-v3"] = (
        "code-generator-experience-blueprint-v3"
    )
    selected_concept_id: str
    narrative_arc: str
    tokens: DesignTokenSystemV3
    layout_regions: list[LayoutRegion]
    resource_usage: list[ResourceUsagePlanV2] = Field(default_factory=list)
    route_shells: list[RouteShellV3]
    distinctive_moves: list[DistinctiveMoveV3]
    assigned_interactions: list[InteractionAssignmentV3] = Field(default_factory=list)
    resource_placements: list[ResourcePlacementV3] = Field(default_factory=list)
    motion_beats: list[MotionBeatV3] = Field(default_factory=list)
    anti_patterns: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_v3_fields(self) -> ExperienceBlueprintV3:
        if not self.distinctive_moves:
            raise ValueError("v3 blueprints require at least one distinctive move")
        shell_ids = [item.route_id for item in self.route_shells]
        if len(shell_ids) != len(set(shell_ids)):
            raise ValueError("route shell IDs must be unique")
        if any(
            not item.thesis.strip() or not item.implementation_constraint.strip()
            for item in self.distinctive_moves
        ):
            raise ValueError("distinctive moves require a thesis and implementation constraint")
        interaction_ids = [item.interaction_id for item in self.assigned_interactions]
        if len(interaction_ids) != len(set(interaction_ids)):
            raise ValueError("assigned interaction IDs must be unique")
        return self


# ---------------------------------------------------------------------------
# V4 transport contracts
# ---------------------------------------------------------------------------
# These DTOs deliberately use closed lists and concrete scalar values.  The
# provider boundary can therefore send the same schema to Anthropic/OpenAI
# native structured-output endpoints without arbitrary JSON maps or tagged
# nullable unions.  The existing V2/V3 models remain readable for old packs.


_CSS_COLOR_RE = re.compile(
    r"^(?:#[0-9a-f]{3,8}|(?:rgb|rgba|hsl|hsla)\([^;{}]+\)|[a-z][a-z0-9-]*)$",
    re.IGNORECASE,
)
_CSS_UNIT_RE = re.compile(r"^(?:px|rem|em|%|vw|vh|vmin|vmax|ch|ex|fr|ms|s)$")
_CSS_SOURCE_SIZE_LENGTH_RE = re.compile(
    r"^(?:0|(?:\d+(?:\.\d*)?|\.\d+)(?:px|cm|mm|q|in|pc|pt|rem|em|ex|ch|cap|ic|lh|rlh|vw|vh|vi|vb|vmin|vmax|svw|svh|svi|svb|svmin|svmax|lvw|lvh|lvi|lvb|lvmin|lvmax|dvw|dvh|dvi|dvb|dvmin|dvmax|cqw|cqh|cqi|cqb|cqmin|cqmax|fr|%))$",
    re.IGNORECASE,
)
_CSS_SOURCE_SIZE_FUNCTION_RE = re.compile(
    r"^(?:calc|min|max|clamp|var|env)\([^{};\"']+\)$",
    re.IGNORECASE,
)
_CSS_WORD_LENGTH_RE = re.compile(
    r"(?<![\w-])[a-z][a-z0-9-]*\s*(?:px|cm|mm|q|in|pc|pt|rem|em|ex|ch|cap|ic|lh|rlh|vw|vh|vi|vb|vmin|vmax|svw|svh|svi|svb|svmin|svmax|lvw|lvh|lvi|lvb|lvmin|lvmax|dvw|dvh|dvi|dvb|dvmin|dvmax|cqw|cqh|cqi|cqb|cqmin|cqmax|fr|%)(?![\w-])",
    re.IGNORECASE,
)
_CSS_MEDIA_DIMENSION_RE = re.compile(
    r"\b(?:min|max)-(?:width|height)\s*:\s*([^\s,)]+)",
    re.IGNORECASE,
)
_EASING_RE = re.compile(
    r"^(?:linear|ease(?:-in|-out|-in-out)?|cubic-bezier\([^()]+\)|steps\([^()]+\))$",
    re.IGNORECASE,
)


def _balanced_parentheses(value: str) -> bool:
    depth = 0
    for character in value:
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _split_top_level_commas(value: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(value):
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        elif character == "," and depth == 0:
            parts.append(value[start:index].strip())
            start = index + 1
    parts.append(value[start:].strip())
    return parts


def _is_concrete_source_size(value: str) -> bool:
    normalized = value.strip()
    if normalized.casefold() == "auto":
        return True
    if _CSS_SOURCE_SIZE_LENGTH_RE.fullmatch(normalized):
        return True
    return bool(
        _CSS_SOURCE_SIZE_FUNCTION_RE.fullmatch(normalized)
        and _balanced_parentheses(normalized)
        and not _CSS_WORD_LENGTH_RE.search(normalized)
    )


def _validate_source_sizes(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized or any(character in normalized for character in ('"', "'", ";", "{", "}")):
        raise ValueError(
            "resource placement sizes require a concrete browser-safe CSS sizes policy"
        )
    if not _balanced_parentheses(normalized):
        raise ValueError("resource placement sizes must have balanced CSS parentheses")
    if _CSS_WORD_LENGTH_RE.search(normalized):
        raise ValueError(
            "resource placement sizes must use numeric CSS lengths; do not spell out a number"
        )
    for component in _split_top_level_commas(normalized):
        if not component:
            raise ValueError("resource placement sizes cannot contain an empty source-size item")
        for match in _CSS_MEDIA_DIMENSION_RE.finditer(component):
            dimension = match.group(1)
            if dimension.casefold().startswith(("calc(", "min(", "max(", "clamp(", "var(")):
                continue
            if not _is_concrete_source_size(dimension):
                raise ValueError(
                    "resource placement media conditions must use concrete CSS lengths"
                )
        if _CSS_SOURCE_SIZE_FUNCTION_RE.fullmatch(component):
            continue
        source_size = component.rsplit(")", 1)[-1].strip()
        if not _is_concrete_source_size(source_size):
            raise ValueError(
                "resource placement sizes must end each item with a numeric CSS length, "
                "auto, or calc/min/max/clamp expression"
            )
    return normalized


class NamedColorTokenV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    value: str

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        normalized = value.strip().replace("_", "-")
        if not re.fullmatch(r"[a-z][a-z0-9-]*", normalized):
            raise ValueError("color token names must be lowercase semantic identifiers")
        return normalized

    @field_validator("value")
    @classmethod
    def _value(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized or not _CSS_COLOR_RE.fullmatch(normalized):
            raise ValueError("color tokens must be concrete CSS color values")
        if "var(" in normalized.casefold() or "url(" in normalized.casefold():
            raise ValueError("color tokens may not reference variables or URLs")
        return normalized


class LengthTokenV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    value: float
    unit: Literal["px", "rem", "em", "%", "vw", "vh", "vmin", "vmax", "ch", "ex", "fr"]

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        normalized = value.strip().replace("_", "-")
        if not re.fullmatch(r"[a-z][a-z0-9-]*", normalized):
            raise ValueError("length token names must be lowercase semantic identifiers")
        return normalized

    @field_validator("value")
    @classmethod
    def _finite(cls, value: float) -> float:
        if not math.isfinite(value) or value < 0:
            raise ValueError("length token values must be finite and non-negative")
        return value


class BorderTokenV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    width: LengthTokenV4
    style: Literal["solid", "dashed", "dotted", "double", "none"] = "solid"
    color_token: str


class MotionTokenV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    duration_ms: int = Field(ge=0, le=5000)
    easing: str

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        normalized = value.strip().replace("_", "-")
        if not re.fullmatch(r"[a-z][a-z0-9-]*", normalized):
            raise ValueError("motion token names must be lowercase semantic identifiers")
        return normalized

    @field_validator("easing")
    @classmethod
    def _easing(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not _EASING_RE.fullmatch(normalized):
            raise ValueError("motion easing must be a validated CSS easing value")
        return normalized


class TypographyBindingV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["body", "display"] = Field(
        description="Explicit typography role. Emit exactly one body role and optionally one display role."
    )
    approved_font_slot: str
    family: str
    weights: list[int] = Field(min_length=1, max_length=8)
    style: Literal["normal", "italic", "oblique"] = "normal"
    local_files: list[str] = Field(min_length=1, max_length=16)
    body_min_rem: float = Field(gt=0, le=4)
    body_max_rem: float = Field(gt=0, le=8)
    heading_ratio: float = Field(gt=1, le=3)
    body_line_height: float = Field(ge=1, le=2.4)
    tracking_em: float = Field(default=0.0, ge=-0.2, le=0.5)
    font_display: Literal["swap", "fallback", "optional"] = "swap"

    @field_validator("approved_font_slot", "family")
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized or any(char in normalized for char in ('"', "'", ";", "\n", "\r")):
            raise ValueError("typography bindings require safe non-empty text")
        return normalized

    @field_validator("weights")
    @classmethod
    def _weights(cls, value: list[int]) -> list[int]:
        if any(item < 100 or item > 1000 or item % 100 for item in value):
            raise ValueError("font weights must be CSS numeric weights")
        return sorted(set(value))

    @model_validator(mode="after")
    def _size_order(self) -> TypographyBindingV4:
        if self.body_min_rem > self.body_max_rem:
            raise ValueError("body_min_rem must not exceed body_max_rem")
        normalized_files: list[str] = []
        for value in self.local_files:
            path = value.replace("\\", "/").lstrip("/")
            if (
                not path
                or ".." in path.split("/")
                or path.casefold().startswith(("http:", "https:", "data:"))
                or not path.casefold().endswith((".woff", ".woff2"))
            ):
                raise ValueError("font roles may reference only safe local WOFF/WOFF2 files")
            normalized_files.append(path)
        self.local_files = list(dict.fromkeys(normalized_files))
        return self


class FluidTypeStepV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    role: Literal["body", "display"]
    minimum_rem: float = Field(gt=0, le=12)
    maximum_rem: float = Field(gt=0, le=20)
    line_height: float = Field(ge=0.8, le=2.4)
    tracking_em: float = Field(ge=-0.2, le=0.5)

    @model_validator(mode="after")
    def _ordered(self) -> FluidTypeStepV4:
        if self.minimum_rem > self.maximum_rem:
            raise ValueError("fluid type minimum must not exceed its maximum")
        normalized = self.name.strip().replace("_", "-")
        if not re.fullmatch(r"[a-z][a-z0-9-]*", normalized):
            raise ValueError("fluid type steps require semantic identifiers")
        self.name = normalized
        return self


class ShadowTokenV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    offset_x: LengthTokenV4
    offset_y: LengthTokenV4
    blur: LengthTokenV4
    spread: LengthTokenV4
    color_token: str


class ContainerTokenV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    maximum: LengthTokenV4
    inline_padding: LengthTokenV4


class DesignTokenSystemV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    colors: list[NamedColorTokenV4] = Field(min_length=1, max_length=32)
    spacing: list[LengthTokenV4] = Field(min_length=1, max_length=32)
    sizes: list[LengthTokenV4] = Field(default_factory=list, max_length=32)
    radii: list[LengthTokenV4] = Field(default_factory=list, max_length=16)
    borders: list[BorderTokenV4] = Field(default_factory=list, max_length=16)
    shadows: list[ShadowTokenV4] = Field(default_factory=list, max_length=16)
    motion: list[MotionTokenV4] = Field(default_factory=list, max_length=16)
    typography_roles: list[TypographyBindingV4] = Field(
        min_length=1,
        max_length=2,
        description=(
            "One or two roles: exactly one object with role body and optionally one object "
            "with role display; every role value is explicit."
        ),
    )
    type_steps: list[FluidTypeStepV4] = Field(min_length=2, max_length=12)
    containers: list[ContainerTokenV4] = Field(min_length=1, max_length=8)
    container_max_px: int = Field(ge=480, le=2400)

    @model_validator(mode="after")
    def _unique_names_and_bindings(self) -> DesignTokenSystemV4:
        for values in (
            self.colors,
            self.spacing,
            self.sizes,
            self.radii,
            self.borders,
            self.shadows,
            self.motion,
            self.containers,
        ):
            names = [item.name for item in values]
            if len(names) != len(set(names)):
                raise ValueError("token names must be unique within each group")
        color_names = {item.name for item in self.colors}
        bound_color_names = {item.color_token for item in self.borders} | {
            item.color_token for item in self.shadows
        }
        if not bound_color_names <= color_names:
            raise ValueError("border and shadow tokens must reference an approved color token")
        roles = [item.role for item in self.typography_roles]
        if len(roles) != len(set(roles)) or "body" not in roles:
            raise ValueError("v4 typography requires one body role and at most one display role")
        if any(item.role not in roles for item in self.type_steps):
            raise ValueError("fluid type steps must reference an approved typography role")
        type_names = [item.name for item in self.type_steps]
        if len(type_names) != len(set(type_names)):
            raise ValueError("fluid type step names must be unique")
        return self

    @property
    def typography(self) -> TypographyBindingV4:
        """Compatibility accessor for internal v3-era compiler code."""

        return next(item for item in self.typography_roles if item.role == "body")


class RouteShellV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route_id: str
    storage_key: str
    navigation_owner: Literal["trusted_shell"] = "trusted_shell"
    main_owner: Literal["trusted_shell"] = "trusted_shell"
    footer_owner: Literal["trusted_shell"] = "trusted_shell"
    h1_owner: str
    section_order: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _concrete(self) -> RouteShellV4:
        if not all(value.strip() for value in (self.route_id, self.storage_key, self.h1_owner)):
            raise ValueError("v4 route shells require route, storage, and h1 owner IDs")
        if len(self.section_order) != len(set(self.section_order)) or any(
            not value.strip() for value in self.section_order
        ):
            raise ValueError("v4 route shells require a unique non-empty section order")
        return self


class SectionRegionV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region_id: str
    route_id: str
    section_id: str
    owner_id: str
    section_selector: str
    region_selector: str
    content_ids: list[str] = Field(default_factory=list, max_length=256)
    criterion_ids: list[str] = Field(default_factory=list, max_length=64)
    order_mobile: int = Field(ge=0, le=100)
    order_tablet: int = Field(ge=0, le=100)
    order_desktop: int = Field(ge=0, le=100)
    columns_mobile: int = Field(ge=1, le=4)
    columns_tablet: int = Field(ge=1, le=12)
    columns_desktop: int = Field(ge=1, le=12)
    max_measure_ch: int = Field(ge=20, le=120)
    gap: LengthTokenV4
    allowable_overlap: bool = False
    width_ratio_min: float = Field(default=0.2, gt=0, le=1)
    width_ratio_max: float = Field(default=1.0, gt=0, le=1)
    overlap_ratio_max: float = Field(default=0.0, ge=0, le=0.75)
    sticky_allowed: bool = False

    @model_validator(mode="after")
    def _geometry_range(self) -> SectionRegionV4:
        if self.width_ratio_min > self.width_ratio_max:
            raise ValueError("region width ratio minimum must not exceed its maximum")
        if not self.allowable_overlap and self.overlap_ratio_max:
            raise ValueError("regions without overlap authority must use a zero overlap ratio")
        if not all(
            value.strip() for value in (self.owner_id, self.section_selector, self.region_selector)
        ):
            raise ValueError("section regions require exact owner and selector identities")
        return self


class DistinctiveMoveV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    move_id: str
    route_id: str
    section_id: str
    region_id: str
    implementation_kind: Literal[
        "asymmetric_width",
        "alignment_spine",
        "controlled_overlap",
        "sticky_narrative_rail",
        "framed_evidence_sequence",
        "isolated_closing_composition",
        "custom",
    ]
    thesis: str
    runtime_marker: str
    source_selector: str
    target_selector: str
    relationship: Literal[
        "width_ratio",
        "horizontal_offset",
        "vertical_overlap",
        "shared_alignment_axis",
        "sticky_within_section",
        "isolated_spacing",
    ]
    minimum_ratio: float = Field(ge=-2, le=2)
    maximum_ratio: float = Field(ge=-2, le=2)
    viewports: list[Literal["mobile", "tablet", "desktop"]] = Field(min_length=1, max_length=3)
    required_css_properties: list[str] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def _concrete(self) -> DistinctiveMoveV4:
        if not all(
            value.strip()
            for value in (
                self.move_id,
                self.route_id,
                self.section_id,
                self.region_id,
                self.thesis,
                self.runtime_marker,
                self.source_selector,
                self.target_selector,
            )
        ):
            raise ValueError("distinctive moves require executable runtime evidence")
        if any(not value.strip() for value in self.required_css_properties):
            raise ValueError("distinctive moves require non-empty CSS property names")
        if self.minimum_ratio > self.maximum_ratio:
            raise ValueError("distinctive move ratio minimum must not exceed its maximum")
        self.viewports = list(dict.fromkeys(self.viewports))
        return self


class InteractionAssignmentV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interaction_id: str
    route_id: str
    owner_work_unit_id: str
    literal_marker: str
    target_selector: str
    outcome_selector: str
    trigger: Literal["click", "activate", "disclosure", "navigation", "download"]
    keyboard_behavior: str
    state_transition: str
    focus_behavior: str
    expected_navigation: str = ""
    expected_state_attribute: str = ""
    expected_state_value: str = ""

    @model_validator(mode="after")
    def _concrete(self) -> InteractionAssignmentV4:
        if not all(
            value.strip()
            for value in (
                self.interaction_id,
                self.route_id,
                self.owner_work_unit_id,
                self.literal_marker,
                self.target_selector,
                self.outcome_selector,
                self.keyboard_behavior,
                self.state_transition,
                self.focus_behavior,
            )
        ):
            raise ValueError(
                "v4 interactions require exact route, owner, selector, and state fields"
            )
        if self.trigger == "navigation" and not self.expected_navigation.strip():
            raise ValueError("navigation interactions require an expected route outcome")
        return self


class ResourcePlacementV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_slot_id: str
    route_id: str
    section_id: str
    element_marker: str
    element_selector: str
    alt_policy: Literal["decorative", "approved_text", "contextual_description"]
    fit: Literal["cover", "contain", "natural"]
    focal_position: str = "center"
    loading: Literal["eager", "lazy"] = "lazy"
    responsive_behavior: str
    sizes: str
    aspect_ratio_min: float = Field(gt=0, le=10)
    aspect_ratio_max: float = Field(gt=0, le=10)
    minimum_visible_ratio: float = Field(default=0.25, gt=0, le=1)

    @model_validator(mode="after")
    def _aspect_range(self) -> ResourcePlacementV4:
        if not all(
            value.strip()
            for value in (
                self.resource_slot_id,
                self.route_id,
                self.section_id,
                self.element_marker,
            )
        ):
            raise ValueError("resource placements require exact route, section, and marker IDs")
        if self.aspect_ratio_min > self.aspect_ratio_max:
            raise ValueError("resource aspect ratio minimum must not exceed its maximum")
        if not self.element_selector.strip() or not self.sizes.strip():
            raise ValueError("resource placements require exact selectors and sizes policy")
        return self

    @field_validator("sizes")
    @classmethod
    def _sizes(cls, value: str) -> str:
        return _validate_source_sizes(value)


class MotionPropertyExpectationV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    property_name: str
    before_value: str
    after_value: str

    @model_validator(mode="after")
    def _concrete(self) -> MotionPropertyExpectationV4:
        if not all(
            value.strip() for value in (self.property_name, self.before_value, self.after_value)
        ):
            raise ValueError("motion property expectations require before and after values")
        return self


class MotionBeatV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motion_id: str
    route_id: str
    section_id: str
    target_marker: str
    target_selector: str
    trigger_selector: str
    trigger: Literal["load", "viewport", "hover", "focus", "activate"]
    changed_properties: list[MotionPropertyExpectationV4] = Field(min_length=1, max_length=8)
    duration_min_ms: int = Field(ge=0, le=5000)
    duration_max_ms: int = Field(ge=0, le=5000)
    easing: str
    purposeful_outcome: str
    performance_budget_ms: int = Field(ge=0, le=100)
    reduced_motion_replacement: str

    @model_validator(mode="after")
    def _range(self) -> MotionBeatV4:
        if (
            self.duration_min_ms > self.duration_max_ms
            or not self.motion_id.strip()
            or not self.route_id.strip()
            or not self.section_id.strip()
            or not self.target_marker.strip()
            or not self.trigger_selector.strip()
            or not self.reduced_motion_replacement.strip()
            or not self.purposeful_outcome.strip()
            or not self.target_selector.strip()
        ):
            raise ValueError("motion beats require a valid duration range and reduced-motion rule")
        if not _EASING_RE.fullmatch(self.easing.strip()):
            raise ValueError("motion beats require a validated CSS easing value")
        return self


class CreativeConceptV3(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_id: str
    thesis: str
    hierarchy: str
    composition: str
    typography: str
    color_logic: str
    motion_vocabulary: str
    resource_use: str
    distinguishing_moves: list[str] = Field(min_length=1, max_length=8)
    anti_patterns: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def _content_specific(self) -> CreativeConceptV3:
        if not all(
            value.strip()
            for value in (
                self.concept_id,
                self.thesis,
                self.hierarchy,
                self.composition,
                self.typography,
                self.color_logic,
                self.motion_vocabulary,
                self.resource_use,
            )
        ) or any(not value.strip() for value in self.distinguishing_moves):
            raise ValueError("creative concepts require content-specific non-empty direction")
        return self


class CreativeDirectionSetV3(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-creative-direction-v3"] = (
        "code-generator-creative-direction-v3"
    )
    concepts: list[CreativeConceptV3] = Field(
        min_length=2,
        max_length=2,
        validation_alias=AliasChoices("concepts", "candidates"),
        serialization_alias="concepts",
    )
    recommended_concept_id: str
    recommendation_basis: str

    @model_validator(mode="after")
    def _materially_distinct(self) -> CreativeDirectionSetV3:
        ids = [item.concept_id for item in self.concepts]
        if len(set(ids)) != 2 or self.recommended_concept_id not in ids:
            raise ValueError("creative direction requires exactly two distinct concepts")

        def signature(item: CreativeConceptV3) -> tuple[str, ...]:
            return tuple(
                " ".join(value.casefold().split())
                for value in (
                    item.hierarchy,
                    item.composition,
                    item.typography,
                    item.motion_vocabulary,
                    item.resource_use,
                )
            )

        first, second = signature(self.concepts[0]), signature(self.concepts[1])
        different_dimensions = sum(left != right for left, right in zip(first, second, strict=True))
        if different_dimensions < 3:
            raise ValueError(
                "creative concepts must differ in at least three normalized design dimensions"
            )
        if not self.recommendation_basis.strip():
            raise ValueError("creative direction requires a recommendation basis")
        return self

    @property
    def candidates(self) -> list[CreativeConceptV3]:
        return self.concepts


class DesignVariantReceiptV1(BaseModel):
    """Persistent design identity reused by retries and replaced by regeneration."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["design-variant-receipt-v1"] = "design-variant-receipt-v1"
    variant_id: str
    ordinal: int = Field(ge=1)
    input_hash: str
    seed_hash: str
    prior_design_fingerprints: list[str] = Field(default_factory=list, max_length=3)
    creation_reason: Literal["initial", "regenerate", "retry"]
    created_at: str
    receipt_hash: str = ""

    @model_validator(mode="after")
    def _stamp(self) -> DesignVariantReceiptV1:
        if not all(
            value.strip()
            for value in (
                self.variant_id,
                self.input_hash,
                self.seed_hash,
                self.created_at,
            )
        ):
            raise ValueError("design variant receipts require immutable identity fields")
        self.prior_design_fingerprints = list(dict.fromkeys(self.prior_design_fingerprints))[-3:]
        payload = self.model_dump(mode="json", exclude={"receipt_hash"})
        computed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.receipt_hash and self.receipt_hash != computed:
            raise ValueError("receipt_hash does not match the design variant receipt")
        self.receipt_hash = computed
        return self


class DesignFingerprintV1(BaseModel):
    """Content-free normalized design characteristics used only across regenerations."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["design-fingerprint-v1"] = "design-fingerprint-v1"
    layout_topology: list[str] = Field(min_length=1)
    token_relationships: list[str] = Field(min_length=1)
    typography_roles: list[str] = Field(min_length=1)
    distinctive_moves: list[str] = Field(min_length=1)
    motion_vocabulary: list[str] = Field(default_factory=list)
    resource_placement_topology: list[str] = Field(default_factory=list)
    fingerprint_hash: str = ""

    @model_validator(mode="after")
    def _normalize_and_stamp(self) -> DesignFingerprintV1:
        for field_name in (
            "layout_topology",
            "token_relationships",
            "typography_roles",
            "distinctive_moves",
            "motion_vocabulary",
            "resource_placement_topology",
        ):
            values = getattr(self, field_name)
            normalized = sorted(
                {" ".join(str(item).casefold().split()) for item in values if str(item).strip()}
            )
            if (
                field_name
                in {
                    "layout_topology",
                    "token_relationships",
                    "typography_roles",
                    "distinctive_moves",
                }
                and not normalized
            ):
                raise ValueError("design fingerprints require all core normalized dimensions")
            setattr(self, field_name, normalized)
        payload = self.model_dump(mode="json", exclude={"fingerprint_hash"})
        computed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.fingerprint_hash and self.fingerprint_hash != computed:
            raise ValueError("fingerprint_hash does not match the normalized design fingerprint")
        self.fingerprint_hash = computed
        return self


class ExperienceBlueprintV4(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-experience-blueprint-v4"] = (
        "code-generator-experience-blueprint-v4"
    )
    selected_concept_id: str
    narrative_arc: str
    tokens: DesignTokenSystemV4
    route_shells: list[RouteShellV4] = Field(min_length=1, max_length=32)
    section_regions: list[SectionRegionV4] = Field(
        min_length=1,
        max_length=256,
        validation_alias=AliasChoices("section_regions", "regions"),
        serialization_alias="section_regions",
    )
    distinctive_moves: list[DistinctiveMoveV4] = Field(min_length=1, max_length=64)
    interaction_assignments: list[InteractionAssignmentV4] = Field(
        default_factory=list,
        max_length=128,
        validation_alias=AliasChoices("interaction_assignments", "interactions"),
        serialization_alias="interaction_assignments",
    )
    resource_placements: list[ResourcePlacementV4] = Field(default_factory=list, max_length=256)
    motion_beats: list[MotionBeatV4] = Field(default_factory=list, max_length=128)
    anti_patterns: list[str] = Field(default_factory=list, max_length=24)

    @model_validator(mode="after")
    def _scope(self) -> ExperienceBlueprintV4:
        if not self.selected_concept_id.strip() or not self.narrative_arc.strip():
            raise ValueError("experience blueprints require a selected concept and narrative arc")
        routes = {item.route_id for item in self.route_shells}
        if len(routes) != len(self.route_shells):
            raise ValueError("route shell IDs must be unique")
        region_ids = {item.region_id for item in self.section_regions}
        if len(region_ids) != len(self.section_regions):
            raise ValueError("region IDs must be unique")
        move_ids = {item.move_id for item in self.distinctive_moves}
        if len(move_ids) != len(self.distinctive_moves):
            raise ValueError("distinctive move IDs must be unique")
        interaction_ids = [item.interaction_id for item in self.interaction_assignments]
        resource_ids = [item.resource_slot_id for item in self.resource_placements]
        motion_ids = [item.motion_id for item in self.motion_beats]
        if len(interaction_ids) != len(set(interaction_ids)):
            raise ValueError("interaction assignment IDs must be unique")
        if len(resource_ids) != len(set(resource_ids)):
            raise ValueError("resource placement slot IDs must be unique")
        if len(motion_ids) != len(set(motion_ids)):
            raise ValueError("motion beat IDs must be unique")
        if any(item.route_id not in routes for item in self.section_regions) or any(
            item.route_id not in routes for item in self.distinctive_moves
        ):
            raise ValueError("blueprint item references an unknown route")
        if (
            any(item.route_id not in routes for item in self.interaction_assignments)
            or any(item.route_id not in routes for item in self.resource_placements)
            or any(item.route_id not in routes for item in self.motion_beats)
        ):
            raise ValueError("blueprint assignment references an unknown route")
        if any(item.region_id not in region_ids for item in self.distinctive_moves):
            raise ValueError("distinctive move references an unknown region")
        if any(not item.thesis.strip() for item in self.distinctive_moves):
            raise ValueError("distinctive moves require content-specific theses")
        for route in self.route_shells:
            if not any(item.route_id == route.route_id for item in self.distinctive_moves):
                raise ValueError("every route needs at least one distinctive move")
        owners = [item.owner_id for item in self.section_regions]
        if len(owners) != len(set(owners)):
            raise ValueError("section owner IDs must be unique")
        return self

    @property
    def regions(self) -> list[SectionRegionV4]:
        """Internal compatibility spelling for the explicit section_regions field."""

        return self.section_regions

    @property
    def layout_regions(self) -> list[SectionRegionV4]:
        return self.section_regions

    @property
    def interactions(self) -> list[InteractionAssignmentV4]:
        """Internal compatibility spelling for interaction_assignments."""

        return self.interaction_assignments


class RegionRuntimeCheckV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region_id: str
    section_id: str
    section_selector: str
    region_selector: str
    order_mobile: int
    order_tablet: int
    order_desktop: int
    columns_mobile: int
    columns_tablet: int
    columns_desktop: int
    max_measure_ch: int
    gap: LengthTokenV4 = Field(
        default_factory=lambda: LengthTokenV4(name="gap", value=0, unit="px")
    )
    width_ratio_min: float
    width_ratio_max: float
    overlap_ratio_max: float
    sticky_allowed: bool


class DistinctiveMoveRuntimeCheckV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    move_id: str
    section_id: str
    source_selector: str
    target_selector: str
    relationship: str
    minimum_ratio: float
    maximum_ratio: float
    viewports: list[str]
    required_css_properties: list[str]


class ResourceRuntimeCheckV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_slot_id: str
    section_id: str
    element_selector: str
    loading: Literal["eager", "lazy"]
    aspect_ratio_min: float
    aspect_ratio_max: float
    minimum_visible_ratio: float
    require_srcset: bool = True
    require_dimensions: bool = True


class InteractionRuntimeCheckV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interaction_id: str
    target_selector: str
    outcome_selector: str
    trigger: str
    expected_navigation: str
    expected_state_attribute: str
    expected_state_value: str
    focus_behavior: str


class MotionRuntimeCheckV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motion_id: str
    target_selector: str
    trigger_selector: str
    trigger: str
    changed_properties: list[MotionPropertyExpectationV4]
    duration_min_ms: int
    duration_max_ms: int
    performance_budget_ms: int
    reduced_motion_replacement: str


class FontRuntimeCheckV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["body", "display"]
    selector: str
    family: str
    weights: list[int]
    local_files: list[str] = Field(min_length=1)


class DesignRealizationContract(BaseModel):
    """Executable, selector-bound runtime obligations compiled from v4 intent."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["design-realization-contract-v2"] = "design-realization-contract-v2"
    route_id: str
    section_order: list[str] = Field(min_length=1)
    region_checks: list[RegionRuntimeCheckV1] = Field(min_length=1)
    distinctive_move_checks: list[DistinctiveMoveRuntimeCheckV1] = Field(min_length=1)
    resource_checks: list[ResourceRuntimeCheckV1] = Field(default_factory=list)
    interaction_checks: list[InteractionRuntimeCheckV1] = Field(default_factory=list)
    motion_checks: list[MotionRuntimeCheckV1] = Field(default_factory=list)
    font_checks: list[FontRuntimeCheckV1] = Field(min_length=1, max_length=2)
    contract_hash: str = ""

    @model_validator(mode="after")
    def _stamp_hash(self) -> DesignRealizationContract:
        payload = self.model_dump(mode="json", exclude={"contract_hash"})
        computed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.contract_hash and self.contract_hash != computed:
            raise ValueError("contract_hash does not match the design realization contract")
        self.contract_hash = computed
        return self

    @property
    def signature_move_ids(self) -> list[str]:
        return [item.move_id for item in self.distinctive_move_checks]

    @property
    def region_ids(self) -> list[str]:
        return [item.region_id for item in self.region_checks]

    @property
    def motion_ids(self) -> list[str]:
        return [item.motion_id for item in self.motion_checks]

    @property
    def resource_slot_ids(self) -> list[str]:
        return [item.resource_slot_id for item in self.resource_checks]

    @property
    def interaction_ids(self) -> list[str]:
        return [item.interaction_id for item in self.interaction_checks]


class ResourceSearchIntentV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["resource-search-intent-v2"] = "resource-search-intent-v2"
    slot_id: str
    subject_terms: list[str] = Field(min_length=2, max_length=6)
    context_terms: list[str] = Field(
        default_factory=list,
        max_length=4,
        validation_alias=AliasChoices("context_terms", "contextual_modifiers"),
        serialization_alias="context_terms",
    )
    negative_concepts: list[str] = Field(default_factory=list, max_length=12)
    provider_filters: list[str] = Field(default_factory=list, max_length=8)
    orientation: Literal["landscape", "portrait", "square", "any"] = "any"
    minimum_width: int = Field(default=0, ge=0, le=10000)
    minimum_height: int = Field(default=0, ge=0, le=10000)
    category: str = ""
    colors: list[str] = Field(default_factory=list, max_length=4)
    alt_policy: Literal["decorative", "approved_text", "contextual_description"]
    crop_policy: Literal["cover", "contain", "natural"] = "cover"
    query_variants: list[str] = Field(default_factory=list, max_length=3)

    @field_validator("subject_terms", "context_terms", "negative_concepts", "provider_filters")
    @classmethod
    def _terms(cls, value: list[str]) -> list[str]:
        result = [" ".join(str(item).strip().split()) for item in value if str(item).strip()]
        if any(len(item) > 48 for item in result):
            raise ValueError("resource search terms are too long")
        return result

    @model_validator(mode="after")
    def _query_bounds(self) -> ResourceSearchIntentV2:
        variants = self.query_variants or [" ".join(self.subject_terms + self.context_terms)]
        if len(variants) > 3 or any(
            len(re.findall(r"[a-z0-9][a-z0-9-]*", variant.casefold())) not in range(2, 7)
            for variant in variants
        ):
            raise ValueError("resource search intents require two to six terms per variant")
        self.query_variants = [
            " ".join(dict.fromkeys(re.findall(r"[a-z0-9][a-z0-9-]*", variant.casefold())))
            for variant in variants
        ]
        return self

    @property
    def contextual_modifiers(self) -> list[str]:
        return self.context_terms


class FailureDetailV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    next_action: str


class SourceGenerationEnvelopeV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["source-generation-envelope-v2"] = "source-generation-envelope-v2"
    result: Literal["changes", "requests", "accepted", "cannot_complete"] = Field(
        validation_alias=AliasChoices("result", "result_tag"),
        serialization_alias="result_tag",
    )
    files: list[SourceFileChange] = Field(min_length=0)
    exported_signatures: list[ExportedSignature] = Field(min_length=0)
    content_ids: list[str] = Field(min_length=0)
    criterion_ids: list[str] = Field(min_length=0)
    resource_slot_ids: list[str] = Field(min_length=0)
    interaction_ids: list[str] = Field(min_length=0)
    resource_requests: list[ResourceRequest] = Field(min_length=0)
    dependency_requests: list[DependencyRequest] = Field(min_length=0)
    failure_details: list[FailureDetailV2] = Field(min_length=0)

    @model_validator(mode="after")
    def _matching_payload(self, info: ValidationInfo) -> SourceGenerationEnvelopeV2:
        if self.result == "changes" and not self.files:
            raise ValueError("changes result requires files")
        if self.result == "requests" and not (self.resource_requests or self.dependency_requests):
            raise ValueError("requests result requires resource or dependency requests")
        if self.result == "cannot_complete" and not self.failure_details:
            raise ValueError("cannot_complete result requires safe failure details")
        if self.result == "accepted" and self.files:
            raise ValueError("accepted result cannot include source files")
        context = info.context or {}
        if self.result == "accepted" and context.get("forbid_accepted_result"):
            # A model call is only allowed to report "accepted" (nothing to
            # change) when the operation legitimately reviews already-
            # generated content (integrate/repair). A first-time generation
            # operation (route_batch, route_compose, foundation) has nothing
            # of its own yet to accept; validation-context-gating this here
            # (rather than only in prose) means a live occurrence forces the
            # existing schema-correction retry with explicit feedback,
            # instead of silently reaching GENERATION_CHANGES_MISSING.
            raise ValueError(
                'result: "accepted" is not valid for this operation - it has no prior '
                'generated content of its own to accept. Return result: "changes" with the '
                "complete new file set instead."
            )
        return self

    @property
    def coverage(self) -> list[str]:
        """Read-only aggregate for legacy diagnostics, never used as typed evidence."""

        return [
            *self.content_ids,
            *self.criterion_ids,
            *self.resource_slot_ids,
            *self.interaction_ids,
        ]

    @property
    def result_tag(self) -> str:
        return self.result


class QualityFindingV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    severity: Literal["blocking", "advisory"]
    owner_work_unit_id: str
    code: str
    evidence: str
    requested_outcome: str


class QualityReviewReceiptV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["quality-review-receipt-v1"] = "quality-review-receipt-v1"
    source_hash: str
    plan_hash: str
    context_hash: str
    hierarchy_score: int = Field(
        ge=1,
        le=5,
        validation_alias=AliasChoices("hierarchy_score", "hierarchy"),
        serialization_alias="hierarchy_score",
    )
    composition_score: int = Field(
        ge=1,
        le=5,
        validation_alias=AliasChoices("composition_score", "composition"),
        serialization_alias="composition_score",
    )
    typography_score: int = Field(
        ge=1,
        le=5,
        validation_alias=AliasChoices("typography_score", "typography"),
        serialization_alias="typography_score",
    )
    resource_fit_score: int = Field(
        ge=1,
        le=5,
        validation_alias=AliasChoices("resource_fit_score", "resource_fit"),
        serialization_alias="resource_fit_score",
    )
    motion_score: int = Field(
        ge=1,
        le=5,
        validation_alias=AliasChoices("motion_score", "motion"),
        serialization_alias="motion_score",
    )
    findings: list[QualityFindingV1] = Field(default_factory=list)
    reviewer_receipt: str
    accepted: bool

    @model_validator(mode="after")
    def _acceptance(self) -> QualityReviewReceiptV1:
        if not all(
            value.strip()
            for value in (
                self.source_hash,
                self.plan_hash,
                self.context_hash,
                self.reviewer_receipt,
            )
        ):
            raise ValueError(
                "quality receipts must bind source, plan, context, and reviewer identity"
            )
        blocking = any(item.severity == "blocking" for item in self.findings)
        scores_ok = (
            min(
                self.hierarchy_score,
                self.composition_score,
                self.typography_score,
                self.resource_fit_score,
                self.motion_score,
            )
            >= 4
        )
        if self.accepted and not (scores_ok and not blocking):
            raise ValueError("accepted quality reviews require scores >=4 and no blocking findings")
        return self

    @property
    def hierarchy(self) -> int:
        return self.hierarchy_score

    @property
    def composition(self) -> int:
        return self.composition_score

    @property
    def typography(self) -> int:
        return self.typography_score

    @property
    def resource_fit(self) -> int:
        return self.resource_fit_score

    @property
    def motion(self) -> int:
        return self.motion_score


class QualityFindingV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    severity: Literal["blocking", "advisory"]
    owner_work_unit_id: str
    code: str
    file: str
    line: int = Field(ge=1)
    marker: str
    evidence: str
    requested_outcome: str

    @model_validator(mode="after")
    def _concrete_evidence(self) -> QualityFindingV2:
        if not all(
            value.strip()
            for value in (
                self.finding_id,
                self.owner_work_unit_id,
                self.code,
                self.file,
                self.marker,
                self.evidence,
                self.requested_outcome,
            )
        ):
            raise ValueError("quality findings require concrete source and owner evidence")
        return self


class QualityScoreEvidenceV1(BaseModel):
    """Concrete source evidence supporting one whole-site quality score."""

    model_config = ConfigDict(extra="forbid")

    dimension: Literal["hierarchy", "composition", "typography", "resource_fit", "motion"]
    score: int = Field(ge=1, le=5)
    owner_work_unit_id: str
    file: str
    line: int = Field(ge=1)
    marker: str
    evidence: str

    @model_validator(mode="after")
    def _concrete_evidence(self) -> QualityScoreEvidenceV1:
        if not all(
            value.strip()
            for value in (
                self.owner_work_unit_id,
                self.file,
                self.marker,
                self.evidence,
            )
        ):
            raise ValueError("every quality score requires concrete file and marker evidence")
        return self


class QualityReviewDraftV1(BaseModel):
    """Provider wire result. The model scores and reports; it never accepts source."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["quality-review-draft-v1"] = "quality-review-draft-v1"
    hierarchy_score: int = Field(ge=1, le=5)
    composition_score: int = Field(ge=1, le=5)
    typography_score: int = Field(ge=1, le=5)
    resource_fit_score: int = Field(ge=1, le=5)
    motion_score: int = Field(ge=1, le=5)
    score_evidence: list[QualityScoreEvidenceV1] = Field(min_length=5, max_length=5)
    findings: list[QualityFindingV2] = Field(default_factory=list, max_length=64)
    advisory_observations: list[str] = Field(default_factory=list, max_length=16)
    review_summary: str

    @model_validator(mode="after")
    def _score_evidence(self) -> QualityReviewDraftV1:
        scores = (
            self.hierarchy_score,
            self.composition_score,
            self.typography_score,
            self.resource_fit_score,
            self.motion_score,
        )
        expected_scores = {
            "hierarchy": self.hierarchy_score,
            "composition": self.composition_score,
            "typography": self.typography_score,
            "resource_fit": self.resource_fit_score,
            "motion": self.motion_score,
        }
        evidence_by_dimension = {item.dimension: item for item in self.score_evidence}
        if set(evidence_by_dimension) != set(expected_scores) or any(
            item.score != expected_scores[item.dimension] for item in self.score_evidence
        ):
            raise ValueError(
                "quality score evidence must cover each dimension with its exact score"
            )
        if min(scores) < 4 and not any(item.severity == "blocking" for item in self.findings):
            raise ValueError("every quality score below four requires a blocking finding")
        if not self.review_summary.strip():
            raise ValueError("quality review drafts require a concise review summary")
        return self


class QualityReviewReceiptV2(BaseModel):
    """Host-stamped final review identity bound to the complete accepted source."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["quality-review-receipt-v2"] = "quality-review-receipt-v2"
    source_manifest_hash: str
    plan_hash: str
    realization_hash: str
    review_context_hash: str
    response_id: str
    review_hash: str
    quality_gate_version: str
    hierarchy_score: int = Field(ge=1, le=5)
    composition_score: int = Field(ge=1, le=5)
    typography_score: int = Field(ge=1, le=5)
    resource_fit_score: int = Field(ge=1, le=5)
    motion_score: int = Field(ge=1, le=5)
    score_evidence: list[QualityScoreEvidenceV1] = Field(min_length=5, max_length=5)
    findings: list[QualityFindingV2] = Field(default_factory=list)
    advisory_observations: list[str] = Field(default_factory=list)
    accepted: bool
    receipt_hash: str = ""

    @model_validator(mode="after")
    def _host_acceptance_and_hash(self) -> QualityReviewReceiptV2:
        bound = (
            self.source_manifest_hash,
            self.plan_hash,
            self.realization_hash,
            self.review_context_hash,
            self.response_id,
            self.review_hash,
            self.quality_gate_version,
        )
        if not all(value.strip() for value in bound):
            raise ValueError("quality review receipts require every final hash binding")
        computed_acceptance = min(
            self.hierarchy_score,
            self.composition_score,
            self.typography_score,
            self.resource_fit_score,
            self.motion_score,
        ) >= 4 and not any(item.severity == "blocking" for item in self.findings)
        expected_scores = {
            "hierarchy": self.hierarchy_score,
            "composition": self.composition_score,
            "typography": self.typography_score,
            "resource_fit": self.resource_fit_score,
            "motion": self.motion_score,
        }
        evidence_by_dimension = {item.dimension: item for item in self.score_evidence}
        if set(evidence_by_dimension) != set(expected_scores) or any(
            item.score != expected_scores[item.dimension] for item in self.score_evidence
        ):
            raise ValueError("quality receipts require exact evidence for every score dimension")
        if self.accepted != computed_acceptance:
            raise ValueError("quality acceptance must be computed from scores and findings")
        payload = self.model_dump(mode="json", exclude={"receipt_hash"})
        computed_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.receipt_hash and self.receipt_hash != computed_hash:
            raise ValueError("receipt_hash does not match the quality review receipt")
        self.receipt_hash = computed_hash
        return self


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
    experience_blueprint: (
        ExperienceBlueprintV4 | ExperienceBlueprintV3 | ExperienceBlueprintV2 | None
    ) = None
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
    def validate_tagged_payload(self, info: ValidationInfo) -> GenerationResult:
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
        context = info.context or {}
        if self.mode == "accepted" and context.get("forbid_accepted_result"):
            # See SourceGenerationEnvelopeV2._matching_payload for why this is
            # validation-context-gated rather than prose-only.
            raise ValueError(
                'mode="accepted" is not valid for this operation - it has no prior generated '
                'content of its own to accept. Return mode="changes" with the complete new '
                "file set instead."
            )
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
    attempt: int = 1
    retry_class: str = ""
    duration_ms: float = Field(default=0.0, ge=0)
    cached_tokens: int = Field(default=0, ge=0)


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
    line: int = 0
    column: int = 0
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
    quality_review: QualityReviewReceiptV2 | QualityReviewReceiptV1 | None = None


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
    realization_contracts: list[DesignRealizationContract] = Field(default_factory=list)
    expected_route_paths: list[str] = Field(default_factory=list)
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
    line: int = 0
    column: int = 0
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
    realization_results: list[dict[str, Any]] = Field(default_factory=list)
    passed: bool


class RepairReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-repair-receipt-v1"] = "code-generator-repair-receipt-v1"
    generation_id: str
    diagnostic_fingerprints: list[str]
    # Empty means a legacy receipt created before repair budgets were grouped
    # by diagnostic gate. Consumers conservatively place those receipts in
    # the shared fallback bucket.
    repair_unit_id: str = ""
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
    route_paths: list[str] = Field(default_factory=list)
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
    previous_pointer_sha256: str = ""
    previous_pointer: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class PublicReadbackEntryV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    kind: Literal["root", "route", "javascript", "stylesheet", "image", "font"]
    status_code: int
    sha256: str = ""
    media_type: str = ""


class PublicReadbackReceiptV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["public-preview-readback-v1"] = "public-preview-readback-v1"
    promotion_id: str
    candidate_id: str
    build_hash: str
    public_origin: str
    entries: list[PublicReadbackEntryV1] = Field(min_length=1)
    checked_at: str
    receipt_hash: str = ""

    @model_validator(mode="after")
    def _stamp(self) -> PublicReadbackReceiptV1:
        if any(item.status_code < 200 or item.status_code >= 300 for item in self.entries):
            raise ValueError("public preview read-back requires successful responses")
        payload = self.model_dump(mode="json", exclude={"receipt_hash"})
        computed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.receipt_hash and self.receipt_hash != computed:
            raise ValueError("receipt_hash does not match public read-back evidence")
        self.receipt_hash = computed
        return self


class ActivePreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = ""
    host: str
    url: str
    candidate_id: str
    candidate_identity_hash: str
    build_hash: str
    receipt_key: str
    receipt_hash: str
    pointer_etag: str
    route_ids: list[str] = Field(default_factory=list)
    route_paths: list[str] = Field(default_factory=list)
    promoted_at: str
    public_readback: PublicReadbackReceiptV1 | None = None


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
        "queued",
        "building",
        "smoke_testing",
        "repairing",
        "preview_pending",
        "ready",
        "needs_attention",
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


class ExportReceipt(BaseModel):
    """Safe, evaluator-facing pointer to the immutable local export."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["not_started", "exported", "failed"] = "not_started"
    relative_path: str = ""
    folder: str = ""
    source_path: str = ""
    dist_path: str = ""
    metadata_path: str = ""
    report_path: str = ""
    exported_at: str = ""
    error_code: str = ""


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
    pipeline_contract_version: str = "code-generator-v4"
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
    design_variant: DesignVariantReceiptV1 | None = None
    design_fingerprint: DesignFingerprintV1 | None = None
    realization_contracts: list[DesignRealizationContract] = Field(default_factory=list)
    integration_review: dict[str, Any] | None = None
    quality_review: QualityReviewReceiptV2 | QualityReviewReceiptV1 | None = None
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
    export_receipt: ExportReceipt | None = None
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


# The provider-safe source envelope intentionally appears before the legacy
# internal source DTOs it adapts into. Resolve those annotations only after the
# complete module namespace exists.
SourceGenerationEnvelopeV2.model_rebuild()
