"""Content Architect state machine.

Five statuses, one linear flow — deliberately simpler than Discovery's own
two-operation machine because Content Architect runs as a single durable job
(`content_architect.build`) whose agent makes up to 3 model calls internally.
There is no separate queued/running pair per stage, and no per-stage status,
because only one job kind ever writes this state.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from oryxenai.agents.content_architect.schemas import (
    ClaimGrounding,
    ContentArchitectApproval,
    ContentArchitectIntake,
    ContentArchitectPreferences,
    ContentArchitectSourceRef,
    ContentArchitectState,
    ContentArchitectStatus,
    DecisionRecord,
    PageContentPack,
    PublicationStatus,
    RoutePlanEntry,
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


class NoPublishableRoutesError(ValueError):
    """Approval attempted with no route cleared for public output.

    `publication_status` is a first-class, cross-agent gating invariant: a
    Content Architect run may plan `pending`/`blocked` content (it still gets
    written, just gated), but APPROVED state must always carry at least one
    route the model cleared for publication. Build Preparation's v2 pack
    contract relies on this precondition downstream, so the state machine is
    the authoritative place to refuse approval when it would otherwise produce
    a state with zero publishable routes.
    """

    def __init__(
        self,
        *,
        route_statuses: dict[str, str],
        route_count: int,
        message: str = "",
    ) -> None:
        self.route_statuses = route_statuses
        self.route_count = route_count
        self.message = message or (
            "Cannot approve: no publishable routes. At least one route_plan "
            "entry must have publication_status 'approved'."
        )
        super().__init__(self.message)


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
    site_story_strategy: dict[str, Any],
    decision_basis: list[DecisionRecord],
    route_plan: list[RoutePlanEntry],
    page_content_packs: list[PageContentPack],
    public_content_manifest: dict[str, Any],
    claim_grounding: list[ClaimGrounding],
    omissions: list[str],
    unresolved_issues: list[str],
    privacy_and_confidentiality: list[str],
    media_status: dict[str, Any],
    visual_director_handoff: dict[str, Any],
    warnings: list[str],
    stages_run: list[str],
    memory_update: dict[str, Any],
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
    new_state.route_plan = route_plan
    new_state.page_content_packs = page_content_packs
    new_state.public_content_manifest = public_content_manifest
    new_state.claim_grounding = claim_grounding
    new_state.omissions = omissions
    new_state.unresolved_issues = unresolved_issues
    new_state.privacy_and_confidentiality = privacy_and_confidentiality
    new_state.media_status = media_status
    new_state.visual_director_handoff = visual_director_handoff
    new_state.warnings = warnings
    new_state.stages_run = stages_run
    new_state.memory = _merge_memory(state.memory, memory_update)
    new_state.latest_error = None
    return new_state


def apply_approval(state: ContentArchitectState, content_hash: str) -> ContentArchitectState:
    _validate_transition(state.status, ContentArchitectStatus.APPROVED)
    if not any(
        route.publication_status == PublicationStatus.APPROVED for route in state.route_plan
    ):
        raise NoPublishableRoutesError(
            route_statuses={
                route.route_id: str(route.publication_status) for route in state.route_plan
            },
            route_count=len(state.route_plan),
        )
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


def _validate_transition(current: ContentArchitectStatus, target: ContentArchitectStatus) -> None:
    if current == target:
        raise InvalidTransitionError(
            current=current.value,
            target=target.value,
            reason="already in state",
        )
    if target not in _VALID_TRANSITIONS.get(current, frozenset()):
        raise InvalidTransitionError(current=current.value, target=target.value)
