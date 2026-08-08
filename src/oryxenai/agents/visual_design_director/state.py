"""Visual Design Director state machine.

Five statuses, one linear flow — deliberately simpler than Discovery's own
two-operation machine because Visual Design Director runs as a single
durable job (`visual_design_director.build`) whose agent makes up to 3 model
calls internally. There is no separate queued/running pair per stage, and no
per-stage status, because only one job kind ever writes this state. Mirrors
Content Architect's state.py exactly, renamed for this stage.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from oryxenai.agents.visual_design_director.schemas import (
    AssetBrief,
    PageVisualDirection,
    ResourceCandidate,
    VisualDesignDirectorApproval,
    VisualDesignDirectorIntake,
    VisualDesignDirectorPreferences,
    VisualDesignDirectorSourceRef,
    VisualDesignDirectorState,
    VisualDesignDirectorStatus,
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


_TERMINAL = frozenset({VisualDesignDirectorStatus.APPROVED})


def _is_terminal(status: VisualDesignDirectorStatus) -> bool:
    return status in _TERMINAL


_VALID_TRANSITIONS: dict[VisualDesignDirectorStatus, frozenset[VisualDesignDirectorStatus]] = {
    VisualDesignDirectorStatus.NOT_STARTED: frozenset({VisualDesignDirectorStatus.BUILD_RUNNING}),
    VisualDesignDirectorStatus.BUILD_RUNNING: frozenset(
        {VisualDesignDirectorStatus.DESIGN_REVIEW, VisualDesignDirectorStatus.NEEDS_ATTENTION}
    ),
    VisualDesignDirectorStatus.DESIGN_REVIEW: frozenset(
        {VisualDesignDirectorStatus.APPROVED, VisualDesignDirectorStatus.BUILD_RUNNING}
    ),
    VisualDesignDirectorStatus.NEEDS_ATTENTION: frozenset(
        {VisualDesignDirectorStatus.BUILD_RUNNING}
    ),
}


def is_valid_transition(
    current: VisualDesignDirectorStatus, target: VisualDesignDirectorStatus
) -> bool:
    return current != target and target in _VALID_TRANSITIONS.get(current, frozenset())


def apply_start(
    state: VisualDesignDirectorState,
    *,
    source_ref: VisualDesignDirectorSourceRef,
    intake: VisualDesignDirectorIntake,
    preferences: VisualDesignDirectorPreferences,
) -> VisualDesignDirectorState:
    """Start (or restart from NEEDS_ATTENTION) a Visual Design Director build."""
    _validate_transition(state.status, VisualDesignDirectorStatus.BUILD_RUNNING)
    new_state = state.model_copy(deep=True)
    new_state.status = VisualDesignDirectorStatus.BUILD_RUNNING
    new_state.source_ref = source_ref
    new_state.intake = intake
    new_state.preferences = preferences
    if not new_state.started_at:
        new_state.started_at = datetime.now(UTC).isoformat()
    new_state.latest_error = None
    return new_state


def apply_build_running(
    state: VisualDesignDirectorState, run_id: str, job_id: str
) -> VisualDesignDirectorState:
    """Idempotent re-entry helper for the job handler.

    Mostly a no-op when the service already set BUILD_RUNNING before the job
    was claimed; matters for the retry-from-NEEDS_ATTENTION recovery path.
    """
    new_state = state.model_copy(deep=True)
    if new_state.status != VisualDesignDirectorStatus.BUILD_RUNNING:
        _validate_transition(state.status, VisualDesignDirectorStatus.BUILD_RUNNING)
        new_state.status = VisualDesignDirectorStatus.BUILD_RUNNING
    new_state.run_id = run_id
    new_state.job_id = job_id
    return new_state


def apply_revision_requested(
    state: VisualDesignDirectorState,
    run_id: str,
    job_id: str,
    revision_request: str,
) -> VisualDesignDirectorState:
    """Re-run the build pipeline from DESIGN_REVIEW with a revision request."""
    _validate_transition(state.status, VisualDesignDirectorStatus.BUILD_RUNNING)
    new_state = state.model_copy(deep=True)
    new_state.status = VisualDesignDirectorStatus.BUILD_RUNNING
    new_state.run_id = run_id
    new_state.job_id = job_id
    new_state.revision_request = revision_request
    return new_state


def apply_build_result(
    state: VisualDesignDirectorState,
    *,
    version: str,
    run_id: str,
    user_summary: str,
    meta: dict[str, Any],
    source_refs: dict[str, Any],
    visual_language: dict[str, Any],
    shared_visual_systems: dict[str, Any],
    navigation_direction: dict[str, Any],
    motion_system: dict[str, Any],
    interaction_system: dict[str, Any],
    pages: list[PageVisualDirection],
    asset_briefs: list[AssetBrief],
    resource_candidates: list[ResourceCandidate],
    accessibility_and_performance: dict[str, Any],
    must_preserve: list[str],
    must_not_fabricate: list[str],
    conflicts: list[str],
    warnings: list[str],
    compiler_handoff: dict[str, Any],
    stages_run: list[str],
    memory_update: dict[str, Any],
) -> VisualDesignDirectorState:
    """Persist a successful build result and move to DESIGN_REVIEW."""
    _validate_transition(state.status, VisualDesignDirectorStatus.DESIGN_REVIEW)
    new_state = state.model_copy(deep=True)
    new_state.status = VisualDesignDirectorStatus.DESIGN_REVIEW
    new_state.version = version
    new_state.run_id = run_id
    new_state.user_summary = user_summary
    new_state.meta = meta
    new_state.source_refs = source_refs
    new_state.visual_language = visual_language
    new_state.shared_visual_systems = shared_visual_systems
    new_state.navigation_direction = navigation_direction
    new_state.motion_system = motion_system
    new_state.interaction_system = interaction_system
    new_state.pages = pages
    new_state.asset_briefs = asset_briefs
    new_state.resource_candidates = resource_candidates
    new_state.accessibility_and_performance = accessibility_and_performance
    new_state.must_preserve = must_preserve
    new_state.must_not_fabricate = must_not_fabricate
    new_state.conflicts = conflicts
    new_state.warnings = warnings
    new_state.compiler_handoff = compiler_handoff
    new_state.stages_run = stages_run
    new_state.memory = _merge_memory(state.memory, memory_update)
    new_state.latest_error = None
    return new_state


def apply_approval(
    state: VisualDesignDirectorState, visual_direction_hash: str
) -> VisualDesignDirectorState:
    _validate_transition(state.status, VisualDesignDirectorStatus.APPROVED)
    new_state = state.model_copy(deep=True)
    new_state.status = VisualDesignDirectorStatus.APPROVED
    new_state.approved = VisualDesignDirectorApproval(
        approved_at=datetime.now(UTC).isoformat(),
        visual_direction_hash=visual_direction_hash,
    )
    return new_state


def apply_needs_attention(
    state: VisualDesignDirectorState, error: dict[str, Any]
) -> VisualDesignDirectorState:
    """Fail the flow with a visible error. Allowed from any non-terminal status."""
    if _is_terminal(state.status):
        raise InvalidTransitionError(
            current=state.status.value,
            target=VisualDesignDirectorStatus.NEEDS_ATTENTION.value,
            reason="terminal status cannot fail",
        )
    new_state = state.model_copy(deep=True)
    new_state.status = VisualDesignDirectorStatus.NEEDS_ATTENTION
    new_state.latest_error = error
    return new_state


def _merge_memory(current: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(current)
    if isinstance(update, dict):
        merged.update(update)
    return merged


def _validate_transition(
    current: VisualDesignDirectorStatus, target: VisualDesignDirectorStatus
) -> None:
    if current == target:
        raise InvalidTransitionError(
            current=current.value,
            target=target.value,
            reason="already in state",
        )
    if target not in _VALID_TRANSITIONS.get(current, frozenset()):
        raise InvalidTransitionError(current=current.value, target=target.value)
