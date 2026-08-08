"""Content Architect agent domain schemas.

Only the OUTPUT contract is validated (envelope shape, not business content).
Input is a compact APPROVED Discovery snapshot — never the raw resume, never
the full Discovery brief markdown, never document text — plus optional user
preferences. No model-specific imports.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ContentArchitectStatus(StrEnum):
    NOT_STARTED = "not_started"
    BUILD_RUNNING = "build_running"
    CONTENT_REVIEW = "content_review"
    APPROVED = "approved"
    NEEDS_ATTENTION = "needs_attention"


class ContentPlanMode(StrEnum):
    """Discriminates the shared output contract across the 3 internal stages."""

    STRATEGY_ONLY = "STRATEGY_ONLY"
    STRATEGY_AND_CONTENT = "STRATEGY_AND_CONTENT"
    PAGES_READY = "PAGES_READY"
    INTEGRATED = "INTEGRATED"


class PresentationMode(StrEnum):
    SINGLE_PAGE = "single_page"
    HYBRID = "hybrid"
    MULTI_PAGE = "multi_page"


class EvidenceStatus(StrEnum):
    """Whether a claim's factual content is backed by the source — evidence
    strength ONLY. Who it belongs to is a separate question; see Ownership.
    """

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    UNRESOLVED = "unresolved"


class Ownership(StrEnum):
    INDIVIDUAL = "individual"
    TEAM = "team"
    UNCLEAR = "unclear"


class PublicationStatus(StrEnum):
    """Whether a route or claim has cleared review to appear in public output.

    PENDING material must never enter page_content_packs/public_content_manifest.
    BLOCKED material must never be referenced from public output at all — this
    is enforced structurally in validators.py, not left to prompt discipline
    alone, because a real model can still slip and needs a hard backstop.
    """

    APPROVED = "approved"
    PENDING = "pending"
    BLOCKED = "blocked"


class DecisionBasis(StrEnum):
    """Provenance of a major site-strategy decision (audience, presentation
    mode, primary CTA, ...) so downstream stages know what may be preserved
    automatically versus what remains open to revision.
    """

    USER_CONFIRMED = "user_confirmed"
    SOURCE_DERIVED = "source_derived"
    SAFE_DEFAULT = "safe_default"


# ── Input (compact approved snapshot, deliberately unvalidated) ────────────


class ContentArchitectIntake(BaseModel):
    """Compact approved Discovery snapshot.

    Deliberately excludes the raw resume/document text AND the full Discovery
    brief markdown — grounding relies on the structured `profile` (facts) and
    the short `user_summary`, the same compact facts Discovery itself already
    extracted. Re-sending the full prose brief on every model call (including
    every revision) duplicates information already captured in `profile`,
    inflates latency/cost, and risks later stages reading stale Discovery
    prose instead of this agent's own finalized output. The Discovery source
    remains fully traceable via `discovery_brief_hash`/`discovery_session_revision`.
    """

    model_config = ConfigDict(extra="allow")

    approved_brief_title: str = ""
    user_summary: str = ""
    profile: dict[str, Any] = Field(default_factory=dict)
    open_items: list[str] = Field(default_factory=list)
    discovery_brief_hash: str = ""
    discovery_session_revision: int = 0


class ContentArchitectPreferences(BaseModel):
    """Optional user preferences. Any type of input is accepted — no validation."""

    model_config = ConfigDict(extra="allow")

    goal: str = ""
    audience: str = ""
    tone: str = ""
    density: str = ""


# ── Output: shared per-stage contract ───────────────────────────────────────


class RoutePlanEntry(BaseModel):
    """One route/page in the site architecture. Stable IDs matter downstream."""

    model_config = ConfigDict(extra="forbid")

    route_id: str = ""
    path: str = ""
    title: str = ""
    purpose: str = ""
    audience_takeaway: str = ""
    priority: str = ""
    content_density: str = ""
    section_sequence: list[str] = Field(default_factory=list)
    mobile_notes: str = ""
    source_refs: list[str] = Field(default_factory=list)
    publication_status: PublicationStatus = PublicationStatus.APPROVED


class ClaimGrounding(BaseModel):
    """Provenance metadata for one important claim.

    evidence_status, ownership, and publication_status are three independent
    questions — a claim can be well-evidenced (evidence_status=verified) but
    still not individually owned (ownership=team) and still not yet cleared
    for publication (publication_status=pending). Collapsing these into one
    field is how "team_outcome" ended up living inside evidence_status in an
    earlier version of this schema; keep them separate.
    """

    model_config = ConfigDict(extra="forbid")

    claim_id: str = ""
    statement: str = ""
    source_reference: str = ""
    source_entity_id: str = ""
    evidence_status: EvidenceStatus = EvidenceStatus.UNRESOLVED
    ownership: Ownership = Ownership.UNCLEAR
    publication_status: PublicationStatus = PublicationStatus.PENDING
    confidence_or_warning: str = ""


class ContentSection(BaseModel):
    """One machine-addressable section within a page's content pack.

    The section CONTAINER is structured (stable ID, purpose, which claims it
    relies on, priority/optionality, mobile handling, outgoing links) so the
    Visual Design Director, revisions, and the Code Generation Engine have an
    unambiguous page structure to work from. The section's own `content` stays
    a flexible dict — content shape varies too much per section type to force
    one rigid template, same reasoning as Discovery keeping brief_markdown
    free text instead of a rigid schema.
    """

    model_config = ConfigDict(extra="forbid")

    section_id: str = ""
    purpose: str = ""
    content: dict[str, Any] = Field(default_factory=dict)
    claim_ids: list[str] = Field(default_factory=list)
    priority: str = ""
    optional: bool = False
    mobile_condensation: str = ""
    link_targets: list[dict[str, Any]] = Field(default_factory=list)


class PageContentPack(BaseModel):
    """Final content for one route, as normalized sections.

    `internal_notes` is the ONLY place review/QA annotations may live (status
    caveats, "needs confirmation" notes, publication checklists). Visitors
    only ever see `sections` — internal_notes must never be duplicated inside
    a section's `content`; validators.py checks for common internal-note key
    names leaking into content as a structural backstop.
    """

    model_config = ConfigDict(extra="forbid")

    route_id: str = ""
    sections: list[ContentSection] = Field(default_factory=list)
    internal_notes: dict[str, Any] = Field(default_factory=dict)


class DecisionRecord(BaseModel):
    """Provenance for one major site-strategy decision."""

    model_config = ConfigDict(extra="forbid")

    decision: str = ""
    value: str = ""
    basis: DecisionBasis = DecisionBasis.SAFE_DEFAULT
    confidence: str = ""
    rationale: str = ""


class ContentArchitectOutput(BaseModel):
    """Structured output shared by all three internal model calls (stages).

    `mode` discriminates which stage produced it; validators.py enforces
    per-stage required-field rules on top of this shared shape. `site_story_strategy`,
    `public_content_manifest`, and `media_status` are deliberately NOT
    force-fit into rigid nested models — content shape varies too much per
    project/page. `page_content_packs` and `claim_grounding`/`route_plan` ARE
    structured, because downstream stages need stable IDs and unambiguous
    page structure, not prose.
    """

    model_config = ConfigDict(extra="forbid")

    mode: ContentPlanMode
    content_included: bool = False
    integration_needed: bool = False
    user_summary: str = ""
    site_story_strategy: dict[str, Any] = Field(default_factory=dict)
    decision_basis: list[DecisionRecord] = Field(default_factory=list)
    route_plan: list[RoutePlanEntry] = Field(default_factory=list)
    claim_grounding: list[ClaimGrounding] = Field(default_factory=list)
    page_content_packs: list[PageContentPack] = Field(default_factory=list)
    public_content_manifest: dict[str, Any] = Field(default_factory=dict)
    omissions: list[str] = Field(default_factory=list)
    unresolved_issues: list[str] = Field(default_factory=list)
    privacy_and_confidentiality: list[str] = Field(default_factory=list)
    media_status: dict[str, Any] = Field(default_factory=dict)
    visual_director_handoff: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    memory_update: dict[str, Any] = Field(default_factory=dict)


# ── Persisted state ──────────────────────────────────────────────────────


class ContentArchitectSourceRef(BaseModel):
    """Snapshot of the Discovery result this Content Architect run is grounded in.

    Used to detect and reject a stale source: if Discovery is re-approved
    with different content after this snapshot was taken, any further
    Content Architect operation must be rejected until a fresh start.
    """

    model_config = ConfigDict(extra="forbid")

    discovery_brief_hash: str = ""
    discovery_session_revision: int = 0
    snapshotted_at: str = ""


class ContentArchitectApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved_at: str = ""
    content_hash: str = ""


class ContentArchitectState(BaseModel):
    """Current Content Architect state, stored under
    portfolio_sessions.current_state['content_architect'].

    Flat: one authoritative copy of each content field (no per-stage
    sub-buckets) since a single job (with up to 3 internal model calls)
    is the only writer.
    """

    model_config = ConfigDict(extra="forbid")

    status: ContentArchitectStatus = ContentArchitectStatus.NOT_STARTED
    model_profile: str = ""
    source_ref: ContentArchitectSourceRef = Field(default_factory=ContentArchitectSourceRef)
    intake: ContentArchitectIntake = Field(default_factory=ContentArchitectIntake)
    preferences: ContentArchitectPreferences = Field(default_factory=ContentArchitectPreferences)
    version: str = ""
    run_id: str = ""
    job_id: str = ""
    user_summary: str = ""
    site_story_strategy: dict[str, Any] = Field(default_factory=dict)
    decision_basis: list[DecisionRecord] = Field(default_factory=list)
    route_plan: list[RoutePlanEntry] = Field(default_factory=list)
    page_content_packs: list[PageContentPack] = Field(default_factory=list)
    public_content_manifest: dict[str, Any] = Field(default_factory=dict)
    claim_grounding: list[ClaimGrounding] = Field(default_factory=list)
    omissions: list[str] = Field(default_factory=list)
    unresolved_issues: list[str] = Field(default_factory=list)
    privacy_and_confidentiality: list[str] = Field(default_factory=list)
    media_status: dict[str, Any] = Field(default_factory=dict)
    visual_director_handoff: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    stages_run: list[str] = Field(default_factory=list)
    memory: dict[str, Any] = Field(default_factory=dict)
    revision_request: str = ""
    approved: ContentArchitectApproval | None = None
    latest_error: dict[str, Any] | None = None
    attempt: int = 0
    max_attempts: int = 3
    started_at: str | None = None
