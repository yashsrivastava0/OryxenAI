"""Lenient, compact model-facing Explorer output shapes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Draft(BaseModel):
    """Base for model-produced drafts: lenient, unknown keys are ignored.

    Drafts describe what the model is asked to return. They are never the
    persisted shape; ``normalize.py`` repairs a raw response into the strict
    state models above, so a stray key or a wrong enum cannot fail a run.
    """

    model_config = ConfigDict(extra="ignore")


class QuestionOptionDraft(_Draft):
    id: str = ""
    label: str = ""


class QuestionDraft(_Draft):
    id: str = ""
    text: str = ""
    kind: str = "text"
    options: list[QuestionOptionDraft] = Field(default_factory=list)
    help_text: str | None = None
    reason: str | None = None


class QuestionSetOutput(_Draft):
    """Model-facing output of the understand_and_question call."""

    mode: str = ""
    assistant_message: str = ""
    questions: list[QuestionDraft] = Field(default_factory=list)


class LinkDraft(_Draft):
    label: str = ""
    url: str = ""


class IntentDraft(_Draft):
    goal: str = ""
    audience: str = ""
    visitor_action: str = ""
    language: str = ""
    preferences: list[str] = Field(default_factory=list)


class SubjectDraft(_Draft):
    name: str = ""
    current_title: str = ""
    location: str = ""
    links: list[LinkDraft] = Field(default_factory=list)


class FactDraft(_Draft):
    id: str = ""
    category: str = ""
    statement: str = ""
    ownership: str = "unknown"
    qualifiers: list[str] = Field(default_factory=list)


class RoleDraft(_Draft):
    id: str = ""
    organization: str = ""
    role: str = ""
    dates: str = ""
    details: list[str] = Field(default_factory=list)
    fact_ids: list[str] = Field(default_factory=list)


class ProjectDraft(_Draft):
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


class EvidenceDraft(_Draft):
    id: str = ""
    category: str = ""
    title: str = ""
    detail: str = ""
    fact_ids: list[str] = Field(default_factory=list)


class RestrictionDraft(_Draft):
    id: str = ""
    scope: str = ""
    instruction: str = ""
    disposition: str = "omit"


class DossierDraft(_Draft):
    """The compact handoff the model writes; the server builds DiscoveryDossier from it."""

    intent: IntentDraft = Field(default_factory=IntentDraft)
    subject: SubjectDraft = Field(default_factory=SubjectDraft)
    facts: list[FactDraft] = Field(default_factory=list)
    roles: list[RoleDraft] = Field(default_factory=list)
    projects: list[ProjectDraft] = Field(default_factory=list)
    other_evidence: list[EvidenceDraft] = Field(default_factory=list)
    restrictions: list[RestrictionDraft] = Field(default_factory=list)


class BriefOutput(_Draft):
    """Model-facing output of the build_or_revise_brief call.

    Only ``brief_markdown`` is essential; every other field is repaired or
    derived by ``normalize.py`` when the model leaves it out.
    """

    assistant_message: str = ""
    brief_title: str = ""
    user_summary: str = ""
    brief_markdown: str = ""
    open_items: list[str] = Field(default_factory=list)
    dossier: DossierDraft = Field(default_factory=DossierDraft)
