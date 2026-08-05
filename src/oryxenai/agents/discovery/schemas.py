"""Discovery agent domain schemas.

All schemas use extra="forbid" for strict validation. Types use bounded
strings and lists where appropriate. No model-specific imports.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

# ── Enums ────────────────────────────────────────────────────────────────────


class ResumeSource(StrEnum):
    NONE = "none"
    PASTED_TEXT = "pasted_text"
    EXTRACTED_PDF_TEXT = "extracted_pdf_text"
    EMPTY_EXTRACTION = "empty_extraction"
    SCANNED_PDF_SUSPECTED = "scanned_pdf_suspected"
    CORRUPT_PDF = "corrupt_pdf"
    PASSWORD_PROTECTED_PDF = "password_protected_pdf"  # noqa: S105
    TRUNCATED_TEXT = "truncated_text"


class LinkKind(StrEnum):
    GITHUB = "github"
    LINKEDIN = "linkedin"
    PROJECT = "project"
    PRODUCT = "product"
    ARTICLE = "article"
    PORTFOLIO = "portfolio"
    RESUME = "resume"
    OTHER = "other"


class SourceKind(StrEnum):
    MAIN_PROMPT = "main_prompt"
    RESUME_TEXT = "resume_text"
    PASTED_RESUME = "pasted_resume"
    USER_ANSWER = "user_answer"
    USER_EDIT = "user_edit"
    SYSTEM_DEFAULT = "system_default"


class FactStatus(StrEnum):
    SUPPORTED = "supported"
    AMBIGUOUS = "ambiguous"
    CONFLICTING = "conflicting"
    USER_ASSERTED = "user_asserted"
    OMITTED = "omitted"


class FactSensitivity(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"


class FactCategory(StrEnum):
    IDENTITY = "identity"
    CONTACT = "contact"
    TARGET_ROLE = "target_role"
    EXPERIENCE = "experience"
    PROJECT = "project"
    EDUCATION = "education"
    SKILL = "skill"
    CERTIFICATION = "certification"
    AWARD = "award"
    PUBLICATION = "publication"
    METRIC = "metric"
    DATE = "date"
    LANGUAGE = "language"
    LOCATION = "location"
    PREFERENCE = "preference"
    CONFIDENTIALITY = "confidentiality"
    OTHER = "other"


class ConflictCategory(StrEnum):
    DATE = "date"
    TITLE = "title"
    ROLE = "role"
    METRIC = "metric"
    CONFIDENTIALITY = "confidentiality"
    LANGUAGE = "language"
    PROJECT_SCOPE = "project_scope"
    CONTRIBUTION = "contribution"
    OTHER = "other"


class ConflictSeverity(StrEnum):
    BLOCKING = "blocking"
    MATERIAL = "material"
    INFORMATIONAL = "informational"


class ConflictResolutionPolicy(StrEnum):
    ASK_USER = "ask_user"
    OMIT_UNTIL_RESOLVED = "omit_until_resolved"
    SAFE_NORMALIZATION = "safe_normalization"
    USER_CHOICE_ALREADY_AVAILABLE = "user_choice_already_available"


class QuestionKind(StrEnum):
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    SHORT_TEXT = "short_text"
    LONG_TEXT = "long_text"
    BOOLEAN = "boolean"


class QuestionCategory(StrEnum):
    TARGET_ROLE = "target_role"
    PORTFOLIO_GOAL = "portfolio_goal"
    AUDIENCE = "audience"
    PROJECT_SELECTION = "project_selection"
    PERSONAL_CONTRIBUTION = "personal_contribution"
    CONFIDENTIALITY = "confidentiality"
    EMPHASIS = "emphasis"
    OMISSION = "omission"
    CONTACT = "contact"
    PRESENTATION = "presentation"
    CONFLICT_RESOLUTION = "conflict_resolution"
    OTHER = "other"


class AnswerMode(StrEnum):
    ANSWERED = "answered"
    AUTO = "auto"
    SKIPPED = "skipped"


class AutoDecisionCategory(StrEnum):
    TONE = "tone"
    THEME = "theme"
    MOTION = "motion"
    PROJECT_ORDERING = "project_ordering"
    SECTION_EMPHASIS = "section_emphasis"
    CTA = "cta"
    VISUAL_INTENSITY = "visual_intensity"


class DiscoveryStatus(StrEnum):
    NOT_STARTED = "not_started"
    INPUT_READY = "input_ready"
    QUESTIONS_QUEUED = "questions_queued"
    QUESTIONS_RUNNING = "questions_running"
    QUESTIONS_READY = "questions_ready"
    ANSWERS_IN_PROGRESS = "answers_in_progress"
    ANSWERS_READY = "answers_ready"
    BRIEF_QUEUED = "brief_queued"
    BRIEF_RUNNING = "brief_running"
    BRIEF_REVIEW = "brief_review"
    APPROVED = "approved"
    NEEDS_ATTENTION = "needs_attention"


# ── Discovery Intake ─────────────────────────────────────────────────────────


class DiscoveryLink(BaseModel):
    """A user-provided link with metadata."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default="", max_length=64)
    url: HttpUrl
    label: str | None = Field(default=None, max_length=256)
    kind: LinkKind | None = None


