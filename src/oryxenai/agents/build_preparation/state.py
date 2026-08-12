"""Build Preparation state machine."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    BuildPreparationSourceRef,
    BuildPreparationState,
    BuildPreparationStatus,
    FetchedResource,
    MaterializationResult,
    PackageResult,
    ResourceNeed,
    RouteScope,
    Stage1QueryPlan,
    Stage2SelectionPlan,
    StageEvent,
)


class InvalidTransitionError(Exception):
    def __init__(self, current: str, target: str, reason: str = "") -> None:
        self.current = current
        self.target = target
        self.reason = reason
        suffix = f": {reason}" if reason else ""
        super().__init__(f"Cannot transition from '{current}' to '{target}'{suffix}")


_VALID_TRANSITIONS: dict[BuildPreparationStatus, frozenset[BuildPreparationStatus]] = {
    BuildPreparationStatus.NOT_STARTED: frozenset({BuildPreparationStatus.RUNNING}),
    BuildPreparationStatus.RUNNING: frozenset(
        {BuildPreparationStatus.READY, BuildPreparationStatus.NEEDS_ATTENTION}
    ),
    BuildPreparationStatus.NEEDS_ATTENTION: frozenset({BuildPreparationStatus.RUNNING}),
    BuildPreparationStatus.READY: frozenset(),
}


def is_valid_transition(current: BuildPreparationStatus, target: BuildPreparationStatus) -> bool:
    return current != target and target in _VALID_TRANSITIONS.get(current, frozenset())


def apply_start(
    state: BuildPreparationState,
    *,
    source_ref: BuildPreparationSourceRef,
    model_profile: str,
    max_attempts: int,
) -> BuildPreparationState:
    if state.status not in {
        BuildPreparationStatus.NOT_STARTED,
        BuildPreparationStatus.NEEDS_ATTENTION,
    }:
        raise InvalidTransitionError(state.status.value, BuildPreparationStatus.RUNNING.value)
    next_state = state.model_copy(deep=True)
    next_state.status = BuildPreparationStatus.RUNNING
    next_state.model_profile = model_profile
    next_state.source_ref = source_ref
    next_state.run_id = ""
    next_state.job_id = ""
    next_state.scope_hash = ""
    next_state.routes = []
    next_state.resource_needs = []
    next_state.current_stage = "stage_0"
    next_state.query_plan = None
    next_state.fetched_candidates = []
    next_state.selection_plan = None
    next_state.build_context = None
    next_state.materialization = None
    next_state.package = None
    next_state.model_calls = 0
    next_state.provider_calls = 0
    next_state.manifest_path = ""
    next_state.warnings = []
    next_state.events = []
    next_state.latest_error = None
    next_state.completed_at = None
    next_state.max_attempts = max_attempts
    if not next_state.started_at:
        next_state.started_at = datetime.now(UTC).isoformat()
    return next_state


def reset_for_regeneration(state: BuildPreparationState) -> BuildPreparationState:
    if state.status not in {
        BuildPreparationStatus.READY,
        BuildPreparationStatus.NEEDS_ATTENTION,
    }:
        raise InvalidTransitionError(
            state.status.value,
            BuildPreparationStatus.NOT_STARTED.value,
            "regeneration is only available after a completed or failed run",
        )
    # Keep a monotonic generation number so a new run cannot reuse the
    # idempotency key of a completed or exhausted run for the same upstream
    # projections.
    return BuildPreparationState(
        model_profile=state.model_profile,
        max_attempts=state.max_attempts,
        attempt=state.attempt + 1,
    )


def apply_build_running(
    state: BuildPreparationState, run_id: str, job_id: str, attempt: int, max_attempts: int
) -> BuildPreparationState:
    next_state = state.model_copy(deep=True)
    if next_state.status != BuildPreparationStatus.RUNNING:
        if not is_valid_transition(next_state.status, BuildPreparationStatus.RUNNING):
            raise InvalidTransitionError(
                next_state.status.value, BuildPreparationStatus.RUNNING.value
            )
        next_state.status = BuildPreparationStatus.RUNNING
    next_state.run_id = run_id
    next_state.job_id = job_id
    next_state.attempt = attempt
    next_state.max_attempts = max_attempts
    return next_state


def apply_result(
    state: BuildPreparationState,
    *,
    scope_hash: str,
    routes: list[RouteScope],
    resource_needs: list[ResourceNeed],
    warnings: list[str],
    events: list[StageEvent],
) -> BuildPreparationState:
    if not is_valid_transition(state.status, BuildPreparationStatus.READY):
        raise InvalidTransitionError(state.status.value, BuildPreparationStatus.READY.value)
    next_state = state.model_copy(deep=True)
    next_state.status = BuildPreparationStatus.READY
    next_state.current_stage = "stage_0"
    next_state.scope_hash = scope_hash
    next_state.routes = routes
    next_state.resource_needs = resource_needs
    next_state.warnings = warnings
    next_state.events = events
    next_state.latest_error = None
    next_state.completed_at = datetime.now(UTC).isoformat()
    return next_state


def apply_phase2_result(
    state: BuildPreparationState,
    *,
    scope_hash: str,
    routes: list[RouteScope],
    resource_needs: list[ResourceNeed],
    query_plan: Stage1QueryPlan,
    fetched_candidates: list[FetchedResource],
    selection_plan: Stage2SelectionPlan,
    build_context: BuildContextDraft,
    materialization: MaterializationResult,
    warnings: list[str],
    events: list[StageEvent],
    model_calls: int,
    provider_calls: int,
) -> BuildPreparationState:
    """Apply a complete Stage 0 through Phase 2 result atomically."""
    if not is_valid_transition(state.status, BuildPreparationStatus.READY):
        raise InvalidTransitionError(state.status.value, BuildPreparationStatus.READY.value)
    next_state = state.model_copy(deep=True)
    next_state.status = BuildPreparationStatus.READY
    next_state.current_stage = "phase_2"
    next_state.scope_hash = scope_hash
    next_state.routes = routes
    next_state.resource_needs = resource_needs
    next_state.query_plan = query_plan
    next_state.fetched_candidates = fetched_candidates
    next_state.selection_plan = selection_plan
    next_state.build_context = build_context
    next_state.materialization = materialization
    next_state.package = None
    next_state.manifest_path = materialization.manifest_path
    next_state.warnings = warnings
    next_state.events = events
    next_state.model_calls = model_calls
    next_state.provider_calls = provider_calls
    next_state.latest_error = None
    next_state.completed_at = datetime.now(UTC).isoformat()
    return next_state


def apply_phase3_result(
    state: BuildPreparationState,
    *,
    scope_hash: str,
    routes: list[RouteScope],
    resource_needs: list[ResourceNeed],
    query_plan: Stage1QueryPlan,
    fetched_candidates: list[FetchedResource],
    selection_plan: Stage2SelectionPlan,
    build_context: BuildContextDraft,
    materialization: MaterializationResult,
    package: PackageResult,
    warnings: list[str],
    events: list[StageEvent],
    model_calls: int,
    provider_calls: int,
) -> BuildPreparationState:
    """Apply only after packaging, storage verification, and mirror restore succeed."""
    if not is_valid_transition(state.status, BuildPreparationStatus.READY):
        raise InvalidTransitionError(state.status.value, BuildPreparationStatus.READY.value)
    next_state = state.model_copy(deep=True)
    next_state.status = BuildPreparationStatus.READY
    next_state.current_stage = "phase_3"
    next_state.scope_hash = scope_hash
    next_state.routes = routes
    next_state.resource_needs = resource_needs
    next_state.query_plan = query_plan
    next_state.fetched_candidates = fetched_candidates
    next_state.selection_plan = selection_plan
    next_state.build_context = build_context
    next_state.materialization = materialization
    next_state.package = package
    next_state.manifest_path = package.manifest_path
    next_state.warnings = warnings
    next_state.events = events
    next_state.model_calls = model_calls
    next_state.provider_calls = provider_calls
    next_state.latest_error = None
    next_state.completed_at = datetime.now(UTC).isoformat()
    return next_state


def apply_needs_attention(
    state: BuildPreparationState, error: dict[str, Any]
) -> BuildPreparationState:
    if state.status == BuildPreparationStatus.READY:
        raise InvalidTransitionError(
            state.status.value,
            BuildPreparationStatus.NEEDS_ATTENTION.value,
            "a ready result cannot be overwritten by a failure",
        )
    next_state = state.model_copy(deep=True)
    next_state.status = BuildPreparationStatus.NEEDS_ATTENTION
    next_state.latest_error = dict(error)
    next_state.completed_at = datetime.now(UTC).isoformat()
    return next_state
