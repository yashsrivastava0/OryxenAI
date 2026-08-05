"""Integration tests for the ServiceHeartbeat repository — require PostgreSQL."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from oryxenai.jobs.heartbeat import HeartbeatRepository

pytestmark = pytest.mark.integration


async def test_upsert_creates_new(db_session):
    repo = HeartbeatRepository(db_session)
    instance_id = str(uuid4())
    hb = await repo.upsert(instance_id, "oryxenai-worker")
    assert hb.instance_id is not None
    assert hb.service_name == "oryxenai-worker"
    assert hb.last_seen_at is not None


async def test_upsert_updates_existing(db_session):
    repo = HeartbeatRepository(db_session)
    instance_id = str(uuid4())
    hb1 = await repo.upsert(instance_id, "oryxenai-worker")
    old_last_seen = hb1.last_seen_at
    await asyncio.sleep(0.1)
    hb2 = await repo.upsert(instance_id, "oryxenai-worker")
    assert hb2.last_seen_at > old_last_seen


async def test_get_recent(db_session):
    repo = HeartbeatRepository(db_session)
    id1 = str(uuid4())
    id2 = str(uuid4())
    await repo.upsert(id1, "oryxenai-worker")
    await asyncio.sleep(0.1)
    await repo.upsert(id2, "oryxenai-worker")
    recent = await repo.get_recent("oryxenai-worker", 10)
    assert len(recent) >= 2
    assert recent[0].last_seen_at >= recent[1].last_seen_at


async def test_get_latest(db_session):
    repo = HeartbeatRepository(db_session)
    id1 = str(uuid4())
    id2 = str(uuid4())
    await repo.upsert(id1, "oryxenai-worker")
    await asyncio.sleep(0.1)
    await repo.upsert(id2, "oryxenai-worker")
    latest = await repo.get_latest("oryxenai-worker")
    assert latest is not None


async def test_mark_stopped(db_session):
    repo = HeartbeatRepository(db_session)
    instance_id = str(uuid4())
    await repo.upsert(instance_id, "oryxenai-worker")
    await repo.mark_stopped(instance_id)
    latest = await repo.get_latest("oryxenai-worker")
    assert latest is not None
    assert latest.stopped_at is not None
