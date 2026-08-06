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
    NORMAL = "normal"


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


# ── v2 Analysis enums ────────────────────────────────────────────────────────


class SourceUsability(StrEnum):
    USABLE = "usable"
    USABLE_WITH_GAPS = "usable_with_gaps"
    SPARSE = "sparse"
    UNUSABLE = "unusable"


class ResumeStructureClarity(StrEnum):
    CLEAR = "clear"
    MOSTLY_CLEAR = "mostly_clear"
    UNCLEAR = "unclear"
    MISSING = "missing"


class CareerStage(StrEnum):
    STUDENT = "student"
    RECENT_GRADUATE = "recent_graduate"
    EARLY = "early"
    EARLY_MID = "early_mid"
    MID = "mid"
    MID_SENIOR = "mid_senior"
    SENIOR = "senior"
    EXECUTIVE = "executive"
    CAREER_CHANGER = "career_changer"
    RETURNING = "returning"
    UNKNOWN = "unknown"


class EvidenceDensity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class UncertaintyCategory(StrEnum):
    METRIC = "metric"
    PROJECT_CONTRIBUTION = "project_contribution"
    PROJECT_SCOPE = "project_scope"
    DATE = "date"
    IDENTITY = "identity"
    SENIORITY = "seniority"
    LEADERSHIP = "leadership"
    CONFIDENTIALITY = "confidentiality"
    OWNERSHIP = "ownership"
    LANGUAGE = "language"
    CONTACT = "contact"
    OTHER = "other"


class RecommendedAction(StrEnum):
    ASK_USER = "ask_user"
    OMIT = "omit"
    SAFE_NORMALIZE = "safe_normalize"
    NO_ACTION = "no_action"


class OmissionReason(StrEnum):
    UNSUPPORTED = "unsupported"
    UNCERTAIN = "uncertain"
    CONFIDENTIAL = "confidential"
    OFF_TOPIC = "off_topic"
    PRIVATE = "private"


class FactOrigin(StrEnum):
    """Distinction between fact types (Section 14.3)."""

    DIRECTLY_STATED = "directly_stated"
    NORMALIZED = "normalized"
    USER_ASSERTION = "user_assertion"
    PRESENTATION_PREFERENCE = "presentation_preference"
    MODEL_RECOMMENDATION = "model_recommendation"
    AMBIGUOUS_INFERENCE = "ambiguous_inference"
    UNSUPPORTED_INFERENCE = "unsupported_inference"
    CONFLICT = "conflict"


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ── v2 Brief enums ───────────────────────────────────────────────────────────


class PortfolioScope(StrEnum):
    SHORT = "short"
    STANDARD = "standard"
    EXTENDED = "extended"


class BriefReadiness(StrEnum):
    READY = "ready"
    READY_WITH_OMISSIONS = "ready_with_omissions"
    NEEDS_USER_INPUT = "needs_user_input"


class DecisionSource(StrEnum):
    USER_ANSWER = "user_answer"
    USER_EDIT = "user_edit"
    AUTO = "auto"
    GROUNDING_POLICY = "grounding_policy"
    MODEL_RECOMMENDATION = "model_recommendation"


class ContentDepth(StrEnum):
    BRIEF = "brief"
    BALANCED = "balanced"
    DEEP = "deep"


class ContactSource(StrEnum):
    EXPLICIT_USER_CHOICE = "explicit_user_choice"
    RESUME_DEFAULT = "resume_default"
    AUTO = "auto"


class UnresolvedSeverity(StrEnum):
    BLOCKING = "blocking"
    MATERIAL = "material"
    INFORMATIONAL = "informational"


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
    origin: FactOrigin = FactOrigin.DIRECTLY_STATED
    confidence: ConfidenceLevel | None = None


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
    why_it_matters: str | None = Field(default=None, max_length=500)

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
    reason_code: OmissionReason = OmissionReason.UNSUPPORTED
    severity: ConflictSeverity = ConflictSeverity.INFORMATIONAL


class DiscoveryWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(default="", max_length=64)
    message: str = Field(default="", max_length=500)
    details: dict[str, Any] = Field(default_factory=dict)


# ── Call A: Analysis Result (v2) ─────────────────────────────────────────────


