"""Code Generator control-plane state: ``current_state['code_generator']``.

This is the only place that decides *which* page is live and whether a build is
in flight; versions and the chat transcript live in their own tables. Transitions
are pure functions (the service/handler persist them with the session-revision
compare-and-swap, exactly like Content Architect).

Four statuses:

* ``not_started``     - nothing was ever built.
* ``build_running``   - ``in_flight`` names the run, job and version being built.
* ``ready``           - ``active_version_id`` is the verified live page. A failed
                        later attempt keeps this status and records ``last_error``.
* ``needs_attention`` - the first build failed; ``last_error`` says exactly why.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from oryxenai.agents.code_generator.schemas import FailureEnvelope


class CodeGeneratorStatus(StrEnum):
    NOT_STARTED = "not_started"
    BUILD_RUNNING = "build_running"
    READY = "ready"
    NEEDS_ATTENTION = "needs_attention"


class InvalidTransitionError(Exception):
    """A state change that the state machine does not allow."""

    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Cannot move the page builder from '{current}' to '{target}'.")


class CodeGeneratorSourceRef(BaseModel):
    """The approved Content Architect result this site was started from."""

    model_config = ConfigDict(extra="ignore")

    content_hash: str = ""
    snapshotted_at: str = ""


class InFlightBuild(BaseModel):
    """The one build that is currently running (or waiting for a worker)."""

    model_config = ConfigDict(extra="ignore")

    run_id: str
    job_id: str
    version_id: str
    origin: Literal["initial", "retry", "change"] = "initial"
    instruction: str = ""
    base_version_id: str = ""
    started_at: str = ""


class CodeGeneratorState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: CodeGeneratorStatus = CodeGeneratorStatus.NOT_STARTED
    theme_id: str = ""
    source_ref: CodeGeneratorSourceRef = Field(default_factory=CodeGeneratorSourceRef)
    active_version_id: str = ""
    active_version_number: int = 0
    in_flight: InFlightBuild | None = None
    last_error: dict[str, Any] | None = None
    builds_started: int = 0
    routing_policy_version: str = ""
    routing_policy_fingerprint: str = ""
    started_at: str | None = None
    updated_at: str | None = None


_VERSION_NAMESPACE = uuid5(NAMESPACE_URL, "https://oryxenai.local/code-generator/site-version")


def version_id_for_run(run_id: UUID | str) -> UUID:
    """Deterministic version id: a redelivered run can never create a second row."""
    return uuid5(_VERSION_NAMESPACE, str(run_id))


def parse_code_generator_state(raw: object) -> CodeGeneratorState:
    """Read ``current_state['code_generator']``, tolerating the retired generator's leftovers.

    Sessions created before the Studio may carry a state written by the earlier,
    retired generator (for example ``status: "queued"`` with its own fields). Such
    a value is not this feature's state: it reads as "not started" and is replaced
    when a build starts. It never raises.
    """
    if not isinstance(raw, dict):
        return CodeGeneratorState()
    try:
        return CodeGeneratorState.model_validate(raw)
    except ValidationError:
        return CodeGeneratorState()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _allowed(current: CodeGeneratorStatus, target: CodeGeneratorStatus) -> bool:
    if current is target:
        return False
    table: dict[CodeGeneratorStatus, frozenset[CodeGeneratorStatus]] = {
        CodeGeneratorStatus.NOT_STARTED: frozenset({CodeGeneratorStatus.BUILD_RUNNING}),
        CodeGeneratorStatus.BUILD_RUNNING: frozenset(
            {CodeGeneratorStatus.READY, CodeGeneratorStatus.NEEDS_ATTENTION}
        ),
        CodeGeneratorStatus.READY: frozenset({CodeGeneratorStatus.BUILD_RUNNING}),
        CodeGeneratorStatus.NEEDS_ATTENTION: frozenset({CodeGeneratorStatus.BUILD_RUNNING}),
    }
    return target in table.get(current, frozenset())


def _require(state: CodeGeneratorState, target: CodeGeneratorStatus) -> None:
    if not _allowed(state.status, target):
        raise InvalidTransitionError(state.status.value, target.value)


def apply_build_started(
    state: CodeGeneratorState,
    *,
    in_flight: InFlightBuild,
    source_ref: CodeGeneratorSourceRef,
    theme_id: str,
    routing_policy_version: str = "",
    routing_policy_fingerprint: str = "",
) -> CodeGeneratorState:
    """Begin a build (first build, a retry after failure, or a later change)."""
    _require(state, CodeGeneratorStatus.BUILD_RUNNING)
    new = state.model_copy(deep=True)
    new.status = CodeGeneratorStatus.BUILD_RUNNING
    new.in_flight = in_flight
    new.source_ref = source_ref
    new.theme_id = theme_id
    new.last_error = None
    new.builds_started = state.builds_started + 1
    new.routing_policy_version = routing_policy_version
    new.routing_policy_fingerprint = routing_policy_fingerprint
    new.started_at = new.started_at or _now()
    new.updated_at = _now()
    return new


def apply_build_succeeded(
    state: CodeGeneratorState, *, version_id: str, version_number: int
) -> CodeGeneratorState:
    """The in-flight version was verified: it becomes the live page."""
    _require(state, CodeGeneratorStatus.READY)
    new = state.model_copy(deep=True)
    new.status = CodeGeneratorStatus.READY
    new.active_version_id = version_id
    new.active_version_number = version_number
    new.in_flight = None
    new.last_error = None
    new.updated_at = _now()
    return new


def apply_reply_only(state: CodeGeneratorState) -> CodeGeneratorState:
    """A chat request needed no new page (a reply, a question, a refusal): back to ready."""
    if not state.active_version_id:
        raise InvalidTransitionError(state.status.value, CodeGeneratorStatus.READY.value)
    _require(state, CodeGeneratorStatus.READY)
    new = state.model_copy(deep=True)
    new.status = CodeGeneratorStatus.READY
    new.in_flight = None
    new.last_error = None
    new.updated_at = _now()
    return new


def apply_restored(
    state: CodeGeneratorState, *, version_id: str, version_number: int
) -> CodeGeneratorState:
    """An earlier verified page was made live again (no build, no model)."""
    if state.status is not CodeGeneratorStatus.READY or state.in_flight is not None:
        raise InvalidTransitionError(state.status.value, CodeGeneratorStatus.READY.value)
    new = state.model_copy(deep=True)
    new.active_version_id = version_id
    new.active_version_number = version_number
    new.last_error = None
    new.updated_at = _now()
    return new


def apply_build_failed(state: CodeGeneratorState, envelope: FailureEnvelope) -> CodeGeneratorState:
    """The in-flight build failed: keep the live page (if any) and say why.

    A failure never replaces the page the user already has. With no live page the
    session needs attention; with one it stays ``ready`` and carries ``last_error``.
    """
    target = (
        CodeGeneratorStatus.READY
        if state.active_version_id
        else CodeGeneratorStatus.NEEDS_ATTENTION
    )
    _require(state, target)
    new = state.model_copy(deep=True)
    new.status = target
    new.in_flight = None
    new.last_error = envelope.to_payload()
    new.updated_at = _now()
    return new


def in_flight_matches(
    state: CodeGeneratorState, run_id: UUID | str, job_id: UUID | str | None
) -> bool:
    """True when ``state`` still records this exact run (and job) as in flight."""
    flight = state.in_flight
    return (
        state.status is CodeGeneratorStatus.BUILD_RUNNING
        and flight is not None
        and flight.run_id == str(run_id)
        and (job_id is None or flight.job_id == str(job_id))
    )
