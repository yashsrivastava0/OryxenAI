"""Discovery agent domain schemas.

Only the OUTPUT contract is validated. Input (message, document text, goal,
answers) is accepted as-is — the model decides how detailed the output should
be. No model-specific imports.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QuestionKind(StrEnum):
    TEXT = "text"
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    BOOLEAN = "boolean"


class AnswerMode(StrEnum):
    ANSWERED = "answered"
    SKIPPED = "skipped"


class OperationMode(StrEnum):
    NEEDS_DETAILS = "NEEDS_DETAILS"
    ASK_QUESTIONS = "ASK_QUESTIONS"
    READY_FOR_BRIEF = "READY_FOR_BRIEF"
    BRIEF_READY = "BRIEF_READY"


class DiscoveryStatus(StrEnum):
    NOT_STARTED = "not_started"
    QUESTIONS_QUEUED = "questions_queued"
    QUESTIONS_RUNNING = "questions_running"
    QUESTIONS_READY = "questions_ready"
    ANSWERS_IN_PROGRESS = "answers_in_progress"
    BRIEF_RUNNING = "brief_running"
    BRIEF_REVIEW = "brief_review"
    NEEDS_INPUT = "needs_input"
    APPROVED = "approved"
    NEEDS_ATTENTION = "needs_attention"


# ── Input (deliberately unvalidated) ────────────────────────────────────────


class DiscoveryIntake(BaseModel):
    """Raw user input. Any type of input is accepted — no validation."""

    model_config = ConfigDict(extra="allow")

    message: str = ""
    document_text: str = ""
    goal: str = ""
    source_text: str = ""


class ProfileLink(BaseModel):
    """One public link (portfolio, GitHub, LinkedIn, ...)."""

    model_config = ConfigDict(extra="forbid")

    label: str = ""
    url: str = ""


class SourceDisposition(StrEnum):
    FACT = "fact"
    INTENT_PREFERENCE = "intent_preference"
    RESTRICTION = "restriction"
    REFERENCE_CONTEXT = "reference_context"
    DUPLICATE = "duplicate"
    EXCLUDED = "excluded"


class FactStatus(StrEnum):
    SOURCE_ASSERTED = "source_asserted"
    USER_CONFIRMED = "user_confirmed"
    CONFLICTING = "conflicting"
    SUPERSEDED = "superseded"


class FactOwnership(StrEnum):
    INDIVIDUAL = "individual"
    TEAM = "team"
    UNKNOWN = "unknown"


class SourceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    start: int
    end: int
    excerpt: str = ""


class SourceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str = "Source material"
    source_kind: str = "user_provided"
    format: str = "text"
    offset_unit: str = "utf16_code_units"
    original_text: str
    sha256: str
    spans: list[SourceSpan] = Field(default_factory=list)
    created_at: str = ""


class DossierIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = ""
    audience: str = ""
    visitor_action: str = ""
    language: str = ""
    preferences: list[str] = Field(default_factory=list)
    basis: dict[str, str] = Field(default_factory=dict)
    basis_refs: dict[str, list[str]] = Field(default_factory=dict)


class DossierSubject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    current_title: str = ""
    location: str = ""
    links: list[ProfileLink] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class DossierFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = ""
    category: str = ""
    statement: str = ""
    original_wording: str = ""
    source_refs: list[str] = Field(default_factory=list)
    qualifiers: list[str] = Field(default_factory=list)
    ownership: FactOwnership = FactOwnership.UNKNOWN
    status: FactStatus = FactStatus.SOURCE_ASSERTED
    supersedes_ref: str = ""


class DossierRole(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = ""
    organization: str = ""
    role: str = ""
    dates: str = ""
    details: list[str] = Field(default_factory=list)
    fact_ids: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class DossierProject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = ""
    name: str = ""
    problem: str = ""
    personal_contribution: str = ""
    team_contribution: str = ""
    approach: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    fact_ids: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class DossierEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = ""
    category: str = ""
    title: str = ""
    detail: str = ""
    fact_ids: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class DossierOpenItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = ""
    detail: str = ""
    importance: str = "context"
    status: str = "open"
    safe_wording: str = ""
    affected_ids: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class DossierRestriction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = ""
    scope: str = ""
    instruction: str = ""
    disposition: str = "omit"
    source_refs: list[str] = Field(default_factory=list)


class SourceCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    span_id: str
    disposition: SourceDisposition
    fact_ids: list[str] = Field(default_factory=list)
    reason: str = ""


class QuestionAnswerRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: int = 0
    status: str = "answered"
    answer: str = ""
    source_refs: list[str] = Field(default_factory=list)
    recorded_at: str = ""


class QuestionHistoryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    gap_id: str = ""
    question: str = ""
    reason: str = ""
    affected_ids: list[str] = Field(default_factory=list)
    status: str = "pending"
    answer: str = ""
    answer_source_refs: list[str] = Field(default_factory=list)
    answer_history: list[QuestionAnswerRevision] = Field(default_factory=list)


class DossierLineage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    source_document_ids: list[str] = Field(default_factory=list)
    source_hashes: list[str] = Field(default_factory=list)
    schema_version: str = "DiscoveryDossier/v1"
    provenance_status: str = "source_indexed"
    created_at: str = ""
    payload_hash: str = ""


class DiscoveryDossier(BaseModel):
    """Complete source-linked factual handoff produced by Discovery."""

    model_config = ConfigDict(extra="forbid")

    contract_version: str = "DiscoveryDossier/v1"
    id: str = ""
    intent: DossierIntent = Field(default_factory=DossierIntent)
    subject: DossierSubject = Field(default_factory=DossierSubject)
    facts: list[DossierFact] = Field(default_factory=list)
    roles: list[DossierRole] = Field(default_factory=list)
    projects: list[DossierProject] = Field(default_factory=list)
    other_evidence: list[DossierEvidence] = Field(default_factory=list)
    open_items: list[DossierOpenItem] = Field(default_factory=list)
    user_choices: list[str] = Field(default_factory=list)
    restrictions: list[DossierRestriction] = Field(default_factory=list)
    source_coverage: list[SourceCoverage] = Field(default_factory=list)
    question_events: list[QuestionHistoryEvent] = Field(default_factory=list)
    lineage: DossierLineage = Field(default_factory=DossierLineage)


# ── Output: Operation A (understand_and_question) ───────────────────────────


class QuestionOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = ""
    label: str = ""


class DiscoveryQuestion(BaseModel):
    """One question for the user during Discovery (output contract)."""

    model_config = ConfigDict(extra="forbid")

    id: str = ""
    text: str = ""
    help_text: str | None = None
    kind: QuestionKind = QuestionKind.TEXT
    options: list[QuestionOption] = Field(default_factory=list)
    reason: str | None = None
    gap_id: str = ""
    affected_ids: list[str] = Field(default_factory=list)
    allow_skip: bool = True
    allow_auto: bool = False


class QuestionSetOutput(BaseModel):
    """Structured output of the understand_and_question model call."""

    model_config = ConfigDict(extra="forbid")

    mode: OperationMode
    assistant_message: str
    questions: list[DiscoveryQuestion] = Field(default_factory=list)
    memory_update: dict[str, Any] = Field(default_factory=dict)


# ── Output: Operation B (build_or_revise_brief) ─────────────────────────────


class ExperienceEntry(BaseModel):
    """One role in the structured profile. Facts only, never invented."""

    model_config = ConfigDict(extra="forbid")

    organization: str = ""
    role: str = ""
    dates: str = ""
    highlights: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    """One education or certification entry."""

    model_config = ConfigDict(extra="forbid")

    institution: str = ""
    credential: str = ""
    dates: str = ""


class ProjectEntry(BaseModel):
    """One project or work sample in the structured profile."""

    model_config = ConfigDict(extra="forbid")

    name: str = ""
    summary: str = ""
    contribution: str = ""
    tech: list[str] = Field(default_factory=list)
    link: str = ""


class StructuredProfile(BaseModel):
    """Categorized facts extracted from the user's material.

    Facts only — no judgment, grouping labels, provenance, or confidence
    scores. Positioning, strategy, and skill-grouping stay in brief_markdown.
    Every field defaults empty and must stay empty when the source does not
    supply it; nothing here may be invented.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = ""
    current_title: str = ""
    location: str = ""
    links: list[ProfileLink] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    spoken_languages: list[str] = Field(default_factory=list)
    private_omitted: list[str] = Field(default_factory=list)