class SourceAssessment(BaseModel):
    """Call A: usability assessment of the supplied sources."""

    model_config = ConfigDict(extra="forbid")

    overall_usability: SourceUsability = SourceUsability.USABLE_WITH_GAPS
    resume_structure: ResumeStructureClarity = ResumeStructureClarity.MOSTLY_CLEAR
    detected_languages: list[str] = Field(default_factory=list, max_length=10)
    requested_output_language: str = Field(default="en", max_length=10)
    compacted: bool = False
    duplicate_content_detected: bool = False
    prompt_injection_detected: bool = False
    warnings: list[DiscoveryWarning] = Field(default_factory=list, max_length=20)
    ignored_content: list[str] = Field(default_factory=list, max_length=50)


class PrimaryRoleCandidate(BaseModel):
    """Call A: candidate primary target role with supporting evidence."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(default="", max_length=256)
    supporting_fact_ids: list[str] = Field(default_factory=list, max_length=30)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class SecondaryCapabilityCandidate(BaseModel):
    """Call A: secondary capability the portfolio should keep visible."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(default="", max_length=256)
    supporting_fact_ids: list[str] = Field(default_factory=list, max_length=30)


class ProfileOverview(BaseModel):
    """Call A: analytical summary of the professional profile.

    ``professional_summary`` is an internal analytical summary for review
    and downstream orientation — it is never final About copy.
    """

    model_config = ConfigDict(extra="forbid")

    professional_summary: str = Field(default="", max_length=2000)
    career_stage: CareerStage = CareerStage.UNKNOWN
    primary_role_candidates: list[PrimaryRoleCandidate] = Field(default_factory=list, max_length=10)
    secondary_capability_candidates: list[SecondaryCapabilityCandidate] = Field(
        default_factory=list, max_length=20
    )
    evidence_density: EvidenceDensity = EvidenceDensity.MEDIUM


class Uncertainty(BaseModel):
    """Call A: an explicit uncertainty with a recommended action."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default="", max_length=128)
    category: UncertaintyCategory = UncertaintyCategory.OTHER
    summary: str = Field(default="", max_length=1000)
    related_fact_ids: list[str] = Field(default_factory=list, max_length=30)
    recommended_action: RecommendedAction = RecommendedAction.ASK_USER


class Readiness(BaseModel):
    """Call A: whether a brief can be built and what blocks it."""

    model_config = ConfigDict(extra="forbid")

    can_build_brief: bool = False
    recommended_question_count: int = 0
    blocking_conflict_ids: list[str] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=20)


class QualityChecksCallA(BaseModel):
    """Call A: deterministic quality self-checks."""

    model_config = ConfigDict(extra="forbid")

    all_supported_facts_have_evidence: bool = True
    factual_auto_answer_count: int = 0
    unsupported_metric_count: int = 0


class DiscoveryAnalysisResult(BaseModel):
    """Output from Discovery Call A — analyze and prepare questions (v2)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 2
    operation: str = "prepare_questions"
    source_assessment: SourceAssessment = Field(default_factory=SourceAssessment)
    profile_overview: ProfileOverview = Field(default_factory=ProfileOverview)
    normalized_profile: NormalizedProfessionalProfile = Field(
        default_factory=NormalizedProfessionalProfile
    )
    facts: list[FactCandidate] = Field(default_factory=list, max_length=500)
    conflicts: list[DiscoveryConflict] = Field(default_factory=list, max_length=50)
    uncertainties: list[Uncertainty] = Field(default_factory=list, max_length=50)
    questions: list[DiscoveryQuestion] = Field(default_factory=list, max_length=10)
    auto_decisions: list[AutoDecision] = Field(default_factory=list, max_length=20)
    omission_candidates: list[OmissionCandidate] = Field(default_factory=list, max_length=100)
    readiness: Readiness = Field(default_factory=Readiness)
    quality_checks: QualityChecksCallA = Field(default_factory=QualityChecksCallA)
    input_warnings: list[DiscoveryWarning] = Field(default_factory=list, max_length=20)


# ── Call B: Strategic Brief (v2) ─────────────────────────────────────────────


class ExecutiveSummary(BaseModel):
    """Call B: one-paragraph strategy summary with scope and readiness."""

    model_config = ConfigDict(extra="forbid")

    strategy_summary: str = Field(default="", max_length=2000)
    portfolio_scope: PortfolioScope = PortfolioScope.STANDARD
    readiness: BriefReadiness = BriefReadiness.READY_WITH_OMISSIONS
    main_opportunity: str = Field(default="", max_length=1000)
    main_limitation: str = Field(default="", max_length=1000)


