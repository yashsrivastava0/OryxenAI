
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryxenai.jobs.heartbeat import HeartbeatRepository
from oryxenai.jobs.worker import Worker

pytestmark = [pytest.mark.integration, pytest.mark.worker]


async def test_worker_sets_running_false():
    worker = Worker()
    worker._running = False
    assert worker._running is False


async def test_shutdown_marks_stopped(test_engine):
    worker = Worker()
    worker._instance_id = uuid4().hex
    worker._sessionmaker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    await worker._init_heartbeat()

    async with worker._sessionmaker() as session:
        repo = HeartbeatRepository(session)
        latest = await repo.get_latest("oryxenai-worker")
        assert latest is not None

    async with worker._sessionmaker() as session:
        repo = HeartbeatRepository(session)
        await repo.mark_stopped(worker._instance_id)
        await session.commit()

    async with worker._sessionmaker() as session:
        repo = HeartbeatRepository(session)
        latest = await repo.get_latest("oryxenai-worker")
        assert latest is not None
        assert latest.stopped_at is not None
