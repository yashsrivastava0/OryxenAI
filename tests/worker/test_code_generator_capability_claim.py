"""Worker claim behavior for the Code Generator capability fence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryxenai.agents.code_generator.core.worker_readiness import (
    capability_proof_blocker,
    worker_contract_readiness,
)
from oryxenai.core.settings import Settings
from oryxenai.jobs import worker as worker_module
from oryxenai.jobs.contracts import JobStatus
from oryxenai.jobs.heartbeat import HeartbeatRepository
from oryxenai.jobs.repository import JobRepository
from oryxenai.jobs.worker import Worker

pytestmark = [pytest.mark.integration, pytest.mark.worker]


async def _stop_worker(worker: Worker) -> None:
    async with worker._sessionmaker() as session:
        await HeartbeatRepository(session).mark_stopped(worker._instance_id)
        await session.commit()


def _preflight_result(*, ready: bool) -> dict[str, object]:
    checked_at = datetime.now(UTC)
    checks = dict.fromkeys(
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
            "preview_gateway",
            "preview_storage_readback",
            "preview_gateway_readback",
            "brief_dependency_paths",
        ),
        ready,
    )
    return {
        "ready": ready,
        "checked_at": checked_at.isoformat(),
        "expires_at": (checked_at + timedelta(minutes=5)).isoformat(),
        "facts": {"node_version": "v22", "npm_version": "10"},
        "checks": checks,
    }


async def test_unproven_worker_fails_queued_codegen_job_with_actionable_reason(
    db_session, test_engine, monkeypatch
) -> None:
    settings = Settings()
    settings.code_generator_verification.enabled = True
    settings.diagnostics.heartbeat_staleness = 1.0
    settings.worker.heartbeat_interval = 0.25
    worker = Worker(settings)
    worker._sessionmaker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def blocked_preflight(_settings, *, require_brief_dependency_paths):
        assert require_brief_dependency_paths is False
        return _preflight_result(ready=False)

    monkeypatch.setattr(worker_module, "run_toolchain_preflight", blocked_preflight)
    monkeypatch.setattr(worker_module, "get_handler", lambda _kind: None)
    repo = JobRepository(db_session)
    job = await repo.enqueue("code_generator.plan", {"test_job": True})
    await db_session.commit()

    claimed = await worker._claim_due(limit=1)

    assert claimed == []
    async with worker._sessionmaker() as session:
        stored = await JobRepository(session).get_by_id(job.id)
        assert stored is not None
        assert stored.status == JobStatus.FAILED.value
        assert stored.error_payload["code"] == "CODE_GENERATOR_WORKER_TOOLCHAIN_UNAVAILABLE"
        assert "fix the reported prerequisite" in stored.error_payload["message"]
    await _stop_worker(worker)


async def test_proven_worker_can_claim_codegen_job(db_session, test_engine, monkeypatch) -> None:
    settings = Settings()
    settings.code_generator_verification.enabled = True
    settings.diagnostics.heartbeat_staleness = 1.0
    settings.worker.heartbeat_interval = 0.25
    worker = Worker(settings)
    worker._sessionmaker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def ready_preflight(_settings, *, require_brief_dependency_paths):
        assert require_brief_dependency_paths is False
        return _preflight_result(ready=True)

    monkeypatch.setattr(worker_module, "run_toolchain_preflight", ready_preflight)
    await worker._refresh_code_generator_capability(force=True)
    local_blocker = capability_proof_blocker(
        worker._code_generator_capability_proof,
        settings=settings,
        worker_instance_id=worker._instance_id,
    )
    assert local_blocker == "", worker._code_generator_capability_proof
    async with worker._sessionmaker() as session:
        await HeartbeatRepository(session).upsert(
            worker._instance_id, "oryxenai-worker", worker._worker_metadata()
        )
        await session.commit()
    async with worker._sessionmaker() as session:
        readiness = await worker_contract_readiness(HeartbeatRepository(session), settings)
    assert readiness["ready"], [
        (
            row["instance_id"],
            row["release_id"],
            row["capability_blocker"],
            row["age_seconds"],
        )
        for row in readiness["active_workers"]
    ]
    repo = JobRepository(db_session)
    job = await repo.enqueue("code_generator.plan", {"test_job": True})
    await db_session.commit()

    try:
        claimed = await worker._claim_due(limit=1)

        if not claimed:
            async with worker._sessionmaker() as session:
                stored = await JobRepository(session).get_by_id(job.id)
                blocker = stored.error_payload if stored is not None else "job was not found"
            pytest.fail(f"a proven worker failed to claim the job: {blocker}")
        assert len(claimed) == 1
        assert claimed[0].id == job.id
        assert claimed[0].status == JobStatus.RUNNING.value
    finally:
        await repo.cancel(
            job.id,
            code="TEST_CLEANUP",
            message="The worker capability test finished.",
        )
        await db_session.commit()
        await _stop_worker(worker)
