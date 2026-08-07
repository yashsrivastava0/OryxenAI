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
    APPROVED = "approved"
    NEEDS_ATTENTION = "needs_attention"


# ── Input (deliberately unvalidated) ────────────────────────────────────────


class DiscoveryIntake(BaseModel):
    """Raw user input. Any type of input is accepted — no validation."""

    model_config = ConfigDict(extra="allow")

    message: str = ""
    document_text: str = ""
    goal: str = ""


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


class BriefOutput(BaseModel):
    """Structured output of the build_or_revise_brief model call.

    The brief itself is free Markdown text; only the envelope is validated.
    """

    model_config = ConfigDict(extra="forbid")

    mode: OperationMode  # always BRIEF_READY
    assistant_message: str
    brief_title: str
    brief_markdown: str
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
    open_items: list[str] = Field(default_factory=list)
    memory_update: dict[str, Any] = Field(default_factory=dict)
    revision_request: str = ""
    approved: DiscoveryApproval | None = None


class DiscoveryState(BaseModel):
    """Current Discovery session state stored under portfolio_sessions.current_state['discovery']."""

    model_config = ConfigDict(extra="forbid")

    status: DiscoveryStatus = DiscoveryStatus.NOT_STARTED
    intake: DiscoveryIntake = Field(default_factory=DiscoveryIntake)
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
