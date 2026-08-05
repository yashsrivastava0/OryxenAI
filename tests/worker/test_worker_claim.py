"""Integration tests for concurrent claim behaviour."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryxenai.jobs.repository import JobRepository

pytestmark = [pytest.mark.integration, pytest.mark.worker]


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