class BriefOutput(BaseModel):
    """Structured output of the build_or_revise_brief model call.

    The brief itself is free Markdown text; only the envelope is validated.
    """

    model_config = ConfigDict(extra="forbid")

    mode: OperationMode  # always BRIEF_READY
    assistant_message: str
    brief_title: str
    brief_markdown: str
    user_summary: str = ""
    profile: StructuredProfile = Field(default_factory=StructuredProfile)
    dossier: DiscoveryDossier
    open_items: list[str] = Field(default_factory=list)
    memory_update: dict[str, Any] = Field(default_factory=dict)


# ── Answers ─────────────────────────────────────────────────────────────────


class DiscoveryAnswer(BaseModel):
    """A user-provided answer. Value is stored as-is."""

    model_config = ConfigDict(extra="allow")

    question_id: str = ""
    mode: AnswerMode = AnswerMode.ANSWERED
    value: Any = None


# ── Approval ────────────────────────────────────────────────────────────────


class DiscoveryApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved_at: str = ""
    brief_hash: str = ""


# ── Discovery State ─────────────────────────────────────────────────────────


class OperationAState(BaseModel):
    """Persisted slice of the last Operation A output, for refresh recovery."""

    model_config = ConfigDict(extra="forbid")

    version: str = ""
    run_id: str = ""
    job_id: str = ""
    mode: OperationMode | None = None
    assistant_message: str = ""
    items: list[DiscoveryQuestion] = Field(default_factory=list)
    memory_update: dict[str, Any] = Field(default_factory=dict)


