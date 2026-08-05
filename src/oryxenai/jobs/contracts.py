"""Job system contracts: statuses, payloads, and handler protocol."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


# ── Valid status transitions ────────────────────────────────────────────────
_VALID_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.QUEUED: frozenset({JobStatus.RUNNING}),
    JobStatus.RUNNING: frozenset({JobStatus.QUEUED, JobStatus.SUCCEEDED, JobStatus.FAILED}),
    JobStatus.SUCCEEDED: frozenset(),
    JobStatus.FAILED: frozenset({JobStatus.QUEUED}),
}


def is_valid_transition(current: JobStatus, target: JobStatus) -> bool:
    return target in _VALID_TRANSITIONS.get(current, frozenset())


# ── System job kinds ────────────────────────────────────────────────────────
SYSTEM_PROBE_KIND = "system.worker_probe"


# ── Payloads ─────────────────────────────────────────────────────────────────


class JobPayload(BaseModel):
    """Validated payload carried by a job. Subclassed by specific handlers."""

    model_config = {"extra": "allow"}


class ProbePayload(JobPayload):
    """Payload for the system.worker_probe handler."""

    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProbeResult(BaseModel):
    """Result returned by system.worker_probe."""

    received_at: str
    worker_instance: str
    echo_message: str


# ── Errors ──────────────────────────────────────────────────────────────────


class JobError(BaseModel):
    """Safe structured error stored on a failed job."""

    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


def retryable(code: str, message: str, details: dict[str, Any] | None = None) -> JobError:
    return JobError(code=code, message=message, retryable=True, details=details or {})


def permanent(code: str, message: str, details: dict[str, Any] | None = None) -> JobError:
    return JobError(code=code, message=message, retryable=False, details=details or {})


# ── Handler protocol ────────────────────────────────────────────────────────


class JobHandler(Protocol):
    """Protocol every registered job handler must satisfy."""

    @property
    def kind(self) -> str: ...

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]: ...


# ── API request/response DTOs ────────────────────────────────────────────────


class EnqueueRequest(BaseModel):
    job_kind: str = SYSTEM_PROBE_KIND
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_scope: str = ""
    idempotency_key: str = ""


class JobStatusResponse(BaseModel):
    id: str
    job_kind: str
    status: str
    attempt: int
    max_attempts: int
    created_at: str
    started_at: str | None
    finished_at: str | None
    result: dict[str, Any] | None
    error: dict[str, Any] | None
    worker_instance: str | None
