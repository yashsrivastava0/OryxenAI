"""Content Architect state machine.

Five statuses, one linear flow — deliberately simpler than Explorer's own
two-operation machine because Content Architect runs as a single durable job
(`content_architect.build`) whose agent makes up to 3 model calls internally.
There is no separate queued/running pair per stage, and no per-stage status,
because only one job kind ever writes this state.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from oryxenai.agents.content_architect.page_content import (
    claim_binding_errors,
    page_completeness_errors,
    page_shape_errors,
)
from oryxenai.agents.content_architect.schemas import (
    ClaimGrounding,
    ContentArchitectApproval,
    ContentArchitectIntake,
    ContentArchitectPreferences,
    ContentArchitectSourceRef,
    ContentArchitectState,
    ContentArchitectStatus,
    ContentCoverageEntry,
    ContentStoryStrategy,
    DecisionRecord,
    PortfolioPageContent,
)


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, current: str, target: str, reason: str = "") -> None:
        self.current = current
        self.target = target
        self.reason = reason
        super().__init__(
            f"Cannot transition from '{current}' to '{target}'{': ' + reason if reason else ''}"
        )


class ContentNotPublishableError(ValueError):
    """Approval attempted with no page content at all.

    The state machine is the authoritative place to refuse approval when a
    review state carries nothing for a visitor to read.
    """

    def __init__(self, message: str = "") -> None:
        self.message = message or (
            "Cannot approve: there is no page content. Revise or re-run Content Architect."
        )
        super().__init__(self.message)


class PublicScopeIncompleteError(ValueError):
    """Approval attempted with page content that is incomplete or unsafe.

    This check runs before the approval hash is stamped, so an approved page
    never has missing template fields or claims bound to non-public copy.
    """

    def __init__(self, *, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(
            "Cannot approve: the page content is incomplete. "
            "Revise Content Architect so the page has complete safe content."
        )


_TERMINAL = frozenset({ContentArchitectStatus.APPROVED})


def _is_terminal(status: ContentArchitectStatus) -> bool:
    return status in _TERMINAL


_VALID_TRANSITIONS: dict[ContentArchitectStatus, frozenset[ContentArchitectStatus]] = {
    ContentArchitectStatus.NOT_STARTED: frozenset({ContentArchitectStatus.BUILD_RUNNING}),
    ContentArchitectStatus.BUILD_RUNNING: frozenset(
        {ContentArchitectStatus.CONTENT_REVIEW, ContentArchitectStatus.NEEDS_ATTENTION}
    ),
    ContentArchitectStatus.CONTENT_REVIEW: frozenset(
        {ContentArchitectStatus.APPROVED, ContentArchitectStatus.BUILD_RUNNING}
    ),
    ContentArchitectStatus.NEEDS_ATTENTION: frozenset({ContentArchitectStatus.BUILD_RUNNING}),
}


def is_valid_transition(current: ContentArchitectStatus, target: ContentArchitectStatus) -> bool:
    return current != target and target in _VALID_TRANSITIONS.get(current, frozenset())


def apply_start(
    state: ContentArchitectState,
    *,
    source_ref: ContentArchitectSourceRef,
    intake: ContentArchitectIntake,
    preferences: ContentArchitectPreferences,
) -> ContentArchitectState:
    """Start (or restart from NEEDS_ATTENTION) a Content Architect build."""
    _validate_transition(state.status, ContentArchitectStatus.BUILD_RUNNING)
    new_state = state.model_copy(deep=True)
    new_state.status = ContentArchitectStatus.BUILD_RUNNING
    new_state.source_ref = source_ref
    new_state.intake = intake
    new_state.preferences = preferences
    if not new_state.started_at:
        new_state.started_at = datetime.now(UTC).isoformat()
    new_state.latest_error = None
    return new_state


def apply_build_running(
    state: ContentArchitectState, run_id: str, job_id: str
) -> ContentArchitectState:
    """Idempotent re-entry helper for the job handler.

    Mostly a no-op when the service already set BUILD_RUNNING before the job
    was claimed; matters for the retry-from-NEEDS_ATTENTION recovery path.
    """
    new_state = state.model_copy(deep=True)
    if new_state.status != ContentArchitectStatus.BUILD_RUNNING:
        _validate_transition(state.status, ContentArchitectStatus.BUILD_RUNNING)
        new_state.status = ContentArchitectStatus.BUILD_RUNNING
    new_state.run_id = run_id
    new_state.job_id = job_id
    return new_state


def apply_revision_requested(
    state: ContentArchitectState,
    run_id: str,
    job_id: str,
    revision_request: str,
) -> ContentArchitectState:
    """Re-run the build pipeline from CONTENT_REVIEW with a revision request."""
    _validate_transition(state.status, ContentArchitectStatus.BUILD_RUNNING)
    new_state = state.model_copy(deep=True)
    new_state.status = ContentArchitectStatus.BUILD_RUNNING
    new_state.run_id = run_id
    new_state.job_id = job_id
    new_state.revision_request = revision_request
    return new_state


def apply_build_result(
    state: ContentArchitectState,
    *,
    version: str,
    run_id: str,
    user_summary: str,
    site_story_strategy: ContentStoryStrategy,
    decision_basis: list[DecisionRecord],
    page_content: PortfolioPageContent,
    internal_notes: dict[str, Any],
    claim_grounding: list[ClaimGrounding],
    omissions: list[str],
    unresolved_issues: list[str],
    privacy_and_confidentiality: list[str],
    warnings: list[str],
    stages_run: list[str],
    memory_update: dict[str, Any],
    coverage_ledger: list[ContentCoverageEntry] | None = None,
) -> ContentArchitectState:
    """Persist a successful build result and move to CONTENT_REVIEW."""
    _validate_transition(state.status, ContentArchitectStatus.CONTENT_REVIEW)
    new_state = state.model_copy(deep=True)
    new_state.status = ContentArchitectStatus.CONTENT_REVIEW
    new_state.version = version
    new_state.run_id = run_id
    new_state.user_summary = user_summary
    new_state.site_story_strategy = site_story_strategy
    new_state.decision_basis = decision_basis
    new_state.page_content = page_content
    new_state.internal_notes = internal_notes
    new_state.claim_grounding = claim_grounding
    new_state.coverage_ledger = coverage_ledger or []
    new_state.omissions = omissions
    new_state.unresolved_issues = unresolved_issues
    new_state.privacy_and_confidentiality = privacy_and_confidentiality
    new_state.warnings = warnings
    new_state.stages_run = stages_run
    new_state.memory = _merge_memory(state.memory, memory_update)
    new_state.latest_error = None
    return new_state


def apply_approval(state: ContentArchitectState, content_hash: str) -> ContentArchitectState:
    _validate_transition(state.status, ContentArchitectStatus.APPROVED)
    if not state.page_content.model_dump(mode="json", exclude_defaults=True):
        raise ContentNotPublishableError()
    scope_errors = public_scope_errors(state)
    if scope_errors:
        raise PublicScopeIncompleteError(errors=scope_errors)
    new_state = state.model_copy(deep=True)
    new_state.status = ContentArchitectStatus.APPROVED
    new_state.approved = ContentArchitectApproval(
        approved_at=datetime.now(UTC).isoformat(),
        content_hash=content_hash,
    )
    return new_state


def apply_needs_attention(
    state: ContentArchitectState, error: dict[str, Any]
) -> ContentArchitectState:
    """Fail the flow with a visible error. Allowed from any non-terminal status."""
    if _is_terminal(state.status):
        raise InvalidTransitionError(
            current=state.status.value,
            target=ContentArchitectStatus.NEEDS_ATTENTION.value,
            reason="terminal status cannot fail",
        )
    new_state = state.model_copy(deep=True)
    new_state.status = ContentArchitectStatus.NEEDS_ATTENTION
    new_state.latest_error = error
    return new_state


def _merge_memory(current: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(current)
    if isinstance(update, dict):
        merged.update(update)
    return merged


def public_scope_errors(state: ContentArchitectState) -> list[str]:
    """Return deterministic completeness and publication-gate errors.

    Free-form copy remains deliberately unjudged; this verifies only that the
    pinned template can render without gaps and that no claim cleared for
    less than publication is bound to a populated public field.
    """
    page = state.page_content.model_dump(mode="json")
    claims = [claim.model_dump(mode="json") for claim in state.claim_grounding]
    return [
        *page_shape_errors(page),
        *page_completeness_errors(page),
        *claim_binding_errors(page, claims),
    ]


def _validate_transition(current: ContentArchitectStatus, target: ContentArchitectStatus) -> None:
    if current == target:
        raise InvalidTransitionError(
            current=current.value,
            target=target.value,
            reason="already in state",
        )
    if target not in _VALID_TRANSITIONS.get(current, frozenset()):
        raise InvalidTransitionError(current=current.value, target=target.value)
