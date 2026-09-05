"""BackgroundJob repository — enqueue, claim, update, recover."""

# The two raw SQL statements below are fixed query templates; the optional
# predicate is selected from a literal string and all values remain bound
# parameters. Ruff cannot prove that property through the CTE formatting.
# ruff: noqa: S608

from __future__ import annotations

from collections.abc import Collection
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, select, update
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.exc import IntegrityError
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
        portfolio_session_id=row.portfolio_session_id,
        owner_user_id=row.owner_user_id,
        actor_user_id=row.actor_user_id,
        authorization_context_version=row.authorization_context_version,
        entitlement_revision=row.entitlement_revision,
        execution_lane=row.execution_lane,
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
        portfolio_session_id: UUID | None = None,
        owner_user_id: UUID | None = None,
        actor_user_id: UUID | None = None,
        authorization_context_version: int = 0,
        entitlement_revision: int | None = None,
        execution_lane: str | None = None,
    ) -> BackgroundJob:
        job = BackgroundJob(
            job_kind=job_kind,
            status=JobStatus.QUEUED.value,
            payload=payload,
            portfolio_session_id=portfolio_session_id,
            owner_user_id=owner_user_id,
            actor_user_id=actor_user_id,
            authorization_context_version=authorization_context_version,
            entitlement_revision=entitlement_revision,
            execution_lane=execution_lane,
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

    async def cancel(
        self,
        job_id: UUID,
        *,
        code: str = "JOB_CANCELLED",
        message: str = "The job was stopped by the user.",
    ) -> bool:
        """Cancel queued/running work and fence any late worker completion.

        Clearing the lease token is intentional: a worker that finishes after
        this update can no longer mark the row succeeded. The agent handler
        also checks the cancelled row before applying its state result.
        """
        now = datetime.now(UTC)
        stmt = (
            update(BackgroundJob)
            .where(
                BackgroundJob.id == job_id,
                BackgroundJob.status.in_((JobStatus.QUEUED.value, JobStatus.RUNNING.value)),
            )
            .values(
                status=JobStatus.CANCELLED.value,
                error_payload={"code": code, "message": message, "retryable": False},
                result=None,
                locked_by=None,
                locked_at=None,
                heartbeat_at=None,
                lease_token=None,
                finished_at=now,
                updated_at=now,
            )
        )
        result = await self._session.execute(stmt)
        return bool(getattr(result, "rowcount", 0))

    async def claim_batch(
        self,
        worker_instance: str,
        lease_seconds: float,
        batch_size: int,
        *,
        allowed_job_kinds: Collection[str] | None = None,
        foreground_job_kinds: Collection[str] | None = None,
    ) -> list[BackgroundJob]:
        """Atomically claim up to `batch_size` due jobs via CTE + SKIP LOCKED."""
        if allowed_job_kinds is not None and not allowed_job_kinds:
            return []
        if foreground_job_kinds is not None and not foreground_job_kinds:
            foreground_job_kinds = None
        now = datetime.now(UTC)
        kind_filter = (
            "AND job.job_kind IN :allowed_job_kinds" if allowed_job_kinds is not None else ""
        )
        foreground_rank = (
            "CASE WHEN job.job_kind IN :foreground_job_kinds THEN 0 ELSE 1 END"
            if foreground_job_kinds is not None
            else "0"
        )
        earlier_foreground_rank = (
            "CASE WHEN earlier.job_kind IN :foreground_job_kinds THEN 0 ELSE 1 END"
            if foreground_job_kinds is not None
            else "0"
        )
        foreground_order = f"{foreground_rank} ASC, " if foreground_job_kinds is not None else ""
        raw = sa_text(
            f"""
            WITH due AS (
                SELECT job.id FROM background_jobs AS job
                WHERE job.status = :status AND job.available_at <= :now
                  {kind_filter}
                  AND (
                    job.execution_lane IS NULL
                    OR NOT EXISTS (
                        SELECT 1 FROM background_jobs AS running
                        WHERE running.status = 'running'
                          AND running.execution_lane = job.execution_lane
                    )
                  )
                  AND (
                    job.execution_lane IS NULL
                    OR NOT EXISTS (
                        SELECT 1 FROM background_jobs AS earlier
                        WHERE earlier.status = 'queued'
                          AND earlier.execution_lane = job.execution_lane
                          AND earlier.available_at <= :now
                          AND (
                              {earlier_foreground_rank} < {foreground_rank}
                              OR (
                                  {earlier_foreground_rank} = {foreground_rank}
                                  AND (
                                      earlier.priority > job.priority
                                      OR (
                                          earlier.priority = job.priority
                                          AND (earlier.created_at, earlier.id)
                                              < (job.created_at, job.id)
                                      )
                                  )
                              )
                          )
                      )
                  )
                ORDER BY {foreground_order}job.priority DESC, job.created_at ASC
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
        if allowed_job_kinds is not None:
            raw = raw.bindparams(bindparam("allowed_job_kinds", expanding=True))
        if foreground_job_kinds is not None:
            raw = raw.bindparams(bindparam("foreground_job_kinds", expanding=True))
        for attempt in range(3):
            try:
                result = await self._session.execute(
                    raw,
                    {
                        "status": JobStatus.QUEUED.value,
                        "newst": JobStatus.RUNNING.value,
                        "now": now,
                        "limit": batch_size,
                        "w": worker_instance,
                        **(
                            {"allowed_job_kinds": list(allowed_job_kinds)}
                            if allowed_job_kinds is not None
                            else {}
                        ),
                        **(
                            {"foreground_job_kinds": list(foreground_job_kinds)}
                            if foreground_job_kinds is not None
                            else {}
                        ),
                    },
                )
                return [_bg_from_row(r) for r in result.fetchall()]
            except IntegrityError:
                await self._session.rollback()
                if attempt == 2:
                    raise
        return []

    async def recover_stale(
        self,
        worker_instance: str,
        lease_seconds: float,
        batch_size: int,
        *,
        exclude_job_ids: set[UUID] | None = None,
        allowed_job_kinds: Collection[str] | None = None,
        foreground_job_kinds: Collection[str] | None = None,
    ) -> list[BackgroundJob]:
        """Recover expired jobs not already active in this worker process.

        A provider or toolchain call can temporarily starve lease renewal. A
        worker must not recover its own still-running task in that window:
        doing so starts a concurrent duplicate and invalidates the original
        lease token. A process restart has an empty active set and can still
        recover abandoned jobs normally.
        """
        if allowed_job_kinds is not None and not allowed_job_kinds:
            return []
        if foreground_job_kinds is not None and not foreground_job_kinds:
            foreground_job_kinds = None
        cutoff = datetime.now(UTC) - timedelta(seconds=lease_seconds)
        kind_filter = (
            "AND job.job_kind IN :allowed_job_kinds" if allowed_job_kinds is not None else ""
        )
        foreground_rank = (
            "CASE WHEN job.job_kind IN :foreground_job_kinds THEN 0 ELSE 1 END"
            if foreground_job_kinds is not None
            else "0"
        )
        foreground_order = f"{foreground_rank} ASC, " if foreground_job_kinds is not None else ""
        raw = sa_text(
            f"""
            WITH stale AS (
                SELECT job.id FROM background_jobs AS job
                WHERE job.status = :status AND job.heartbeat_at <= :cutoff
                  {kind_filter}
                  AND job.id NOT IN :exclude_job_ids
                  AND (
                    job.execution_lane IS NULL
                    OR NOT EXISTS (
                        SELECT 1 FROM background_jobs AS running
                        WHERE running.status = 'running'
                          AND running.execution_lane = job.execution_lane
                          AND running.id <> job.id
                    )
                  )
                  AND (
                        job.execution_lane IS NULL
                        OR NOT EXISTS (
                          SELECT 1 FROM background_jobs AS earlier_stale
                          WHERE earlier_stale.status = 'running'
                            AND earlier_stale.heartbeat_at <= :cutoff
                          AND earlier_stale.execution_lane = job.execution_lane
                          AND earlier_stale.id <> job.id
                          AND (earlier_stale.created_at, earlier_stale.id)
                              < (job.created_at, job.id)
                    )
                  )
                ORDER BY {foreground_order}job.created_at ASC
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
        if allowed_job_kinds is not None:
            raw = raw.bindparams(bindparam("allowed_job_kinds", expanding=True))
        if foreground_job_kinds is not None:
            raw = raw.bindparams(bindparam("foreground_job_kinds", expanding=True))
        result = await self._session.execute(
            raw,
            {
                "status": JobStatus.RUNNING.value,
                "cutoff": cutoff,
                "limit": batch_size,
                "w": worker_instance,
                "now": datetime.now(UTC),
                "exclude_job_ids": list(exclude_job_ids or set()),
                **(
                    {"allowed_job_kinds": list(allowed_job_kinds)}
                    if allowed_job_kinds is not None
                    else {}
                ),
                **(
                    {"foreground_job_kinds": list(foreground_job_kinds)}
                    if foreground_job_kinds is not None
                    else {}
                ),
            },
        )
        return [_bg_from_row(r) for r in result.fetchall()]

    async def requeue_stale(
        self,
        lease_seconds: float,
        batch_size: int,
        *,
        exclude_job_ids: set[UUID] | None = None,
        allowed_job_kinds: Collection[str] | None = None,
        foreground_job_kinds: Collection[str] | None = None,
    ) -> int:
        """Release expired leases so the normal claim order can choose work.

        Requeueing first is important when an abandoned job occupies the
        unique model-generation lane: a fresh foreground request must be
        able to claim that lane before the abandoned job is dispatched again.
        The old worker's lease token is cleared, so any late completion is
        fenced by the existing completion predicates.
        """
        if batch_size <= 0:
            return 0
        if allowed_job_kinds is not None and not allowed_job_kinds:
            return 0
        if foreground_job_kinds is not None and not foreground_job_kinds:
            foreground_job_kinds = None
        cutoff = datetime.now(UTC) - timedelta(seconds=lease_seconds)
        # A worker restricted to a subset of handlers still needs to release
        # an expired *different* kind when that row occupies an execution
        # lane required by one of its due jobs.  Otherwise a stale generator
        # lease can keep a healthy Discovery-only worker idle forever.  The
        # worker may only claim allowed kinds; this broader predicate merely
        # releases the expired lane blocker and fences its old lease token.
        kind_filter = (
            """
            AND (
                job.job_kind IN :allowed_job_kinds
                OR (
                    job.execution_lane IS NOT NULL
                    AND EXISTS (
                        SELECT 1 FROM background_jobs AS due_allowed
                        WHERE due_allowed.status = :queued_status
                          AND due_allowed.available_at <= :now
                          AND due_allowed.execution_lane = job.execution_lane
                          AND due_allowed.job_kind IN :allowed_job_kinds
                    )
                )
            )
            """
            if allowed_job_kinds is not None
            else ""
        )
        foreground_rank = (
            "CASE WHEN job.job_kind IN :foreground_job_kinds THEN 0 ELSE 1 END"
            if foreground_job_kinds is not None
            else "0"
        )
        foreground_order = f"{foreground_rank} ASC, " if foreground_job_kinds is not None else ""
        raw = sa_text(
            f"""
            WITH stale AS (
                SELECT job.id FROM background_jobs AS job
                WHERE job.status = :running_status AND job.heartbeat_at <= :cutoff
                  {kind_filter}
                  AND job.id NOT IN :exclude_job_ids
                  AND (
                    job.execution_lane IS NULL
                    OR NOT EXISTS (
                        SELECT 1 FROM background_jobs AS running
                        WHERE running.status = :running_status
                          AND running.execution_lane = job.execution_lane
                          AND running.id <> job.id
                          AND running.heartbeat_at > :cutoff
                    )
                  )
                  AND (
                    job.execution_lane IS NULL
                    OR NOT EXISTS (
                        SELECT 1 FROM background_jobs AS earlier_stale
                        WHERE earlier_stale.status = :running_status
                          AND earlier_stale.heartbeat_at <= :cutoff
                          AND earlier_stale.execution_lane = job.execution_lane
                          AND earlier_stale.id <> job.id
                          AND (earlier_stale.created_at, earlier_stale.id)
                              < (job.created_at, job.id)
                    )
                  )
                ORDER BY {foreground_order}job.created_at ASC
                LIMIT :limit
                FOR UPDATE SKIP LOCKED
            )
            UPDATE background_jobs SET
                status = :queued_status,
                locked_by = NULL,
                locked_at = NULL,
                heartbeat_at = NULL,
                lease_token = NULL,
                started_at = NULL,
                available_at = :now,
                updated_at = :now
            WHERE id IN (SELECT id FROM stale)
            RETURNING id
            """
        ).bindparams(
            bindparam(
                "exclude_job_ids",
                expanding=True,
                type_=PostgreSQLUUID(as_uuid=True),
            )
        )
        if allowed_job_kinds is not None:
            raw = raw.bindparams(bindparam("allowed_job_kinds", expanding=True))
        if foreground_job_kinds is not None:
            raw = raw.bindparams(bindparam("foreground_job_kinds", expanding=True))
        result = await self._session.execute(
            raw,
            {
                "running_status": JobStatus.RUNNING.value,
                "queued_status": JobStatus.QUEUED.value,
                "cutoff": cutoff,
                "limit": batch_size,
                "now": datetime.now(UTC),
                "exclude_job_ids": list(exclude_job_ids or set()),
                **(
                    {"allowed_job_kinds": list(allowed_job_kinds)}
                    if allowed_job_kinds is not None
                    else {}
                ),
                **(
                    {"foreground_job_kinds": list(foreground_job_kinds)}
                    if foreground_job_kinds is not None
                    else {}
                ),
            },
        )
        return len(result.fetchall())

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
            .values(
                status=JobStatus.SUCCEEDED.value,
                result=result,
                error_payload=None,
                finished_at=now,
            )
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