class DiscoveryProductConstraints(BaseModel):
    """Constraints the Discovery agent must respect."""

    model_config = ConfigDict(extra="forbid")

    max_questions: int = 8
    max_featured_projects: int = 5
    supported_output_languages: list[str] = Field(default_factory=lambda: ["en"])


class DiscoveryIntake(BaseModel):
    """Input snapshot for Discovery."""

    model_config = ConfigDict(extra="forbid")

    main_prompt: str | None = Field(default=None, max_length=20000)
    resume_text: str | None = Field(default=None, max_length=200000)
    resume_source: ResumeSource = ResumeSource.NONE
    links: list[DiscoveryLink] = Field(default_factory=list, max_length=30)
    output_language: str = Field(default="en", max_length=10)
    product_constraints: DiscoveryProductConstraints = Field(
        default_factory=DiscoveryProductConstraints
    )
    source_revision: int = 0


# ── Provenance and Facts ─────────────────────────────────────────────────────


class EvidenceReference(BaseModel):
    """Provenance for a single supporting piece of evidence."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(default="", max_length=128)
    source_kind: SourceKind
    evidence_excerpt: str = Field(default="", max_length=2000)
    location_hint: str | None = Field(default=None, max_length=512)


class FactCandidate(BaseModel):
    """A grounded or inferred fact with provenance."""

    model_config = ConfigDict(extra="forbid")

    local_key: str = Field(default="", max_length=128)
    category: FactCategory
    field: str = Field(default="", max_length=128)
    value: Any = None
    normalized_value: Any | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list, max_length=20)
    status: FactStatus = FactStatus.SUPPORTED
    sensitivity: FactSensitivity = FactSensitivity.PUBLIC
    publish_default: bool = True


# ── Normalized Profile ───────────────────────────────────────────────────────


class IdentityEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=256)
    preferred_display_name: str | None = Field(default=None, max_length=256)
    pronouns: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, max_length=256)
    headline: str | None = Field(default=None, max_length=512)
    summary: str | None = Field(default=None, max_length=2000)
    fact_ids: list[str] = Field(default_factory=list, max_length=50)


class ContactMethod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(default="email", max_length=32)
    value: str = Field(default="", max_length=256)
    display_label: str | None = Field(default=None, max_length=128)
    is_public: bool = False
    fact_ids: list[str] = Field(default_factory=list, max_length=10)


class LocationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    city: str | None = Field(default=None, max_length=128)
    region: str | None = Field(default=None, max_length=128)
    country: str | None = Field(default=None, max_length=128)
    remote_preference: str | None = Field(default=None, max_length=64)
    fact_ids: list[str] = Field(default_factory=list, max_length=10)


class TargetRoleCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="", max_length=256)
    seniority: str | None = Field(default=None, max_length=64)
    domain: str | None = Field(default=None, max_length=128)
    is_primary: bool = False
    fact_ids: list[str] = Field(default_factory=list, max_length=10)


class ExperienceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization: str = Field(default="", max_length=256)
    title: str = Field(default="", max_length=256)
    start_date: str | None = Field(default=None, max_length=32)
    end_date: str | None = Field(default=None, max_length=32)
    is_current: bool = False
    location: str | None = Field(default=None, max_length=256)
    responsibilities: list[str] = Field(default_factory=list, max_length=40)
    outcomes: list[str] = Field(default_factory=list, max_length=20)
    technologies: list[str] = Field(default_factory=list, max_length=40)
    fact_ids: list[str] = Field(default_factory=list, max_length=30)


class ProjectEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="", max_length=256)
    description: str | None = Field(default=None, max_length=2000)
    scope: str | None = Field(default=None, max_length=1000)
    personal_contribution: str | None = Field(default=None, max_length=2000)
    team_contribution: str | None = Field(default=None, max_length=1000)
    technologies: list[str] = Field(default_factory=list, max_length=40)
    supported_outcomes: list[str] = Field(default_factory=list, max_length=20)
    supported_metrics: list[str] = Field(default_factory=list, max_length=20)
    public_links: list[str] = Field(default_factory=list, max_length=10)
    confidentiality_status: str | None = Field(default=None, max_length=32)
    is_featured: bool = False
    fact_ids: list[str] = Field(default_factory=list, max_length=30)


class EducationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution: str = Field(default="", max_length=256)
    degree: str | None = Field(default=None, max_length=256)
    field_of_study: str | None = Field(default=None, max_length=256)
    start_date: str | None = Field(default=None, max_length=32)
    end_date: str | None = Field(default=None, max_length=32)
    fact_ids: list[str] = Field(default_factory=list, max_length=10)


class SkillGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(default="", max_length=128)
    items: list[str] = Field(default_factory=list, max_length=100)
    proficiency: str | None = Field(default=None, max_length=32)
    fact_ids: list[str] = Field(default_factory=list, max_length=30)


class CertificationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="", max_length=256)
    issuer: str | None = Field(default=None, max_length=256)
    date_obtained: str | None = Field(default=None, max_length=32)
    expiration_date: str | None = Field(default=None, max_length=32)
    fact_ids: list[str] = Field(default_factory=list, max_length=10)


class AwardEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="", max_length=256)
    issuer: str | None = Field(default=None, max_length=256)
    date: str | None = Field(default=None, max_length=32)
    fact_ids: list[str] = Field(default_factory=list, max_length=10)


class PublicationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="", max_length=512)
    venue: str | None = Field(default=None, max_length=256)
    date: str | None = Field(default=None, max_length=32)
    url: str | None = Field(default=None, max_length=2048)
    fact_ids: list[str] = Field(default_factory=list, max_length=10)


class LanguageEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str = Field(default="", max_length=64)
    proficiency: str | None = Field(default=None, max_length=32)
    fact_ids: list[str] = Field(default_factory=list, max_length=5)


class PublicLinkEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(default="", max_length=2048)
    label: str | None = Field(default=None, max_length=256)
    kind: LinkKind | None = None
    fact_ids: list[str] = Field(default_factory=list, max_length=5)


class NormalizedProfessionalProfile(BaseModel):
    """Normalized profile built from source evidence only."""

    model_config = ConfigDict(extra="forbid")

    identity: IdentityEntry | None = None
    contact_methods: list[ContactMethod] = Field(default_factory=list, max_length=20)
    location: LocationEntry | None = None
    target_roles: list[TargetRoleCandidate] = Field(default_factory=list, max_length=10)
    experience_entries: list[ExperienceEntry] = Field(default_factory=list, max_length=40)
    projects: list[ProjectEntry] = Field(default_factory=list, max_length=30)
    education: list[EducationEntry] = Field(default_factory=list, max_length=10)
    skills: list[SkillGroup] = Field(default_factory=list, max_length=20)
    certifications: list[CertificationEntry] = Field(default_factory=list, max_length=20)
    awards: list[AwardEntry] = Field(default_factory=list, max_length=20)
    publications: list[PublicationEntry] = Field(default_factory=list, max_length=20)
    languages: list[LanguageEntry] = Field(default_factory=list, max_length=10)
    public_links: list[PublicLinkEntry] = Field(default_factory=list, max_length=30)
    additional_facts: list[str] = Field(default_factory=list, max_length=50)


# ── Conflicts ────────────────────────────────────────────────────────────────


class ConflictAlternative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any = None
    source: str = Field(default="", max_length=64)
    evidence_excerpt: str | None = Field(default=None, max_length=1000)


class DiscoveryConflict(BaseModel):
    """A detected material conflict between sources."""

    model_config = ConfigDict(extra="forbid")

    local_key: str = Field(default="", max_length=128)
    category: ConflictCategory
    field: str = Field(default="", max_length=128)
    alternatives: list[ConflictAlternative] = Field(default_factory=list, max_length=10)
    severity: ConflictSeverity = ConflictSeverity.MATERIAL
    resolution_policy: ConflictResolutionPolicy = ConflictResolutionPolicy.ASK_USER
    related_fact_keys: list[str] = Field(default_factory=list, max_length=20)
    user_visible_summary: str = Field(default="", max_length=500)


# ── Questions ────────────────────────────────────────────────────────────────


class QuestionOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default="", max_length=64)
    label: str = Field(default="", max_length=256)


class DiscoveryQuestion(BaseModel):
    """A question for the user during Discovery."""

    model_config = ConfigDict(extra="forbid")

    local_key: str = Field(default="", max_length=128)
    category: QuestionCategory
    text: str = Field(default="", max_length=1000)
    help_text: str | None = Field(default=None, max_length=500)
    kind: QuestionKind = QuestionKind.SINGLE_SELECT
    options: list[QuestionOption] = Field(default_factory=list, max_length=20)
    required: bool = False
    allows_skip: bool = True
    allows_auto: bool = False
    auto_answer: Any | None = None
    related_fact_keys: list[str] = Field(default_factory=list, max_length=20)
    resolves_conflict_keys: list[str] = Field(default_factory=list, max_length=10)
    priority: int = 0

    @field_validator("priority")
    @classmethod
    def _priority_in_range(cls, v: int) -> int:
        return max(0, min(v, 10))


class DiscoveryAnswer(BaseModel):
    """A user-provided answer to a Discovery question."""

    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(default="", max_length=128)
    mode: AnswerMode = AnswerMode.ANSWERED
    value: Any | None = None
    answer_revision: int = 0


# ── Auto Decisions ───────────────────────────────────────────────────────────


class AutoDecision(BaseModel):
    """A safe automatic presentation decision."""

    model_config = ConfigDict(extra="forbid")

    category: AutoDecisionCategory
    selected_value: Any = None
    explanation: str = Field(default="", max_length=500)
    basis_fact_ids: list[str] = Field(default_factory=list, max_length=20)


# ── Warnings and Omissions ───────────────────────────────────────────────────


class OmissionCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_key: str = Field(default="", max_length=128)
    reason: str = Field(default="", max_length=500)
    severity: ConflictSeverity = ConflictSeverity.INFORMATIONAL


class DiscoveryWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(default="", max_length=64)
    message: str = Field(default="", max_length=500)
    details: dict[str, Any] = Field(default_factory=dict)


# ── Call A: Analysis Result ──────────────────────────────────────────────────


class DiscoveryAnalysisResult(BaseModel):
    """Output from Discovery Call A — analyze and prepare questions."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    detected_languages: list[str] = Field(default_factory=list, max_length=10)
    normalized_profile: NormalizedProfessionalProfile = Field(
        default_factory=NormalizedProfessionalProfile
    )
    fact_candidates: list[FactCandidate] = Field(default_factory=list, max_length=500)
    conflicts: list[DiscoveryConflict] = Field(default_factory=list, max_length=50)
    questions: list[DiscoveryQuestion] = Field(default_factory=list, max_length=10)
    auto_decisions: list[AutoDecision] = Field(default_factory=list, max_length=20)
    omission_candidates: list[OmissionCandidate] = Field(default_factory=list, max_length=100)
    input_warnings: list[DiscoveryWarning] = Field(default_factory=list, max_length=20)


