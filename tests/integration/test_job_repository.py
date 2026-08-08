"""Integration tests for the BackgroundJob repository — require PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from oryxenai.db.models.background_job import BackgroundJob
from oryxenai.jobs.contracts import JobStatus
from oryxenai.jobs.repository import JobRepository

pytestmark = pytest.mark.integration


async def test_enqueue_creates_queued_job(db_session):
    repo = JobRepository(db_session)
    job = await repo.enqueue("system.worker_probe", {"message": "hello"})
    assert job.status == JobStatus.QUEUED.value
    assert job.payload == {"message": "hello"}


async def test_jsonb_payload_round_trip(db_session):
    repo = JobRepository(db_session)
    payload = {"nested": {"deep": [1, 2, 3]}, "list": ["a", "b"], "flag": True}
    job = await repo.enqueue("test.kind", payload)
    fetched = await repo.get_by_id(job.id)
    assert fetched is not None
    assert fetched.payload == payload
    assert fetched.payload["nested"]["deep"] == [1, 2, 3]
    assert fetched.payload["flag"] is True


async def test_claim_batch_atomic(db_session):
    repo = JobRepository(db_session)
    for i in range(3):
        await repo.enqueue("system.worker_probe", {"i": i})
    claimed = await repo.claim_batch("worker-1", 120.0, batch_size=2)
    assert len(claimed) == 2
    for job in claimed:
        assert job.status == JobStatus.RUNNING.value
    remaining = await repo.list_recent(10)
    queued = [j for j in remaining if j.status == JobStatus.QUEUED.value]
    assert len(queued) == 1


async def test_claim_skip_locked(db_session, test_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    repo = JobRepository(db_session)
    await repo.enqueue("system.worker_probe", {"i": 1})
    await repo.enqueue("system.worker_probe", {"i": 2})
    await db_session.commit()

    claimed_a = await repo.claim_batch("worker-a", 120.0, batch_size=1)
    assert len(claimed_a) == 1
    assert claimed_a[0].status == JobStatus.RUNNING.value
    await db_session.commit()

    sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as session_b:
        repo_b = JobRepository(session_b)
        claimed_b = await repo_b.claim_batch("worker-b", 120.0, batch_size=2)
        assert len(claimed_b) == 1
        assert claimed_b[0].id != claimed_a[0].id
        await session_b.commit()


async def test_idempotency_unique(db_session):
    repo = JobRepository(db_session)
    job1 = await repo.enqueue(
        "system.worker_probe", {"x": 1}, idempotency_scope="test", idempotency_key="key1"
    )
    found = await repo.find_idempotent("test", "key1")
    assert found is not None
    assert found.id == job1.id


async def test_idempotency_unique_constraint(db_session):
    job1 = BackgroundJob(
        job_kind="system.worker_probe",
        status=JobStatus.QUEUED.value,
        payload={},
        idempotency_scope="test",
        idempotency_key="dup",
    )
    db_session.add(job1)
    await db_session.flush()

    job2 = BackgroundJob(
        job_kind="system.worker_probe",
        status=JobStatus.QUEUED.value,
        payload={},
        idempotency_scope="test",
        idempotency_key="dup",
    )
    db_session.add(job2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_mark_succeeded(db_session):
    repo = JobRepository(db_session)
    job = await repo.enqueue("system.worker_probe", {"message": "hi"})
    claimed = await repo.claim_batch("worker-1", 120.0, 1)
    assert len(claimed) == 1

    await repo.mark_succeeded(job.id, {"result": "ok"})
    fetched = await repo.get_by_id(job.id)
    assert fetched is not None
    assert fetched.status == JobStatus.SUCCEEDED.value
    assert fetched.result == {"result": "ok"}


async def test_mark_failed(db_session):
    repo = JobRepository(db_session)
    job = await repo.enqueue("system.worker_probe", {})
    claimed = await repo.claim_batch("worker-1", 120.0, 1)
    assert len(claimed) == 1

    error = {"code": "TEST_ERROR", "message": "boom"}
    await repo.mark_failed(job.id, error)
    fetched = await repo.get_by_id(job.id)
    assert fetched is not None
    assert fetched.status == JobStatus.FAILED.value
    assert fetched.error_payload == error


async def test_mark_failed_with_retry(db_session):
    repo = JobRepository(db_session)
    job = await repo.enqueue("system.worker_probe", {})
    claimed = await repo.claim_batch("worker-1", 120.0, 1)
    assert len(claimed) == 1

    future = datetime.now(UTC) + timedelta(seconds=30)
    error = {"code": "RETRYABLE", "message": "retry later"}
    await repo.mark_failed(job.id, error, available_at=future)
    fetched = await repo.get_by_id(job.id)
    assert fetched is not None
    assert fetched.status == JobStatus.QUEUED.value
    assert fetched.error_payload == error
    assert fetched.available_at is not None


async def test_update_heartbeat(db_session):
    repo = JobRepository(db_session)
    job = await repo.enqueue("system.worker_probe", {})
    claimed = await repo.claim_batch("worker-1", 120.0, 1)
    assert len(claimed) == 1

    old_heartbeat = claimed[0].heartbeat_at
    await repo.update_heartbeat(job.id)
    fetched = await repo.get_by_id(job.id)
    assert fetched is not None
    assert fetched.heartbeat_at is not None
    assert fetched.heartbeat_at >= old_heartbeat


async def test_recover_stale(db_session):
    now = datetime.now(UTC)
    old_time = now - timedelta(seconds=300)

    stale_job = BackgroundJob(
        job_kind="system.worker_probe",
        status=JobStatus.RUNNING.value,
        payload={},
        locked_by="dead-worker",
        heartbeat_at=old_time,
        started_at=old_time,
    )
    db_session.add(stale_job)
    await db_session.commit()

    repo = JobRepository(db_session)
    recovered = await repo.recover_stale("new-worker", 60.0, 10)
    assert len(recovered) == 1
    assert recovered[0].id == stale_job.id
    assert recovered[0].locked_by == "new-worker"


async def test_recover_stale_skips_a_recently_renewed_heartbeat(db_session):
    """A job whose lease was renewed mid-execution must not be reclaimed.

    worker.py renews a claimed job's heartbeat periodically while its
    handler is still running (Worker._renew_lease_loop), specifically so a
    handler that legitimately runs close to the lease_duration (e.g. a
    slow model generation) never looks abandoned. Without that renewal,
    recover_stale would redispatch the same job for a second, concurrent
    execution while the first one is still genuinely in flight.
    """
    now = datetime.now(UTC)
    old_claim_time = now - timedelta(seconds=300)

    long_running_job = BackgroundJob(
        job_kind="system.worker_probe",
        status=JobStatus.RUNNING.value,
        payload={},
        locked_by="still-alive-worker",
        heartbeat_at=old_claim_time,
        started_at=old_claim_time,
    )
    db_session.add(long_running_job)
    await db_session.commit()

    repo = JobRepository(db_session)
    await repo.update_heartbeat(long_running_job.id)

    recovered = await repo.recover_stale("new-worker", 60.0, 10)
    assert recovered == []

    fetched = await repo.get_by_id(long_running_job.id)
    assert fetched is not None
    assert fetched.locked_by == "still-alive-worker"


async def test_list_recent(db_session):
    repo = JobRepository(db_session)
    for i in range(3):
        await repo.enqueue("system.worker_probe", {"i": i})
    jobs = await repo.list_recent(2)
    assert len(jobs) == 2
    assert jobs[0].created_at >= jobs[1].created_at
