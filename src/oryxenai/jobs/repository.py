"""BackgroundJob repository — enqueue, claim, update, recover."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, select, update
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.db.models.background_job import BackgroundJob
from oryxenai.db.models.service_heartbeat import ServiceHeartbeat
from oryxenai.jobs.contracts import JobStatus


def _bg_from_row(row: Any) -> BackgroundJob:
    """Build a BackgroundJob from a raw SQL RETURNING row."""
    return BackgroundJob(
        id=row.id,
        job_kind=row.job_kind,
        status=row.status,
        payload=row.payload or {},
        result=row.result,
        error_payload=row.error_payload,
        priority=row.priority,
        attempt=row.attempt,
        max_attempts=row.max_attempts,
        available_at=row.available_at,
        locked_by=row.locked_by,
        locked_at=row.locked_at,
        heartbeat_at=row.heartbeat_at,
        lease_token=row.lease_token,
        idempotency_scope=row.idempotency_scope,
        idempotency_key=row.idempotency_key,
        created_at=row.created_at,
        updated_at=row.updated_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


class JobRepository:
    """Repository for background_jobs table operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(
        self,
        job_kind: str,
        payload: dict[str, Any],
        *,
        priority: int = 0,
        max_attempts: int = 3,
        idempotency_scope: str | None = None,
        idempotency_key: str | None = None,
    ) -> BackgroundJob:
        job = BackgroundJob(
            job_kind=job_kind,
            status=JobStatus.QUEUED.value,
            payload=payload,
            priority=priority,
            attempt=0,
            max_attempts=max_attempts,
            idempotency_scope=idempotency_scope or None,
            idempotency_key=idempotency_key or None,
        )
        self._session.add(job)
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def find_idempotent(
        self,
        scope: str,
        key: str,
    ) -> BackgroundJob | None:
        stmt = select(BackgroundJob).where(
            BackgroundJob.idempotency_scope == scope,
            BackgroundJob.idempotency_key == key,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, job_id: UUID) -> BackgroundJob | None:
        stmt = select(BackgroundJob).where(BackgroundJob.id == job_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def claim_batch(
        self,
        worker_instance: str,
        lease_seconds: float,
        batch_size: int,
    ) -> list[BackgroundJob]:
        """Atomically claim up to `batch_size` due jobs via CTE + SKIP LOCKED."""
        now = datetime.now(UTC)
        raw = sa_text(
            """
            WITH due AS (
                SELECT id FROM background_jobs
                WHERE status = :status AND available_at <= :now
                ORDER BY priority DESC, created_at ASC
                LIMIT :limit
                FOR UPDATE SKIP LOCKED
            )
            UPDATE background_jobs SET
                status = :newst, locked_by = :w, locked_at = :now,
                heartbeat_at = :now, attempt = attempt + 1,
                lease_token = md5(id::text || :w || clock_timestamp()::text), started_at = :now
            WHERE id IN (SELECT id FROM due)
            RETURNING *
            """
        )
        result = await self._session.execute(
            raw,
            {
                "status": JobStatus.QUEUED.value,
                "newst": JobStatus.RUNNING.value,
                "now": now,
                "limit": batch_size,
                "w": worker_instance,
            },
        )
        return [_bg_from_row(r) for r in result.fetchall()]

    async def recover_stale(
        self,
        worker_instance: str,
        lease_seconds: float,
        batch_size: int,
        *,
        exclude_job_ids: set[UUID] | None = None,
    ) -> list[BackgroundJob]:
        """Recover expired jobs not already active in this worker process.

        A provider or toolchain call can temporarily starve lease renewal. A
        worker must not recover its own still-running task in that window:
        doing so starts a concurrent duplicate and invalidates the original
        lease token. A process restart has an empty active set and can still
        recover abandoned jobs normally.
        """
        cutoff = datetime.now(UTC) - timedelta(seconds=lease_seconds)
        raw = sa_text(
            """
            WITH stale AS (
                SELECT id FROM background_jobs
                WHERE status = :status AND heartbeat_at <= :cutoff
                  AND id NOT IN :exclude_job_ids
                LIMIT :limit
                FOR UPDATE SKIP LOCKED
            )
            UPDATE background_jobs SET
                locked_by = :w, locked_at = :now, heartbeat_at = :now,
                attempt = attempt + 1,
                lease_token = md5(id::text || :w || clock_timestamp()::text), started_at = :now
            WHERE id IN (SELECT id FROM stale)
            RETURNING *
            """
        ).bindparams(
            bindparam(
                "exclude_job_ids",
                expanding=True,
                type_=PostgreSQLUUID(as_uuid=True),
            )
        )
        result = await self._session.execute(
            raw,
            {
                "status": JobStatus.RUNNING.value,
                "cutoff": cutoff,
                "limit": batch_size,
                "w": worker_instance,
                "now": datetime.now(UTC),
                "exclude_job_ids": list(exclude_job_ids or set()),
            },
        )
        return [_bg_from_row(r) for r in result.fetchall()]

    async def mark_succeeded(
        self,
        job_id: UUID,
        result: dict[str, Any],
        *,
        worker_instance: str | None = None,
        attempt: int | None = None,
        lease_token: str | None = None,
    ) -> bool:
        now = datetime.now(UTC)
        conditions = [BackgroundJob.id == job_id]
        if worker_instance is not None:
            conditions.append(BackgroundJob.locked_by == worker_instance)
        if attempt is not None:
            conditions.append(BackgroundJob.attempt == attempt)
        if lease_token is not None:
            conditions.append(BackgroundJob.lease_token == lease_token)
        stmt = (
            update(BackgroundJob)
            .where(*conditions)
            .values(status=JobStatus.SUCCEEDED.value, result=result, finished_at=now)
        )
        result_proxy = await self._session.execute(stmt)
        return bool(getattr(result_proxy, "rowcount", 0))

    async def mark_failed(
        self,
        job_id: UUID,
        error_payload: dict[str, Any],
        available_at: datetime | None = None,
        *,
        worker_instance: str | None = None,
        attempt: int | None = None,
        lease_token: str | None = None,
    ) -> bool:
        now = datetime.now(UTC)
        values: dict[str, Any] = {
            "status": JobStatus.FAILED.value,
            "error_payload": error_payload,
            "finished_at": now,
        }
        if available_at is not None:
            values["status"] = JobStatus.QUEUED.value
            values["available_at"] = available_at
            values["finished_at"] = None
        conditions = [BackgroundJob.id == job_id]
        if worker_instance is not None:
            conditions.append(BackgroundJob.locked_by == worker_instance)
        if attempt is not None:
            conditions.append(BackgroundJob.attempt == attempt)
        if lease_token is not None:
            conditions.append(BackgroundJob.lease_token == lease_token)
        stmt = update(BackgroundJob).where(*conditions).values(**values)
        result_proxy = await self._session.execute(stmt)
        return bool(getattr(result_proxy, "rowcount", 0))

    async def update_heartbeat(
        self,
        job_id: UUID,
        *,
        worker_instance: str | None = None,
        attempt: int | None = None,
        lease_token: str | None = None,
    ) -> bool:
        conditions = [BackgroundJob.id == job_id]
        if worker_instance is not None:
            conditions.append(BackgroundJob.locked_by == worker_instance)
        if attempt is not None:
            conditions.append(BackgroundJob.attempt == attempt)
        if lease_token is not None:
            conditions.append(BackgroundJob.lease_token == lease_token)
        stmt = update(BackgroundJob).where(*conditions).values(heartbeat_at=datetime.now(UTC))
        result_proxy = await self._session.execute(stmt)
        return bool(getattr(result_proxy, "rowcount", 0))

    async def list_recent(self, limit: int = 20) -> list[BackgroundJob]:
        limit = max(1, min(limit, 100))
        stmt = select(BackgroundJob).order_by(BackgroundJob.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def cleanup_heartbeats(self, stale_seconds: float) -> None:
        cutoff = datetime.now(UTC) - timedelta(seconds=stale_seconds)
        stmt = (
            update(ServiceHeartbeat)
            .where(
                ServiceHeartbeat.last_seen_at < cutoff,
                ServiceHeartbeat.stopped_at.is_(None),
            )
            .values(stopped_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
