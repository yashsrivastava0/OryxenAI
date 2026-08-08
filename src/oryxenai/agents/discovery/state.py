"""Discovery state machine.

Linear flow with a single transition map and one error state.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from oryxenai.agents.discovery.schemas import (
    DiscoveryQuestion,
    DiscoveryState,
    DiscoveryStatus,
    OperationAState,
    OperationMode,
    StructuredProfile,
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


_TERMINAL = frozenset({DiscoveryStatus.APPROVED})


def _is_terminal(status: DiscoveryStatus) -> bool:
    return status in _TERMINAL


_VALID_TRANSITIONS: dict[DiscoveryStatus, frozenset[DiscoveryStatus]] = {
    DiscoveryStatus.NOT_STARTED: frozenset({DiscoveryStatus.QUESTIONS_QUEUED}),
    DiscoveryStatus.QUESTIONS_QUEUED: frozenset({DiscoveryStatus.QUESTIONS_RUNNING}),
    DiscoveryStatus.QUESTIONS_RUNNING: frozenset(
        {DiscoveryStatus.QUESTIONS_READY, DiscoveryStatus.NEEDS_ATTENTION}
    ),
    DiscoveryStatus.QUESTIONS_READY: frozenset(
        {DiscoveryStatus.QUESTIONS_QUEUED, DiscoveryStatus.ANSWERS_IN_PROGRESS}
    ),
    DiscoveryStatus.ANSWERS_IN_PROGRESS: frozenset({DiscoveryStatus.BRIEF_RUNNING}),
    DiscoveryStatus.BRIEF_RUNNING: frozenset(
        {DiscoveryStatus.BRIEF_REVIEW, DiscoveryStatus.NEEDS_ATTENTION}
    ),
    DiscoveryStatus.BRIEF_REVIEW: frozenset(
        {DiscoveryStatus.APPROVED, DiscoveryStatus.BRIEF_RUNNING}
    ),
    DiscoveryStatus.NEEDS_ATTENTION: frozenset(
        {
            DiscoveryStatus.QUESTIONS_QUEUED,
            DiscoveryStatus.ANSWERS_IN_PROGRESS,
            DiscoveryStatus.BRIEF_RUNNING,
        }
    ),
}


def is_valid_transition(current: DiscoveryStatus, target: DiscoveryStatus) -> bool:
    return current != target and target in _VALID_TRANSITIONS.get(current, frozenset())


def apply_start(state: DiscoveryState) -> DiscoveryState:
    """Start the discovery flow and enqueue the questions job."""
    _validate_transition(state.status, DiscoveryStatus.QUESTIONS_QUEUED)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.QUESTIONS_QUEUED
    if not new_state.started_at:
        new_state.started_at = datetime.now(UTC).isoformat()
    new_state.latest_error = None
    return new_state


def apply_questions_running(state: DiscoveryState) -> DiscoveryState:
    _validate_transition(state.status, DiscoveryStatus.QUESTIONS_RUNNING)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.QUESTIONS_RUNNING
    return new_state


def apply_questions_ready(
    state: DiscoveryState,
    *,
    items: list[DiscoveryQuestion],
    version: str,
    run_id: str,
    mode: OperationMode,
    assistant_message: str,
    memory_update: dict[str, Any],
) -> DiscoveryState:
    _validate_transition(state.status, DiscoveryStatus.QUESTIONS_READY)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.QUESTIONS_READY
    new_state.operation_a = OperationAState(
        version=version,
        run_id=run_id,
        job_id=state.operation_a.job_id,
        mode=mode,
        assistant_message=assistant_message,
        items=items,
        memory_update=memory_update,
    )
    new_state.memory = _merge_memory(state.memory, memory_update)
    new_state.latest_error = None
    return new_state


def apply_answers_in_progress(state: DiscoveryState) -> DiscoveryState:
    _validate_transition(state.status, DiscoveryStatus.ANSWERS_IN_PROGRESS)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.ANSWERS_IN_PROGRESS
    return new_state


def apply_brief_running(state: DiscoveryState, run_id: str, job_id: str) -> DiscoveryState:
    _validate_transition(state.status, DiscoveryStatus.BRIEF_RUNNING)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.BRIEF_RUNNING
    new_state.brief.run_id = run_id
    new_state.brief.job_id = job_id
    return new_state


def apply_brief_review(
    state: DiscoveryState,
    *,
    version: str,
    run_id: str,
    title: str,
    markdown: str,
    open_items: list[str],
    memory_update: dict[str, Any],
    revision_request: str = "",
    user_summary: str = "",
    profile: dict[str, Any] | None = None,
) -> DiscoveryState:
    _validate_transition(state.status, DiscoveryStatus.BRIEF_REVIEW)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.BRIEF_REVIEW
    new_state.brief.version = version
    new_state.brief.run_id = run_id
    new_state.brief.title = title
    new_state.brief.markdown = markdown
    new_state.brief.user_summary = user_summary
    new_state.brief.profile = StructuredProfile.model_validate(profile or {})
    new_state.brief.open_items = open_items
    new_state.brief.memory_update = memory_update
    new_state.brief.revision_request = revision_request
    new_state.memory = _merge_memory(state.memory, memory_update)
    new_state.latest_error = None
    return new_state


def apply_approval(state: DiscoveryState, brief_hash: str) -> DiscoveryState:
    from oryxenai.agents.discovery.schemas import DiscoveryApproval

    _validate_transition(state.status, DiscoveryStatus.APPROVED)
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.APPROVED
    new_state.brief.approved = DiscoveryApproval(
        approved_at=datetime.now(UTC).isoformat(),
        brief_hash=brief_hash,
    )
    return new_state


def apply_needs_attention(state: DiscoveryState, error: dict[str, Any]) -> DiscoveryState:
    """Fail the flow with a visible error. Allowed from any non-terminal status."""
    if _is_terminal(state.status):
        raise InvalidTransitionError(
            current=state.status.value,
            target=DiscoveryStatus.NEEDS_ATTENTION.value,
            reason="terminal status cannot fail",
        )
    new_state = state.model_copy(deep=True)
    new_state.status = DiscoveryStatus.NEEDS_ATTENTION
    new_state.latest_error = error
    return new_state


def _merge_memory(current: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(current)
    if isinstance(update, dict):
        merged.update(update)
    return merged


def _validate_transition(current: DiscoveryStatus, target: DiscoveryStatus) -> None:
    if current == target:
        raise InvalidTransitionError(
            current=current.value,
            target=target.value,
            reason="already in state",
        )
    if target not in _VALID_TRANSITIONS.get(current, frozenset()):
        raise InvalidTransitionError(current=current.value, target=target.value)