class AnswersState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: int = 0
    items: dict[str, DiscoveryAnswer] = Field(default_factory=dict)


class BriefState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = ""
    run_id: str = ""
    job_id: str = ""
    title: str = ""
    markdown: str = ""
    user_summary: str = ""
    profile: StructuredProfile = Field(default_factory=StructuredProfile)
    dossier_hash: str = ""
    open_items: list[str] = Field(default_factory=list)
    memory_update: dict[str, Any] = Field(default_factory=dict)
    revision_request: str = ""
    approved: DiscoveryApproval | None = None


class DiscoveryState(BaseModel):
    """Current Discovery session state stored under portfolio_sessions.current_state['discovery']."""

    model_config = ConfigDict(extra="forbid")

    status: DiscoveryStatus = DiscoveryStatus.NOT_STARTED
    model_profile: str = ""
    routing_policy_version: str = ""
    routing_policy_fingerprint: str = ""
    intake: DiscoveryIntake = Field(default_factory=DiscoveryIntake)
    source_documents: list[SourceDocument] = Field(default_factory=list)
    dossier: DiscoveryDossier | None = None
    question_events: list[QuestionHistoryEvent] = Field(default_factory=list)
    operation_a: OperationAState = Field(default_factory=OperationAState)
    answers: AnswersState = Field(default_factory=AnswersState)
    brief: BriefState = Field(default_factory=BriefState)
    memory: dict[str, Any] = Field(default_factory=dict)
    latest_error: dict[str, Any] | None = None
    attempt: int = 0
    max_attempts: int = 3
    started_at: str | None = None


# ── Structured Model Result ─────────────────────────────────────────────────


class StructuredModelResult(BaseModel):
    """Normalized result from a structured model call."""

    model_config = ConfigDict(extra="forbid")

    parsed_output: dict[str, Any] = Field(default_factory=dict)
    response_id: str | None = None
    model: str = ""
    usage: dict[str, Any] = Field(default_factory=dict)
    finish_reason: str | None = None
    latency_ms: float = 0.0
    telemetry: dict[str, Any] = Field(default_factory=dict)
    # This is transport metadata only. Agent output remains independent from
    # whether the result came from the durable cache or a provider call.
    cache_metadata: dict[str, Any] = Field(default_factory=dict)