class PrimaryTargetRole(BaseModel):
    """Call B: the single primary role the portfolio should target."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(default="", max_length=256)
    basis_fact_ids: list[str] = Field(default_factory=list, max_length=30)
    decision_source: DecisionSource = DecisionSource.USER_ANSWER
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class SecondaryStrength(BaseModel):
    """Call B: a secondary strength that stays visible."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(default="", max_length=256)
    basis_fact_ids: list[str] = Field(default_factory=list, max_length=30)


class AudienceEntry(BaseModel):
    """Call B: one portfolio audience."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(default="", max_length=256)
    priority: str = Field(default="primary", max_length=32)


class PortfolioGoal(BaseModel):
    """Call B: the outcome the user wants from the portfolio."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(default="", max_length=1000)
    basis: DecisionSource = DecisionSource.USER_ANSWER


class CareerStageEntry(BaseModel):
    """Call B: career-stage reading. Never translated into public seniority."""

    model_config = ConfigDict(extra="forbid")

    value: CareerStage = CareerStage.UNKNOWN
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    note: str = Field(default="", max_length=500)


class IdentityAndGoal(BaseModel):
    """Call B: who the portfolio is for and what it must achieve."""

    model_config = ConfigDict(extra="forbid")

    primary_target_role: PrimaryTargetRole = Field(default_factory=PrimaryTargetRole)
    secondary_strengths: list[SecondaryStrength] = Field(default_factory=list, max_length=10)
    audiences: list[AudienceEntry] = Field(default_factory=list, max_length=10)
    portfolio_goal: PortfolioGoal = Field(default_factory=PortfolioGoal)
    career_stage: CareerStageEntry = Field(default_factory=CareerStageEntry)


class Differentiator(BaseModel):
    """Call B: one evidence-backed positioning differentiator."""

    model_config = ConfigDict(extra="forbid")

    statement: str = Field(default="", max_length=1000)
    basis_fact_ids: list[str] = Field(default_factory=list, max_length=30)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class PositioningStrategy(BaseModel):
    """Call B: evidence-backed positioning with explicit credibility limits."""

    model_config = ConfigDict(extra="forbid")

    positioning_direction: str = Field(default="", max_length=1500)
    differentiators: list[Differentiator] = Field(default_factory=list, max_length=15)
    evidence_strengths: list[str] = Field(default_factory=list, max_length=20)
    credibility_boundaries: list[str] = Field(default_factory=list, max_length=20)


class SectionPriorityEntry(BaseModel):
    """Call B: one recommended section with priority and purpose."""

    model_config = ConfigDict(extra="forbid")

    section: str = Field(default="", max_length=128)
    priority: int = 0
    purpose: str = Field(default="", max_length=500)


class ContentDensity(BaseModel):
    """Call B: how much content depth the evidence justifies."""

    model_config = ConfigDict(extra="forbid")

    recommendation: ContentDepth = ContentDepth.BALANCED
    reason: str = Field(default="", max_length=1000)


class ProjectContribution(BaseModel):
    """Call B: one supported personal contribution for a featured project."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(default="", max_length=1000)
    basis_fact_ids: list[str] = Field(default_factory=list, max_length=30)


class ProjectConfidentiality(BaseModel):
    """Call B: confidentiality level and restrictions for one project."""

    model_config = ConfigDict(extra="forbid")

    level: str = Field(default="normal", max_length=64)
    restrictions: list[str] = Field(default_factory=list, max_length=20)


class FeaturedProject(BaseModel):
    """Call B: one featured project with evidence, depth, and unknowns."""

    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(default="", max_length=128)
    priority: int = 0
    selection_reason: str = Field(default="", max_length=1000)
    target_role_relevance: str = Field(default="medium", max_length=64)
    supported_project_scope: str = Field(default="", max_length=1500)
    supported_personal_contribution: list[ProjectContribution] = Field(
        default_factory=list, max_length=10
    )
    narrative_focus: list[str] = Field(default_factory=list, max_length=20)
    recommended_content_depth: ContentDepth = ContentDepth.BALANCED
    evidence_to_preserve: list[str] = Field(default_factory=list, max_length=30)
    unknowns_to_omit: list[str] = Field(default_factory=list, max_length=20)
    confidentiality: ProjectConfidentiality = Field(default_factory=ProjectConfidentiality)


class ExperienceFocus(BaseModel):
    """Call B: an experience dimension the portfolio should emphasize."""

    model_config = ConfigDict(extra="forbid")

    focus: str = Field(default="", max_length=500)
    basis_fact_ids: list[str] = Field(default_factory=list, max_length=30)


class CapabilityCluster(BaseModel):
    """Call B: a grouped set of related capabilities."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(default="", max_length=256)
    items: list[str] = Field(default_factory=list, max_length=50)
    basis_fact_ids: list[str] = Field(default_factory=list, max_length=30)


