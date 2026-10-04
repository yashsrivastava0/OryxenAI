"""Content Architect agent domain schemas.

Only the OUTPUT contract is validated (envelope shape, not business content).
Input is the approved Discovery dossier when available, with the legacy
profile/summary retained for older sessions, plus optional user preferences.
No model-specific imports.

The page content tree mirrors the one pinned portfolio template
(docs/HTML and CSS/index.html + styles.css) region for region, so the
downstream HTML step can place every field without guessing. Multi-theme
support is deliberately deferred until a second stylesheet exists.
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
    """Whether a claim has cleared review to appear in public page content.

    PENDING claims must never be reachable from a populated page field.
    BLOCKED claims must never be referenced from public output at all — this
    is enforced structurally in validators.py, not left to prompt discipline
    alone, because a real model can still slip and needs a hard backstop.
    """

    APPROVED = "approved"
    PENDING = "pending"
    BLOCKED = "blocked"


class DecisionBasis(StrEnum):
    """Provenance of a major content-strategy decision (audience, primary CTA,
    tone, ...) so downstream stages know what may be preserved automatically
    versus what remains open to revision.
    """

    USER_CONFIRMED = "user_confirmed"
    SOURCE_DERIVED = "source_derived"
    SAFE_DEFAULT = "safe_default"


class CoverageDisposition(StrEnum):
    """What happened to one Discovery fact/entity on the way to the page."""

    USED = "used"
    CONDENSED = "condensed"
    RETAINED_INTERNALLY = "retained_internally"
    EXCLUDED_BY_RESTRICTION = "excluded_by_restriction"
    EXCLUDED_EDITORIALLY = "excluded_editorially"
    UNRESOLVED = "unresolved"


# ── Input (approved Discovery snapshot) ────────────────────────────────────


class ContentArchitectIntake(BaseModel):
    """Approved Discovery facts, including the complete dossier when present.

    The raw pasted text and free-form brief stay upstream. The dossier carries
    the full fact/entity inventory, restrictions, source references, question
    history, and open items that a compact profile cannot represent. Older
    approved sessions without a dossier retain the legacy profile fallback.
    """

    model_config = ConfigDict(extra="allow")

    approved_brief_title: str = ""
    user_summary: str = ""
    profile: dict[str, Any] = Field(default_factory=dict)
    dossier: dict[str, Any] = Field(default_factory=dict)
    open_items: list[str] = Field(default_factory=list)
    discovery_brief_hash: str = ""
    discovery_session_revision: int = 0
    selected_theme_id: str = ""
    allow_illustrative_work: bool = False


class ContentArchitectPreferences(BaseModel):
    """Optional user preferences. Any type of input is accepted — no validation."""

    model_config = ConfigDict(extra="allow")

    goal: str = ""
    audience: str = ""
    tone: str = ""
    density: str = ""


# ── Output: the single page, region by region ───────────────────────────────
# Stray keys from a model are dropped (extra="ignore") rather than failing a
# finished run; internal-review key leakage is still rejected in validators.py.


class HeroContent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = ""
    eyebrow_primary: str = ""
    eyebrow_secondary: str = ""
    headline_prefix: str = ""
    headline_emphasis: str = ""
    intro: str = ""
    location: str = ""
    primary_cta_label: str = ""
    secondary_cta_label: str = ""


class PageMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = ""
    description: str = ""


class SystemsPracticePillar(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = ""
    description: str = ""


class SystemsPracticeContent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    eyebrow: str = ""
    heading: str = ""
    intro: str = ""
    pillars: list[SystemsPracticePillar] = Field(default_factory=list)


class CapabilityGroup(BaseModel):
    model_config = ConfigDict(extra="ignore")

    heading: str = ""
    items: list[str] = Field(default_factory=list)


class TechnicalCapabilitiesContent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    eyebrow: str = ""
    heading: str = ""
    intro: str = ""
    groups: list[CapabilityGroup] = Field(default_factory=list)


class ProfessionalContextContent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    eyebrow: str = ""
    heading: str = ""
    intro: str = ""
    organizations: list[str] = Field(default_factory=list)


class ConnectDestination(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str = ""
    url: str = ""
    featured: bool = False


class ConnectContent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    eyebrow: str = ""
    heading: str = ""
    intro: str = ""
    destinations: list[ConnectDestination] = Field(default_factory=list)


class AtlasExperience(BaseModel):
    role: str = ""
    organization: str = ""
    dates: str = ""
    description: str = ""


class AtlasEducation(BaseModel):
    credential: str = ""
    institution: str = ""
    dates: str = ""


class AtlasStatistic(BaseModel):
    value: str = ""
    label: str = ""


class AtlasProject(BaseModel):
    kind: str = "real"
    title: str = ""
    summary: str = ""
    role: str = ""
    period: str = ""
    problem: str = ""
    approach: str = ""
    outcome: str = ""
    external_url: str = ""


class AtlasPages(BaseModel):
    about_heading: str = ""
    about_intro: str = ""
    about_quote: str = ""
    experience: list[AtlasExperience] = Field(default_factory=list)
    education: list[AtlasEducation] = Field(default_factory=list)
    statistics: list[AtlasStatistic] = Field(default_factory=list)
    projects: list[AtlasProject] = Field(default_factory=list)


class PortfolioPageContent(BaseModel):
    """Every visitor-facing string of the one pinned portfolio template."""

    model_config = ConfigDict(extra="ignore")

    hero: HeroContent = Field(default_factory=HeroContent)
    metadata: PageMetadata = Field(default_factory=PageMetadata)
    marquee_keywords: list[str] = Field(default_factory=list)
    systems_practice: SystemsPracticeContent = Field(default_factory=SystemsPracticeContent)
    technical_capabilities: TechnicalCapabilitiesContent = Field(
        default_factory=TechnicalCapabilitiesContent
    )
    professional_context: ProfessionalContextContent = Field(
        default_factory=ProfessionalContextContent
    )
    connect: ConnectContent = Field(default_factory=ConnectContent)
    atlas: AtlasPages = Field(default_factory=AtlasPages)


class ContentStoryStrategy(BaseModel):
    """Editorial reasoning behind the page. Never rendered publicly."""

    model_config = ConfigDict(extra="ignore")

    positioning: str = ""
    value_proposition: str = ""
    primary_audience: str = ""
    secondary_audience: str = ""
    primary_action: str = ""
    narrative_thesis: str = ""
    leading_evidence: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    content_risks: list[str] = Field(default_factory=list)
    tone: str = ""
    content_density: str = ""


class ClaimGrounding(BaseModel):
    """Provenance metadata for one important claim.

    evidence_status, ownership, and publication_status are three independent
    questions — a claim can be well-evidenced (evidence_status=verified) but
    still not individually owned (ownership=team) and still not yet cleared
    for publication (publication_status=pending). Collapsing these into one
    field is how "team_outcome" ended up living inside evidence_status in an
    earlier version of this schema; keep them separate.

    `field_paths` lists the page fields whose copy relies on this claim, using
    the dotted/bracket syntax of page_content.resolve_field_path, e.g.
    "hero.headline_emphasis" or "systems_practice.pillars[0].description".
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
    field_paths: list[str] = Field(default_factory=list)


