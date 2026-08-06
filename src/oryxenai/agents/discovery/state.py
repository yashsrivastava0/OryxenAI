"""Discovery state machine and revision rules.

Explicit state transitions with structured conflict errors for invalid ones.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from oryxenai.agents.discovery.schemas import DiscoveryState, DiscoveryStatus


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, current: str, target: str, reason: str = "") -> None:
        self.current = current
        self.target = target
        self.reason = reason
        super().__init__(
            f"Cannot transition from '{current}' to '{target}'{': ' + reason if reason else ''}"
        )


_VALID_TRANSITIONS: dict[DiscoveryStatus, frozenset[DiscoveryStatus]] = {
    DiscoveryStatus.NOT_STARTED: frozenset({DiscoveryStatus.INPUT_READY}),
    DiscoveryStatus.INPUT_READY: frozenset({DiscoveryStatus.QUESTIONS_QUEUED}),
    DiscoveryStatus.QUESTIONS_QUEUED: frozenset({DiscoveryStatus.QUESTIONS_RUNNING}),
    DiscoveryStatus.QUESTIONS_RUNNING: frozenset(
        {DiscoveryStatus.QUESTIONS_READY, DiscoveryStatus.NEEDS_ATTENTION}
    ),
    DiscoveryStatus.QUESTIONS_READY: frozenset(
        {DiscoveryStatus.ANSWERS_IN_PROGRESS, DiscoveryStatus.INPUT_READY}
    ),
    DiscoveryStatus.ANSWERS_IN_PROGRESS: frozenset({DiscoveryStatus.ANSWERS_READY}),
    DiscoveryStatus.ANSWERS_READY: frozenset(
        {DiscoveryStatus.BRIEF_QUEUED, DiscoveryStatus.ANSWERS_IN_PROGRESS}
    ),
    DiscoveryStatus.BRIEF_QUEUED: frozenset({DiscoveryStatus.BRIEF_RUNNING}),
    DiscoveryStatus.BRIEF_RUNNING: frozenset(
        {DiscoveryStatus.BRIEF_REVIEW, DiscoveryStatus.NEEDS_ATTENTION}
    ),
    DiscoveryStatus.BRIEF_REVIEW: frozenset(
        {
            DiscoveryStatus.APPROVED,
            DiscoveryStatus.ANSWERS_READY,
            DiscoveryStatus.INPUT_READY,
            DiscoveryStatus.BRIEF_QUEUED,
        }
    ),
    DiscoveryStatus.APPROVED: frozenset(
        {DiscoveryStatus.INPUT_READY, DiscoveryStatus.ANSWERS_READY, DiscoveryStatus.BRIEF_REVIEW}
    ),
    DiscoveryStatus.NEEDS_ATTENTION: frozenset(
        {DiscoveryStatus.QUESTIONS_QUEUED, DiscoveryStatus.BRIEF_QUEUED}
    ),
}


def is_valid_transition(current: DiscoveryStatus, target: DiscoveryStatus) -> bool:
    return target in _VALID_TRANSITIONS.get(current, frozenset())


# Explicit allowed-source sets for edit/approval transitions. These are
# deliberate departures from the queue/run map above: they describe
# user-initiated edits that intentionally invalidate downstream results.
# The durable worker still guards late results with source/answer revision
# checks, so these status changes can never be silently overwritten.

# Source edits are allowed from settled states only. In-flight operations
# (queued/running) must complete or fail first, so a running worker result
# can never race a new source revision; the durable worker additionally
# guards late results with revision checks.
_SOURCE_EDIT_ALLOWED_FROM: frozenset[DiscoveryStatus] = frozenset(
    {
        DiscoveryStatus.NOT_STARTED,
        DiscoveryStatus.INPUT_READY,
        DiscoveryStatus.QUESTIONS_READY,
        DiscoveryStatus.ANSWERS_IN_PROGRESS,
        DiscoveryStatus.ANSWERS_READY,
        DiscoveryStatus.BRIEF_REVIEW,
        DiscoveryStatus.APPROVED,
        DiscoveryStatus.NEEDS_ATTENTION,
    }
)

# Editing answers after a brief exists moves back to ANSWERS_READY.
_ANSWER_EDIT_ALLOWED_FROM: frozenset[DiscoveryStatus] = frozenset(
    {DiscoveryStatus.BRIEF_REVIEW, DiscoveryStatus.APPROVED}
)

# Manual brief edits are only meaningful once a draft exists.
_BRIEF_EDIT_ALLOWED_FROM: frozenset[DiscoveryStatus] = frozenset(
    {DiscoveryStatus.BRIEF_REVIEW, DiscoveryStatus.APPROVED}
)

# Approval is only valid from a reviewable brief.
_APPROVAL_ALLOWED_FROM: frozenset[DiscoveryStatus] = frozenset({DiscoveryStatus.BRIEF_REVIEW})

# Needs-attention is only reachable from an in-flight operation.
_NEEDS_ATTENTION_ALLOWED_FROM: frozenset[DiscoveryStatus] = frozenset(
    {DiscoveryStatus.QUESTIONS_RUNNING, DiscoveryStatus.BRIEF_RUNNING}
)


def apply_source_edit(state: DiscoveryState) -> DiscoveryState:
    """Source edited — invalidate downstream state, return to input_ready.

    Allowed only from settled states. In-flight operations (queued/running)
    reject the edit; the durable worker additionally rejects late results
    via source/answer revision checks.
    """
    _validate_allowed(state.status, _SOURCE_EDIT_ALLOWED_FROM, DiscoveryStatus.INPUT_READY)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.INPUT_READY
    new_state.questions = type(new_state.questions)()
    new_state.answers = type(new_state.answers)()
    new_state.brief = type(new_state.brief)()
    new_state.latest_error = None
    _invalidate_approval(new_state)
    return new_state


def apply_answer_edit(state: DiscoveryState) -> DiscoveryState:
    """Answers edited — mark brief stale, invalidate approval."""
    _validate_allowed(state.status, _ANSWER_EDIT_ALLOWED_FROM, DiscoveryStatus.ANSWERS_READY)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.ANSWERS_READY
    new_state.brief.generated_from_answer_revision = None
    _invalidate_approval(new_state)
    return new_state


def apply_brief_edit(state: DiscoveryState) -> DiscoveryState:
    """Manual brief edit — increment revision, invalidate approval."""
    _validate_allowed(state.status, _BRIEF_EDIT_ALLOWED_FROM, DiscoveryStatus.BRIEF_REVIEW)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.BRIEF_REVIEW
    new_state.brief.version += 1
    _invalidate_approval(new_state)
    return new_state


def apply_approval(state: DiscoveryState, approval_details: dict[str, Any]) -> DiscoveryState:
    """Create immutable approved snapshot."""
    from oryxenai.agents.discovery.schemas import DiscoveryApproval

    _validate_allowed(state.status, _APPROVAL_ALLOWED_FROM, DiscoveryStatus.APPROVED)

    now = datetime.now(UTC).isoformat()
    brief_draft = state.brief.draft
    brief_json = brief_draft.model_dump_json() if brief_draft else "{}"
    brief_hash = _compute_hash(brief_json)

    approval = DiscoveryApproval(
        approved_at=now,
        session_identity=approval_details.get("session_identity"),
        brief_version=state.brief.version,
        brief_hash=brief_hash,
        source_revision=state.source_revision,
        answer_revision=state.answers.revision,
        run_provenance=approval_details.get("run_provenance", {}),
    )

    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.APPROVED
    new_state.brief.approved = approval
    new_state.brief.approved_brief = brief_draft.model_copy(deep=True) if brief_draft else None
    return new_state


def apply_questions_queued(state: DiscoveryState, run_id: str, job_id: str) -> DiscoveryState:
    _validate_transition(state.status, DiscoveryStatus.QUESTIONS_QUEUED)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.QUESTIONS_QUEUED
    new_state.questions.run_id = run_id
    new_state.questions.job_id = job_id
    return new_state


def apply_questions_running(state: DiscoveryState) -> DiscoveryState:
    _validate_transition(state.status, DiscoveryStatus.QUESTIONS_RUNNING)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.QUESTIONS_RUNNING
    return new_state


def apply_questions_ready(
    state: DiscoveryState,
    questions: list[Any],
    run_id: str,
    source_revision: int,
) -> DiscoveryState:
    _validate_transition(state.status, DiscoveryStatus.QUESTIONS_READY)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.QUESTIONS_READY
    new_state.questions.version += 1
    new_state.questions.run_id = run_id
    new_state.questions.generated_from_source_revision = source_revision
    new_state.questions.items = questions
    new_state.latest_error = None
    return new_state


def apply_answers_in_progress(state: DiscoveryState) -> DiscoveryState:
    _validate_transition(state.status, DiscoveryStatus.ANSWERS_IN_PROGRESS)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.ANSWERS_IN_PROGRESS
    return new_state


def apply_answers_ready(state: DiscoveryState, answers: dict[str, Any]) -> DiscoveryState:
    _validate_transition(state.status, DiscoveryStatus.ANSWERS_READY)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.ANSWERS_READY
    new_state.answers.revision += 1
    new_state.answers.items = answers
    _mark_brief_stale(new_state)
    _invalidate_approval(new_state)
    return new_state


def apply_brief_queued(state: DiscoveryState, run_id: str, job_id: str) -> DiscoveryState:
    _validate_transition(state.status, DiscoveryStatus.BRIEF_QUEUED)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.BRIEF_QUEUED
    new_state.brief.run_id = run_id
    new_state.brief.job_id = job_id
    return new_state


def apply_brief_running(state: DiscoveryState) -> DiscoveryState:
    _validate_transition(state.status, DiscoveryStatus.BRIEF_RUNNING)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.BRIEF_RUNNING
    return new_state


def apply_brief_review(state: DiscoveryState, brief: Any, run_id: str) -> DiscoveryState:
    _validate_transition(state.status, DiscoveryStatus.BRIEF_REVIEW)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.BRIEF_REVIEW
    new_state.brief.version += 1
    new_state.brief.run_id = run_id
    new_state.brief.draft = brief
    new_state.latest_error = None
    return new_state


def apply_needs_attention(state: DiscoveryState, error: Any) -> DiscoveryState:
    from oryxenai.agents.discovery.schemas import DiscoveryWarning

    _validate_allowed(state.status, _NEEDS_ATTENTION_ALLOWED_FROM, DiscoveryStatus.NEEDS_ATTENTION)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.NEEDS_ATTENTION
    if isinstance(error, DiscoveryWarning):
        new_state.latest_error = error
    elif isinstance(error, dict):
        new_state.latest_error = DiscoveryWarning(**error)
    return new_state


def invalidate_approval(state: DiscoveryState) -> DiscoveryState:
    """Explicitly invalidate approval."""
    return _invalidate_approval(state.model_copy(deep=True))


# ── Helpers ──────────────────────────────────────────────────────────────────


def _validate_transition(current: DiscoveryStatus, target: DiscoveryStatus) -> None:
    if not is_valid_transition(current, target):
        raise InvalidTransitionError(
            current=current.value,
            target=target.value,
        )


def _validate_allowed(
    current: DiscoveryStatus,
    allowed_from: frozenset[DiscoveryStatus],
    target: DiscoveryStatus,
) -> None:
    if current not in allowed_from:
        raise InvalidTransitionError(
            current=current.value,
            target=target.value,
            reason="operation not allowed from this state",
        )


def _invalidate_approval(state: DiscoveryState) -> DiscoveryState:
    state.brief.approved = None
    return state


def _mark_brief_stale(state: DiscoveryState) -> None:
    state.brief.generated_from_answer_revision = None


def _compute_hash(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()