class ItemToOmit(BaseModel):
    """Call B: a deliberate content omission."""

    model_config = ConfigDict(extra="forbid")

    item: str = Field(default="", max_length=500)
    reason: str = Field(default="", max_length=500)


class ContentStrategy(BaseModel):
    """Call B: what content leads, what depth, and what is omitted."""

    model_config = ConfigDict(extra="forbid")

    recommended_section_priority: list[SectionPriorityEntry] = Field(
        default_factory=list, max_length=20
    )
    content_density: ContentDensity = Field(default_factory=ContentDensity)
    featured_projects: list[FeaturedProject] = Field(default_factory=list, max_length=10)
    experience_focus: list[ExperienceFocus] = Field(default_factory=list, max_length=20)
    capability_clusters: list[CapabilityCluster] = Field(default_factory=list, max_length=20)
    items_to_omit: list[ItemToOmit] = Field(default_factory=list, max_length=30)


class PresentationPreference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str = Field(default="", max_length=128)
    source: str = Field(default="auto", max_length=32)
    explanation: str = Field(default="", max_length=500)


class PresentationDirection(BaseModel):
    """Call B: high-level presentation direction, not a visual blueprint."""

    model_config = ConfigDict(extra="forbid")

    tone: PresentationPreference = Field(default_factory=PresentationPreference)
    voice_rules: list[str] = Field(default_factory=list, max_length=20)
    theme_preference: PresentationPreference = Field(default_factory=PresentationPreference)
    motion_preference: PresentationPreference = Field(default_factory=PresentationPreference)
    visual_density: str = Field(default="balanced", max_length=64)
    technical_editorial_balance: str = Field(default="balanced", max_length=64)
    patterns_to_avoid: list[str] = Field(default_factory=list, max_length=20)


class ContactChoice(BaseModel):
    """Call B: one contact method and its publication decision."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(default="", max_length=64)
    source: ContactSource = ContactSource.EXPLICIT_USER_CHOICE
    fact_id: str | None = Field(default=None, max_length=128)


class PrivateOrOmittedContact(BaseModel):
    """Call B: a contact method that must NOT be published."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(default="", max_length=64)
    reason: str = Field(default="", max_length=500)


class CtaAndContact(BaseModel):
    """Call B: CTA intent and explicit contact publication decisions."""

    model_config = ConfigDict(extra="forbid")

    primary_cta_intent: str = Field(default="", max_length=500)
    secondary_cta_intent: str | None = Field(default=None, max_length=500)
    publishable_contact_choices: list[ContactChoice] = Field(default_factory=list, max_length=10)
    private_or_omitted_contact: list[PrivateOrOmittedContact] = Field(
        default_factory=list, max_length=10
    )


class ConfidentialityRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: str = Field(default="", max_length=256)
    rule: str = Field(default="", max_length=500)
    applies_to: list[str] = Field(default_factory=list, max_length=20)
    fact_ids: list[str] = Field(default_factory=list, max_length=10)


class ConfidentialityAndOmissions(BaseModel):
    """Call B: confidentiality boundaries and deliberate omissions."""

    model_config = ConfigDict(extra="forbid")

    rules: list[ConfidentialityRule] = Field(default_factory=list, max_length=10)
    deliberate_omissions: list[str] = Field(default_factory=list, max_length=30)


