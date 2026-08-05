"""Unit tests for job system contracts."""

from __future__ import annotations

import pytest

from oryxenai.jobs.contracts import (
    SYSTEM_PROBE_KIND,
    EnqueueRequest,
    JobStatus,
    JobStatusResponse,
    ProbePayload,
    ProbeResult,
    is_valid_transition,
    permanent,
    retryable,
)


def test_job_status_values():
    """JobStatus enum has the expected values."""
    assert JobStatus.QUEUED.value == "queued"
    assert JobStatus.RUNNING.value == "running"
    assert JobStatus.SUCCEEDED.value == "succeeded"
    assert JobStatus.FAILED.value == "failed"


def test_is_valid_transition_valid():
    """Valid transitions return True."""
    assert is_valid_transition(JobStatus.QUEUED, JobStatus.RUNNING) is True
    assert is_valid_transition(JobStatus.RUNNING, JobStatus.SUCCEEDED) is True
    assert is_valid_transition(JobStatus.RUNNING, JobStatus.FAILED) is True
    assert is_valid_transition(JobStatus.RUNNING, JobStatus.QUEUED) is True
    assert is_valid_transition(JobStatus.FAILED, JobStatus.QUEUED) is True


def test_is_valid_transition_invalid():
    """Invalid transitions return False."""
    assert is_valid_transition(JobStatus.QUEUED, JobStatus.SUCCEEDED) is False
    assert is_valid_transition(JobStatus.QUEUED, JobStatus.FAILED) is False
    assert is_valid_transition(JobStatus.SUCCEEDED, JobStatus.QUEUED) is False
    assert is_valid_transition(JobStatus.SUCCEEDED, JobStatus.RUNNING) is False
    assert is_valid_transition(JobStatus.FAILED, JobStatus.RUNNING) is False


def test_probe_payload_valid():
    """ProbePayload accepts valid data."""
    payload = ProbePayload(message="hello", metadata={"key": "value"})
    assert payload.message == "hello"
    assert payload.metadata == {"key": "value"}


def test_probe_payload_defaults():
    """ProbePayload uses defaults when no args provided."""
    payload = ProbePayload()
    assert payload.message == ""
    assert payload.metadata == {}


def test_probe_payload_invalid_type():
    """ProbePayload rejects invalid message type."""
    with pytest.raises(Exception):
        ProbePayload(message=42)


def test_probe_result_creation():
    """ProbeResult can be created with required fields."""
    result = ProbeResult(
        received_at="2025-01-01T00:00:00+00:00",
        worker_instance="worker-1",
        echo_message="hello",
    )
    assert result.received_at == "2025-01-01T00:00:00+00:00"
    assert result.worker_instance == "worker-1"
    assert result.echo_message == "hello"


def test_job_error_retryable():
    """retryable() creates a JobError with retryable=True."""
    err = retryable("ERR_TEMP", "temporary")
    assert err.code == "ERR_TEMP"
    assert err.message == "temporary"
    assert err.retryable is True
    assert err.details == {}


def test_job_error_permanent():
    """permanent() creates a JobError with retryable=False."""
    err = permanent("ERR_FATAL", "fatal")
    assert err.code == "ERR_FATAL"
    assert err.message == "fatal"
    assert err.retryable is False
    assert err.details == {}


def test_job_error_with_details():
    """JobError carries optional details dict."""
    err = retryable("ERR_X", "msg", details={"hint": "retry later"})
    assert err.details == {"hint": "retry later"}


def test_enqueue_request_defaults():
    """EnqueueRequest defaults to system.worker_probe."""
    req = EnqueueRequest()
    assert req.job_kind == SYSTEM_PROBE_KIND
    assert req.payload == {}
    assert req.idempotency_scope == ""
    assert req.idempotency_key == ""


def test_enqueue_request_custom():
    """EnqueueRequest accepts custom fields."""
    req = EnqueueRequest(
        job_kind="custom.kind",
        payload={"x": 1},
        idempotency_scope="session",
        idempotency_key="abc",
    )
    assert req.job_kind == "custom.kind"
    assert req.payload == {"x": 1}


def test_job_status_response_creation():
    """JobStatusResponse can be created with all fields."""
    resp = JobStatusResponse(
        id="job-1",
        job_kind="system.worker_probe",
        status="succeeded",
        attempt=1,
        max_attempts=3,
        created_at="2025-01-01T00:00:00+00:00",
        started_at="2025-01-01T00:00:01+00:00",
        finished_at="2025-01-01T00:00:02+00:00",
        result={"ok": True},
        error=None,
        worker_instance="worker-1",
    )
    assert resp.id == "job-1"
    assert resp.status == "succeeded"
    assert resp.attempt == 1
    assert resp.result == {"ok": True}
    assert resp.error is None
