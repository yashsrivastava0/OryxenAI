"""Integration tests for concurrent claim behaviour."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryxenai.jobs.policy import MODEL_GENERATION_LANE
from oryxenai.jobs.repository import JobRepository

pytestmark = [pytest.mark.integration, pytest.mark.worker]


async def test_model_lane_claims_multiple_jobs_up_to_configured_limit(db_session):
    repo = JobRepository(db_session)
    jobs = [
        await repo.enqueue(
            "discovery.understand_and_question",
            {"i": i},
            execution_lane=MODEL_GENERATION_LANE,
        )
        for i in range(4)
    ]
    await db_session.commit()

    first = await repo.claim_batch("worker-a", 120.0, 4, model_lane_concurrency=2)
    # RETURNING order is unspecified and same-transaction enqueues can share a
    # created_at, so assert the slot limit and membership rather than order.
    assert len(first) == 2
    assert {job.id for job in first} <= {job.id for job in jobs}
    await db_session.commit()

    second = await repo.claim_batch("worker-b", 120.0, 4, model_lane_concurrency=2)
    assert second == []


async def test_concurrent_model_claimers_share_slot_limit(db_session, test_engine):
    repo = JobRepository(db_session)
    jobs = [
        await repo.enqueue(
            "discovery.understand_and_question",
            {"i": i},
            execution_lane=MODEL_GENERATION_LANE,
        )
        for i in range(4)
    ]
    await db_session.commit()
    sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def claim(worker: str):
        async with sessionmaker() as session:
            claimed = await JobRepository(session).claim_batch(
                worker, 120.0, 2, model_lane_concurrency=2
            )
            await session.commit()
            return [job.id for job in claimed]

    first, second = await asyncio.gather(claim("worker-a"), claim("worker-b"))
    assert len(first) + len(second) == 2
    assert set(first + second) <= {job.id for job in jobs}


async def test_two_claimers_no_conflict(db_session, test_engine):
    repo = JobRepository(db_session)
    for i in range(10):
        await repo.enqueue("system.worker_probe", {"i": i})
    await db_session.commit()

    sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as session_a:
        repo_a = JobRepository(session_a)
        claimed_a = await repo_a.claim_batch("worker-a", 120.0, 5)
        assert len(claimed_a) == 5
        await session_a.commit()

    async with sessionmaker() as session_b:
        repo_b = JobRepository(session_b)
        claimed_b = await repo_b.claim_batch("worker-b", 120.0, 5)
        assert len(claimed_b) == 5
        await session_b.commit()

    ids_a = {j.id for j in claimed_a}
    ids_b = {j.id for j in claimed_b}
    assert ids_a.isdisjoint(ids_b)
    assert len(ids_a | ids_b) == 10


async def test_claim_respects_priority(db_session):
    repo = JobRepository(db_session)
    await repo.enqueue("system.worker_probe", {"pri": 0}, priority=0)
    await repo.enqueue("system.worker_probe", {"pri": 10}, priority=10)
    await db_session.commit()

    claimed = await repo.claim_batch("worker-1", 120.0, 1)
    assert len(claimed) == 1
    assert claimed[0].payload == {"pri": 10}