# ── Call B: Strategic Brief ──────────────────────────────────────────────────


class BriefRole(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="", max_length=256)
    seniority: str | None = Field(default=None, max_length=64)
    domain: str | None = Field(default=None, max_length=128)
    fact_ids: list[str] = Field(default_factory=list, max_length=10)


class FeaturedProjectSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(default="", max_length=128)
    title: str = Field(default="", max_length=256)
    selection_reason: str = Field(default="", max_length=500)
    fact_ids: list[str] = Field(default_factory=list, max_length=10)


class BriefEmphasis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area: str = Field(default="", max_length=128)
    description: str = Field(default="", max_length=500)
    fact_ids: list[str] = Field(default_factory=list, max_length=10)


class BriefOmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area: str = Field(default="", max_length=128)
    reason: str = Field(default="", max_length=500)
    fact_ids: list[str] = Field(default_factory=list, max_length=10)


class PresentationPreference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    choice: str = Field(default="", max_length=128)
    rationale: str = Field(default="", max_length=500)
    source: str = Field(default="auto", max_length=32)


class ContactChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str = Field(default="", max_length=64)
    value: str = Field(default="", max_length=256)
    is_public: bool = False
    fact_ids: list[str] = Field(default_factory=list, max_length=5)


class ConfidentialityRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: str = Field(default="", max_length=256)
    rule: str = Field(default="", max_length=500)
    applies_to: list[str] = Field(default_factory=list, max_length=20)
    fact_ids: list[str] = Field(default_factory=list, max_length=10)


class UnresolvedConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conflict_key: str = Field(default="", max_length=128)
    summary: str = Field(default="", max_length=500)
    severity: ConflictSeverity = ConflictSeverity.MATERIAL


class DiscoveryBrief(BaseModel):
    """Output from Discovery Call B — strategic portfolio brief."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    target_role: BriefRole = Field(default_factory=BriefRole)
    secondary_strengths: list[str] = Field(default_factory=list, max_length=10)
    audience: list[str] = Field(default_factory=list, max_length=10)
    goal: str = Field(default="", max_length=1000)
    positioning: str = Field(default="", max_length=1000)
    featured_projects: list[FeaturedProjectSelection] = Field(default_factory=list, max_length=10)
    emphasize: list[BriefEmphasis] = Field(default_factory=list, max_length=20)
    omit: list[BriefOmission] = Field(default_factory=list, max_length=20)
    tone: PresentationPreference = Field(default_factory=PresentationPreference)
    theme_preference: PresentationPreference = Field(default_factory=PresentationPreference)
    motion_preference: PresentationPreference = Field(default_factory=PresentationPreference)
    primary_cta: str | None = Field(default=None, max_length=500)
    contact_choices: list[ContactChoice] = Field(default_factory=list, max_length=10)
    confidentiality_rules: list[ConfidentialityRule] = Field(default_factory=list, max_length=10)
    output_language: str = Field(default="en", max_length=10)
    downstream_fact_ids: list[str] = Field(default_factory=list, max_length=200)
    unresolved_conflicts: list[UnresolvedConflict] = Field(default_factory=list, max_length=20)
    warnings: list[DiscoveryWarning] = Field(default_factory=list, max_length=20)


# ── Approval ─────────────────────────────────────────────────────────────────


class DiscoveryApproval(BaseModel):
    """Immutable snapshot created when the user clicks Next."""

    model_config = ConfigDict(extra="forbid")

    approved_at: str = Field(default="")
    session_identity: str | None = Field(default=None, max_length=128)
    brief_version: int = 0
    brief_hash: str = Field(default="", max_length=128)
    source_revision: int = 0
    answer_revision: int = 0
    run_provenance: dict[str, Any] = Field(default_factory=dict)


class BriefEditRecord(BaseModel):
    """Audit record for an explicit user edit to the draft brief."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(default="", max_length=128)
    previous_value: Any = None
    new_value: Any = None
    edited_at: str = Field(default="", max_length=64)
    editor_identity: str | None = Field(default=None, max_length=128)
    provenance: str = Field(default="user_edit", max_length=32)