class DecisionRecord(BaseModel):
    """Provenance for one major content-strategy decision."""

    model_config = ConfigDict(extra="forbid")

    decision: str = ""
    value: str = ""
    basis: DecisionBasis = DecisionBasis.SAFE_DEFAULT
    confidence: str = ""
    rationale: str = ""


class ContentCoverageEntry(BaseModel):
    """Editorial disposition of one source-linked Discovery fact or entity.

    `disposition` stays a plain string (values: CoverageDisposition) so rows
    persisted before the six-way taxonomy still load; agent.py validates it.
    """

    model_config = ConfigDict(extra="ignore")

    source_id: str = ""
    disposition: str = ""
    field_paths: list[str] = Field(default_factory=list)
    reason: str = ""


class ContentArchitectOutput(BaseModel):
    """Structured output shared by the three internal model operations.

    `mode` discriminates which operation produced it; validators.py enforces
    operation-specific required-field rules on top of this shared shape.
    """

    model_config = ConfigDict(extra="forbid")

    mode: ContentPlanMode
    content_included: bool = False
    integration_needed: bool = False
    user_summary: str = ""
    site_story_strategy: ContentStoryStrategy = Field(default_factory=ContentStoryStrategy)
    decision_basis: list[DecisionRecord] = Field(default_factory=list)
    page_content: PortfolioPageContent = Field(default_factory=PortfolioPageContent)
    claim_grounding: list[ClaimGrounding] = Field(default_factory=list)
    coverage_ledger: list[ContentCoverageEntry] = Field(default_factory=list)
    internal_notes: dict[str, Any] = Field(default_factory=dict)
    omissions: list[str] = Field(default_factory=list)
    unresolved_issues: list[str] = Field(default_factory=list)
    privacy_and_confidentiality: list[str] = Field(default_factory=list)
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

    # Ignore fields from older persisted output contracts. The response model
    # above remains strict, so new model results cannot reintroduce removed
    # fields while historical JSONB rows continue to load safely.
    model_config = ConfigDict(extra="ignore")

    status: ContentArchitectStatus = ContentArchitectStatus.NOT_STARTED
    model_profile: str = ""
    routing_policy_version: str = ""
    routing_policy_fingerprint: str = ""
    source_ref: ContentArchitectSourceRef = Field(default_factory=ContentArchitectSourceRef)
    intake: ContentArchitectIntake = Field(default_factory=ContentArchitectIntake)
    preferences: ContentArchitectPreferences = Field(default_factory=ContentArchitectPreferences)
    version: str = ""
    run_id: str = ""
    job_id: str = ""
    user_summary: str = ""
    site_story_strategy: ContentStoryStrategy = Field(default_factory=ContentStoryStrategy)
    decision_basis: list[DecisionRecord] = Field(default_factory=list)
    page_content: PortfolioPageContent = Field(default_factory=PortfolioPageContent)
    claim_grounding: list[ClaimGrounding] = Field(default_factory=list)
    coverage_ledger: list[ContentCoverageEntry] = Field(default_factory=list)
    internal_notes: dict[str, Any] = Field(default_factory=dict)
    omissions: list[str] = Field(default_factory=list)
    unresolved_issues: list[str] = Field(default_factory=list)
    privacy_and_confidentiality: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    stages_run: list[str] = Field(default_factory=list)
    memory: dict[str, Any] = Field(default_factory=dict)
    revision_request: str = ""
    approved: ContentArchitectApproval | None = None
    latest_error: dict[str, Any] | None = None
    attempt: int = 0
    max_attempts: int = 3
    started_at: str | None = None
