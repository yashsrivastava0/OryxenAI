"""Code Generator contracts: the model envelope, failures, and persisted state.

The model returns a tiny envelope; everything else here is host-owned. A
failure is always one :class:`FailureEnvelope`: what failed (``code``,
``stage``), where (``where``), why (``cause``), and what to do (``action``).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ── model output ─────────────────────────────────────────────────────────────


class GeneratedPageEnvelope(BaseModel):
    """What ``generate_page`` returns: the page body and its language tag."""

    model_config = ConfigDict(extra="ignore")

    lang: str = "en"
    body_html: str


class ChangeIntent(StrEnum):
    CONTENT_EDIT = "content_edit"
    STYLE_REQUEST = "style_request"
    NEEDS_CLARIFICATION = "needs_clarification"
    CHAT_ONLY = "chat_only"
    UNSUPPORTED = "unsupported"


class ChangeOperation(BaseModel):
    """One typed edit to ``page_content`` proposed by ``interpret_change``."""

    model_config = ConfigDict(extra="ignore")

    op: Literal["set", "append", "remove"]
    path: str
    value: Any = None


class ChangePlanEnvelope(BaseModel):
    """What ``interpret_change`` returns."""

    model_config = ConfigDict(extra="ignore")

    intent: ChangeIntent = ChangeIntent.CHAT_ONLY
    reply: str = ""
    clarification: str = ""
    privacy_sensitive: bool = False
    ops: list[ChangeOperation] = Field(default_factory=list)


# ── failures ─────────────────────────────────────────────────────────────────

FailureStage = Literal["start", "interpret", "generate", "validate", "bundle", "verify", "promote"]
FailureOwner = Literal[
    "model_output",
    "validation",
    "content",
    "theme",
    "browser",
    "infrastructure",
    "configuration",
    "user_input",
]


class FailureLocation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["field", "selector", "source", "viewport", "request", "file"]
    ref: str
    detail: str = ""


class FailureEnvelope(BaseModel):
    """One structured, user-presentable failure: what, where, why, what next."""

    model_config = ConfigDict(extra="ignore")

    code: str
    stage: FailureStage
    summary: str
    cause: str = ""
    where: list[FailureLocation] = Field(default_factory=list)
    expected: str | None = None
    found: str | None = None
    owner: FailureOwner = "infrastructure"
    retryable: bool = True
    action: str = ""
    issue_count: int = 0
    reference: str = ""
    issues: list[dict[str, Any]] = Field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class CodeGeneratorFailure(Exception):
    """Raised by pipeline steps; carries the envelope that will be persisted."""

    def __init__(self, envelope: FailureEnvelope) -> None:
        self.envelope = envelope
        super().__init__(f"{envelope.code}: {envelope.summary}")