class UnresolvedItem(BaseModel):
    """Call B: an unresolved material item preserved for later agents."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default="", max_length=128)
    severity: UnresolvedSeverity = UnresolvedSeverity.MATERIAL
    summary: str = Field(default="", max_length=1000)
    downstream_behavior: str = Field(default="", max_length=1000)


class CarefulWordingEntry(BaseModel):
    """Call B: a fact that requires cautious wording downstream."""

    model_config = ConfigDict(extra="forbid")

    fact_id: str = Field(default="", max_length=128)
    guidance: str = Field(default="", max_length=1000)


class ClaimPolicy(BaseModel):
    """Call B: explicit claim boundaries for later agents."""

    model_config = ConfigDict(extra="forbid")

    must_use_fact_ids: list[str] = Field(default_factory=list, max_length=200)
    allowed_user_asserted_fact_ids: list[str] = Field(default_factory=list, max_length=50)
    requires_careful_wording: list[CarefulWordingEntry] = Field(default_factory=list, max_length=30)
    must_not_claim: list[str] = Field(default_factory=list, max_length=30)


class ContentArchitectHandoff(BaseModel):
    """Call B: constraints for the Content Architect (no final copy)."""

    model_config = ConfigDict(extra="forbid")

    central_story: str = Field(default="", max_length=1500)
    content_hierarchy: list[str] = Field(default_factory=list, max_length=20)
    evidence_to_preserve: list[str] = Field(default_factory=list, max_length=30)
    writing_constraints: list[str] = Field(default_factory=list, max_length=20)


class VisualDesignDirectorHandoff(BaseModel):
    """Call B: constraints for the Visual Design Director (no layout)."""

    model_config = ConfigDict(extra="forbid")

    desired_impression: str = Field(default="", max_length=1000)
    content_implications: list[str] = Field(default_factory=list, max_length=20)
    presentation_constraints: list[str] = Field(default_factory=list, max_length=20)


class DownstreamHandoff(BaseModel):
    """Call B: rich strategic handoff for later agents."""

    model_config = ConfigDict(extra="forbid")

    content_architect: ContentArchitectHandoff = Field(default_factory=ContentArchitectHandoff)
    visual_design_director: VisualDesignDirectorHandoff = Field(
        default_factory=VisualDesignDirectorHandoff
    )
    universal_constraints: list[str] = Field(default_factory=list, max_length=30)


class DecisionLogEntry(BaseModel):
    """Call B: one recorded decision and its source."""

    model_config = ConfigDict(extra="forbid")

    decision: str = Field(default="", max_length=500)
    source: DecisionSource = DecisionSource.MODEL_RECOMMENDATION
    related_fact_ids: list[str] = Field(default_factory=list, max_length=30)


class QualityChecksCallB(BaseModel):
    """Call B: deterministic quality self-checks."""

    model_config = ConfigDict(extra="forbid")

    all_factual_strategies_reference_facts: bool = True
    unsupported_metrics_included: bool = False
    skipped_facts_converted_to_claims: bool = False
    factual_auto_decisions_included: bool = False
    unresolved_material_conflicts_preserved: bool = True
    final_portfolio_copy_included: bool = False


class DiscoveryBrief(BaseModel):
    """Output from Discovery Call B — strategic portfolio brief (v2).

    The brief is a strategic handoff for later agents. It must not contain
    final hero/about/project copy, exact components, layout, or code.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 2
    operation: str = "build_brief"
    executive_summary: ExecutiveSummary = Field(default_factory=ExecutiveSummary)
    identity_and_goal: IdentityAndGoal = Field(default_factory=IdentityAndGoal)
    positioning_strategy: PositioningStrategy = Field(default_factory=PositioningStrategy)
    content_strategy: ContentStrategy = Field(default_factory=ContentStrategy)
    presentation_direction: PresentationDirection = Field(default_factory=PresentationDirection)
    cta_and_contact: CtaAndContact = Field(default_factory=CtaAndContact)
    confidentiality_and_omissions: ConfidentialityAndOmissions = Field(
        default_factory=ConfidentialityAndOmissions
    )
    unresolved_items: list[UnresolvedItem] = Field(default_factory=list, max_length=20)
    claim_policy: ClaimPolicy = Field(default_factory=ClaimPolicy)
    downstream_handoff: DownstreamHandoff = Field(default_factory=DownstreamHandoff)
    decision_log: list[DecisionLogEntry] = Field(default_factory=list, max_length=30)
    quality_checks: QualityChecksCallB = Field(default_factory=QualityChecksCallB)
    output_language: str = Field(default="en", max_length=10)
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
