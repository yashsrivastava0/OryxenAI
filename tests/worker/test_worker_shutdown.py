from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryxenai.jobs import worker as worker_module
from oryxenai.jobs.heartbeat import HeartbeatRepository
from oryxenai.jobs.worker import Worker

pytestmark = [pytest.mark.integration, pytest.mark.worker]


async def test_worker_sets_running_false():
    worker = Worker()
    worker._running = False
    assert worker._running is False


async def test_shutdown_marks_stopped(test_engine, monkeypatch):
    worker = Worker()
    worker._instance_id = str(uuid4())
    worker._sessionmaker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def fake_preflight(_settings, *, require_brief_dependency_paths):
        assert require_brief_dependency_paths is False
        checked_at = datetime.now(UTC)
        return {
            "ready": True,
            "checked_at": checked_at.isoformat(),
            "expires_at": (checked_at + timedelta(minutes=5)).isoformat(),
            "facts": {"node_version": "v22", "npm_version": "10"},
            "checks": dict.fromkeys(
                (
                    "scaffold",
                    "node",
                    "npm",
                    "workspace_writable",
                    "checkpoint_writable",
                    "artifact_writable",
                    "cache_writable",
                    "preview_writable",
                    "install",
                    "typecheck",
                    "build",
                    "browser",
                    "preview_gateway_readback",
                    "preview_storage_readback",
                ),
                True,
            ),
        }

    monkeypatch.setattr(worker_module, "run_toolchain_preflight", fake_preflight)
    await worker._init_heartbeat()

    async with worker._sessionmaker() as session:
        repo = HeartbeatRepository(session)
        latest = await repo.get_latest("oryxenai-worker")
        assert latest is not None
        assert latest.service_metadata["code_generator_capability"] is True
        assert latest.service_metadata["code_generator_capability_proof"][
            "toolchain_identity_sha256"
        ]

    async with worker._sessionmaker() as session:
        repo = HeartbeatRepository(session)
        await repo.mark_stopped(worker._instance_id)
        await session.commit()

    async with worker._sessionmaker() as session:
        repo = HeartbeatRepository(session)
        latest = await repo.get_latest("oryxenai-worker")
        assert latest is not None
        assert latest.stopped_at is not None
