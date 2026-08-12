"""Visual Design Director agent domain schemas.

Only the OUTPUT contract is validated (envelope shape, not business content)
— mirrors Content Architect's exact philosophy. Input is a compact projection
of the CURRENT APPROVED Content Architect output, deliberately unvalidated.
No model-specific imports.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VisualDesignDirectorStatus(StrEnum):
    NOT_STARTED = "not_started"
    BUILD_RUNNING = "build_running"
    DESIGN_REVIEW = "design_review"
    APPROVED = "approved"
    NEEDS_ATTENTION = "needs_attention"


class VisualPlanMode(StrEnum):
    """Discriminates the shared output contract across the 3 internal stages."""

    VISUAL_LANGUAGE_ONLY = "VISUAL_LANGUAGE_ONLY"
    VISUAL_LANGUAGE_AND_PAGES = "VISUAL_LANGUAGE_AND_PAGES"
    PAGES_READY = "PAGES_READY"
    INTEGRATED = "INTEGRATED"


class AssetImportance(StrEnum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    OPTIONAL = "optional"


class AssetSourceStatus(StrEnum):
    APPROVED_EXISTING = "approved_existing"
    LOCAL_LIBRARY_CANDIDATE = "local_library_candidate"
    NEEDS_ACQUISITION = "needs_acquisition"
    OPTIONAL = "optional"
    UNAVAILABLE = "unavailable"


class AssetSourcePolicy(StrEnum):
    """Policy carried into the hidden Build Preparation acquisition stage.

    Visual Design Director records intent only; it never calls a provider.
    """

    APPROVED_USER_MEDIA = "approved_user_media"
    CURATED_LOCAL = "curated_local"
    GENERATED_LOCAL_VISUAL = "generated_local_visual"
    OPTIONAL_EXTERNAL_ACQUISITION = "optional_external_acquisition"


class PagePublicationStatus(StrEnum):
    """Whether a page's route has cleared Content Architect's own publication
    review. Deterministically stamped by agent.py from the known Content
    Architect route_plan — NEVER model-authored — so it can never go stale
    or contradict itself the way free-text narrative fields can. A route
    whose Content Architect publication_status is "blocked" can never reach
    this point at all (validators.py hard-rejects it), so only APPROVED and
    PENDING are ever legitimately stamped here.
    """

    APPROVED = "approved"
    PENDING = "pending"


# ── Input (compact approved Content Architect projection, deliberately
# unvalidated) ───────────────────────────────────────────────────────────


class VisualDesignDirectorIntake(BaseModel):
    """Compact projection of the CURRENT APPROVED Content Architect output.

    Content Architect's own output is already the privacy-safe projection of
    Discovery — VDD reads it as-is, never a second-hand reduction, and never
    touches Discovery's raw resume/document text. `visual_director_handoff`
    is Content Architect's real handoff field (content_hierarchy,
    density_guidance, storytelling_opportunities, available/unavailable
    media, diagram_opportunities, confidentiality_restrictions,
    must_preserve, mobile_shortenable, never_fabricate) — read as
    authoritative, not reinvented into separate fields here.
    """

    model_config = ConfigDict(extra="allow")

    content_architect_content_hash: str = ""
    content_architect_session_revision: int = 0
    presentation_mode: str = ""
    site_story_strategy: dict[str, Any] = Field(default_factory=dict)
    route_plan: list[dict[str, Any]] = Field(default_factory=list)
    page_content_packs: list[dict[str, Any]] = Field(default_factory=list)
    public_content_manifest: dict[str, Any] = Field(default_factory=dict)
    media_status: dict[str, Any] = Field(default_factory=dict)
    visual_director_handoff: dict[str, Any] = Field(default_factory=dict)
    privacy_and_confidentiality: list[str] = Field(default_factory=list)


class VisualDesignDirectorPreferences(BaseModel):
    """Optional user preferences. Any type of input is accepted — no validation."""

    model_config = ConfigDict(extra="allow")

    visual_tone: str = ""
    motion_preference: str = ""
    density_preference: str = ""
    accessibility_notes: str = ""


# ── Output: shared per-stage contract ───────────────────────────────────────


class SceneDirection(BaseModel):
    """One deliberate visual/interaction moment within a route.

    A section (from Content Architect) is not automatically one scene, and a
    long page is not one scene — a page may contain several. Stable IDs
    matter for downstream compilation but never become rigid template slots.
    """

    model_config = ConfigDict(extra="forbid")

    scene_id: str = ""
    route_id: str = ""
    narrative_goal: str = ""
    viewport_role: str = ""
    content_refs: list[str] = Field(default_factory=list)
    layout_intent: str = ""
    alignment_relationships: str = ""
    relative_proportions: str = ""
    layer_stack: str = ""
    background_intent: str = ""
    asset_requirements: list[str] = Field(default_factory=list)
    resource_candidates: list[str] = Field(default_factory=list)
    motion_intent: dict[str, Any] = Field(default_factory=dict)
    interaction_states: dict[str, Any] = Field(default_factory=dict)
    transition_in: str = ""
    transition_out: str = ""
    responsive_behavior: str = ""
    accessibility_intent: str = ""
    reduced_motion_behavior: str = ""
    performance_risk: str = ""
    failure_safe_static_state: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)


class AssetBrief(BaseModel):
    """Intent for one meaningful image/visual requirement — never a concrete
    file. The hidden Build Preparation stage resolves actual files; this agent
    supplies purpose/crop/treatment/fallback intent only.

    subject/mood/aspect_ratio_need/color_relationship/negative_concepts are
    semantic search intent for the external-acquisition source (only
    meaningful when source_policy is optional_external_acquisition or
    source_status is needs_acquisition). These fields let Build Preparation
    search without re-deriving intent from prose.
    """

    model_config = ConfigDict(extra="forbid")

    asset_id: str = ""
    purpose: str = ""
    content_ref: str = ""
    asset_type: str = ""
    source_status: AssetSourceStatus = AssetSourceStatus.UNAVAILABLE
    source_policy: AssetSourcePolicy = AssetSourcePolicy.CURATED_LOCAL
    importance: AssetImportance = AssetImportance.OPTIONAL
    orientation: str = ""
    focal_point: str = ""
    safe_crop_region: str = ""
    text_safe_region: str = ""
    composition_role: str = ""
    desktop_treatment: str = ""
    mobile_treatment: str = ""
    fit_intent: str = ""
    cropping_tolerance: str = ""
    visual_treatment: str = ""
    quality_requirement: str = ""
    fallback_strategy: str = ""
    decorative_vs_informative: str = ""
    alt_text_intent: str = ""
    attribution_requirement: str = ""
    subject: str = ""
    mood: str = ""
    aspect_ratio_need: str = ""
    color_relationship: str = ""
    negative_concepts: list[str] = Field(default_factory=list)


class ResourceCandidate(BaseModel):
    """A candidate/reference from the local resource catalogue.

    Adaptable, never mandatory — the future Code Generation Engine may use,
    adapt, combine, or ignore it. `resource_id` must always come from the
    catalogue shortlist actually given to the model call that selected it —
    validators.py hard-rejects any other value, so by the time this object
    is persisted, the reference has already been catalogue-verified.

    category/resource_library_version/lookup_status are deterministically
    stamped by agent.py AFTER validation succeeds — never model-authored —
    so a future Resource & Asset Packager can trust this provenance without
    re-deriving it from code behavior: lookup_status is always "verified"
    for any candidate that survived to persistence, and
    resource_library_version pins exactly which catalogue snapshot verified
    it, in case the catalogue itself changes later.
    """

    model_config = ConfigDict(extra="forbid")

    resource_id: str = ""
    category: str = ""
    why_it_matches: str = ""
    where_it_may_help: str = ""
    priority: str = ""
    possible_use: str = ""
    adaptation_notes: str = ""
    fallback: str = ""
    confidence: str = ""
    resource_library_version: str = ""
    lookup_status: str = ""


class PageVisualDirection(BaseModel):
    """Visual/experience direction for one route.

    `route_id` MUST echo a Content Architect route_id verbatim — Content
    Architect owns route topology; this agent never invents, drops, or
    renames a route.

    publication_status/compilable are deterministically stamped by agent.py
    from the known Content Architect route_plan — NEVER model-authored.
    This is the authoritative, structural signal a future Blueprint
    Compiler must gate on instead of trusting free-text narrative fields
    (user_summary, meta, compiler_handoff), which the model can otherwise
    describe inconsistently with what it actually produced. A page for a
    PENDING route may still carry full scene-level direction (mirrors
    Content Architect's own precedent that pending content still gets
    planned, just gated) — it is simply marked not yet compilable.
    """

    model_config = ConfigDict(extra="forbid")

    route_id: str = ""
    publication_status: PagePublicationStatus = PagePublicationStatus.APPROVED
    compilable: bool = True
    path: str = ""
    purpose: str = ""
    visitor_takeaway: str = ""
    first_impression: str = ""
    storyboard: str = ""
    section_rhythm: str = ""
    primary_emphasis: str = ""
    secondary_emphasis: str = ""
    background_evolution: str = ""
    main_evidence_moment: str = ""
    main_interaction_moment: str = ""
    closing_action: str = ""
    relationship_to_next_route: str = ""
    navigation_behavior: str = ""
    responsive_summary: str = ""
    scenes: list[SceneDirection] = Field(default_factory=list)
    asset_briefs: list[str] = Field(default_factory=list)
    resource_candidates: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class VisualDesignDirectorOutput(BaseModel):
    """Structured output shared by all three internal model calls (stages).

    `mode` discriminates which stage produced it; validators.py enforces
    per-stage required-field rules on top of this shared shape.
    `visual_language`/`shared_visual_systems`/`navigation_direction`/
    `motion_system`/`interaction_system`/`compiler_handoff` are deliberately
    free dicts — visual direction shape varies too much per project/page to
    force a rigid nested model. `pages`/`asset_briefs`/`resource_candidates`
    ARE structured, because downstream stages and a future compiler need
    stable IDs, not prose.
    """

    model_config = ConfigDict(extra="forbid")

    mode: VisualPlanMode
    pages_included: bool = False
    integration_needed: bool = False
    user_summary: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)
    source_refs: dict[str, Any] = Field(default_factory=dict)
    visual_language: dict[str, Any] = Field(default_factory=dict)
    shared_visual_systems: dict[str, Any] = Field(default_factory=dict)
    navigation_direction: dict[str, Any] = Field(default_factory=dict)
    motion_system: dict[str, Any] = Field(default_factory=dict)
    interaction_system: dict[str, Any] = Field(default_factory=dict)
    pages: list[PageVisualDirection] = Field(default_factory=list)
    asset_briefs: list[AssetBrief] = Field(default_factory=list)
    resource_candidates: list[ResourceCandidate] = Field(default_factory=list)
    accessibility_and_performance: dict[str, Any] = Field(default_factory=dict)
    must_preserve: list[str] = Field(default_factory=list)
    must_not_fabricate: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    compiler_handoff: dict[str, Any] = Field(default_factory=dict)
    memory_update: dict[str, Any] = Field(default_factory=dict)


# ── Persisted state ──────────────────────────────────────────────────────


class VisualDesignDirectorSourceRef(BaseModel):
    """Snapshot of the Content Architect result this run is grounded in.

    Used to detect and reject a stale source: if Content Architect is
    re-approved with different content after this snapshot was taken, any
    further Visual Design Director operation must be rejected until a fresh
    start.

    route_publication_hash is checked independently of
    content_architect_content_hash: Content Architect's own content hash is
    computed only from page_content_packs/public_content_manifest, NOT from
    route_plan's publication_status values — so a route flipping from
    pending to approved (or vice versa) with no other content change would
    otherwise go undetected. content_architect_visual_input_hash additionally
    covers every other Content Architect projection consumed by VDD (story
    strategy, route intent, media, handoff, privacy, and page packs). This
    closes those edge cases without touching Content Architect's own
    already-verified hash computation.
    """

    model_config = ConfigDict(extra="forbid")

    content_architect_content_hash: str = ""
    content_architect_visual_input_hash: str = ""
    content_architect_session_revision: int = 0
    route_publication_hash: str = ""
    snapshotted_at: str = ""


class VisualDesignDirectorApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved_at: str = ""
    visual_direction_hash: str = ""


class VisualDesignDirectorState(BaseModel):
    """Current Visual Design Director state, stored under
    portfolio_sessions.current_state['visual_design_director'].

    Flat: one authoritative copy of each direction field (no per-stage
    sub-buckets) since a single job (with up to 3 internal model calls) is
    the only writer.
    """

    model_config = ConfigDict(extra="forbid")

    status: VisualDesignDirectorStatus = VisualDesignDirectorStatus.NOT_STARTED
    model_profile: str = ""
    source_ref: VisualDesignDirectorSourceRef = Field(default_factory=VisualDesignDirectorSourceRef)
    intake: VisualDesignDirectorIntake = Field(default_factory=VisualDesignDirectorIntake)
    preferences: VisualDesignDirectorPreferences = Field(
        default_factory=VisualDesignDirectorPreferences
    )
    version: str = ""
    run_id: str = ""
    job_id: str = ""
    user_summary: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)
    source_refs: dict[str, Any] = Field(default_factory=dict)
    visual_language: dict[str, Any] = Field(default_factory=dict)
    shared_visual_systems: dict[str, Any] = Field(default_factory=dict)
    navigation_direction: dict[str, Any] = Field(default_factory=dict)
    motion_system: dict[str, Any] = Field(default_factory=dict)
    interaction_system: dict[str, Any] = Field(default_factory=dict)
    pages: list[PageVisualDirection] = Field(default_factory=list)
    asset_briefs: list[AssetBrief] = Field(default_factory=list)
    resource_candidates: list[ResourceCandidate] = Field(default_factory=list)
    accessibility_and_performance: dict[str, Any] = Field(default_factory=dict)
    must_preserve: list[str] = Field(default_factory=list)
    must_not_fabricate: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    compiler_handoff: dict[str, Any] = Field(default_factory=dict)
    stages_run: list[str] = Field(default_factory=list)
    memory: dict[str, Any] = Field(default_factory=dict)
    revision_request: str = ""
    approved: VisualDesignDirectorApproval | None = None
    latest_error: dict[str, Any] | None = None
    attempt: int = 0
    max_attempts: int = 3
    started_at: str | None = None
