"""Integration tests for the worker retry behaviour."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from oryxenai.jobs.contracts import JobStatus, retryable
from oryxenai.jobs.repository import JobRepository
from oryxenai.jobs.retry import should_retry

pytestmark = [pytest.mark.integration, pytest.mark.worker]


async def test_retryable_job_goes_back_to_queued(db_session):
    repo = JobRepository(db_session)
    job = await repo.enqueue("system.worker_probe", {})
    claimed = await repo.claim_batch("worker-1", 120.0, 1)
    assert len(claimed) == 1

    future = datetime.now(UTC) + timedelta(seconds=60)
    error = {"code": "RETRYABLE", "message": "transient", "retryable": True}
    await repo.mark_failed(job.id, error, available_at=future)

    fetched = await repo.get_by_id(job.id)
    assert fetched is not None
    assert fetched.status == JobStatus.QUEUED.value
    assert fetched.available_at is not None
    assert fetched.error_payload == error


async def test_permanent_failure_stays_failed(db_session):
    repo = JobRepository(db_session)
    job = await repo.enqueue("system.worker_probe", {})
    claimed = await repo.claim_batch("worker-1", 120.0, 1)
    assert len(claimed) == 1

    error = {"code": "PERMANENT", "message": "fatal", "retryable": False}
    await repo.mark_failed(job.id, error)

    fetched = await repo.get_by_id(job.id)
    assert fetched is not None
    assert fetched.status == JobStatus.FAILED.value
    assert fetched.error_payload == error


async def test_max_attempts_exhausted(db_session):
    repo = JobRepository(db_session)
    job = await repo.enqueue("system.worker_probe", {}, max_attempts=1)
    claimed = await repo.claim_batch("worker-1", 120.0, 1)
    assert len(claimed) == 1
    assert claimed[0].attempt == 2

    error = retryable("TEST", "should not retry")
    assert not should_retry(error, claimed[0].attempt, job.max_attempts)

    await repo.mark_failed(job.id, {"code": "TEST", "message": "exhausted"})
    fetched = await repo.get_by_id(job.id)
    assert fetched is not None
    assert fetched.status == JobStatus.FAILED.value