# ── Discovery State ──────────────────────────────────────────────────────────


class QuestionSetState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 0
    run_id: str | None = Field(default=None, max_length=64)
    job_id: str | None = Field(default=None, max_length=64)
    generated_from_source_revision: int = 0
    items: list[DiscoveryQuestion] = Field(default_factory=list)


class AnswersState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: int = 0
    question_version: int = 0
    items: dict[str, DiscoveryAnswer] = Field(default_factory=dict)


class BriefState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 0
    run_id: str | None = Field(default=None, max_length=64)
    job_id: str | None = Field(default=None, max_length=64)
    generated_from_source_revision: int | None = None
    generated_from_answer_revision: int | None = None
    draft: DiscoveryBrief | None = None
    approved: DiscoveryApproval | None = None
    approved_brief: DiscoveryBrief | None = None
    edit_history: list[BriefEditRecord] = Field(default_factory=list, max_length=100)


class DiscoveryState(BaseModel):
    """Current Discovery session state stored under portfolio_sessions.current_state['discovery']."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    status: DiscoveryStatus = DiscoveryStatus.NOT_STARTED
    source_revision: int = 0
    source_snapshot_id: str | None = Field(default=None, max_length=128)
    source_snapshot_hash: str | None = Field(default=None, max_length=128)
    questions: QuestionSetState = Field(default_factory=QuestionSetState)
    answers: AnswersState = Field(default_factory=AnswersState)
    brief: BriefState = Field(default_factory=BriefState)
    latest_error: DiscoveryWarning | None = None


# ── Run Provenance Records ───────────────────────────────────────────────────


class ModelRunMetadata(BaseModel):
    """Metadata recorded for every model call."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(default="", max_length=64)
    configured_model: str = Field(default="", max_length=128)
    resolved_model: str = Field(default="", max_length=128)
    provider_response_id: str | None = Field(default=None, max_length=256)
    latency_ms: float = 0.0
    prompt_version: str = Field(default="", max_length=32)
    attempt: int = 1
    status: str = Field(default="", max_length=32)
    safety_identifier: str | None = Field(default=None, max_length=128)
    usage: dict[str, Any] = Field(default_factory=dict)


# ── Model Request Context ────────────────────────────────────────────────────


class ModelRequestContext(BaseModel):
    """Context passed to a model call (no raw user data)."""

    model_config = ConfigDict(extra="forbid")

    operation: str = Field(default="", max_length=64)
    request_id: str = Field(default="", max_length=64)
    session_id: str = Field(default="", max_length=64)
    run_id: str = Field(default="", max_length=64)
    attempt: int = 1
    safety_identifier: str = Field(default="", max_length=128)


# ── Structured Model Result ──────────────────────────────────────────────────


class StructuredModelResult(BaseModel):
    """Normalized result from a structured model call."""

    model_config = ConfigDict(extra="forbid")

    parsed_output: dict[str, Any] = Field(default_factory=dict)
    response_id: str | None = Field(default=None, max_length=256)
    model: str = Field(default="", max_length=128)
    usage: dict[str, Any] = Field(default_factory=dict)
    finish_reason: str | None = Field(default=None, max_length=32)
    latency_ms: float = 0.0
