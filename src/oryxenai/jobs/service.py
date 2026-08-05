"""Job service — thin wrapper for enqueue operations used by the API layer."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.jobs.repository import JobRepository


class JobService:
    """Service for enqueuing durable background jobs.

    Accepts an existing SQLAlchemy session so that enqueue can participate
    in the caller's transaction.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = JobRepository(session)

    async def enqueue(
        self,
        job_kind: str,
        payload: dict[str, Any],
        *,
        priority: int = 0,
        max_attempts: int = 3,
        idempotency_scope: str = "",
        idempotency_key: str = "",
    ) -> Any:
        """Enqueue a job; returns the persisted BackgroundJob row."""
        scope = idempotency_scope or None
        key = idempotency_key or None
        if scope and key:
            existing = await self._repo.find_idempotent(scope, key)
            if existing is not None:
                return existing
        return await self._repo.enqueue(
            job_kind=job_kind,
            payload=payload,
            priority=priority,
            max_attempts=max_attempts,
            idempotency_scope=scope,
            idempotency_key=key,
        )

    async def get(self, job_id: UUID) -> Any:
        """Return a job by ID for status polling."""
        return await self._repo.get_by_id(job_id)

    async def find_idempotent(self, scope: str, key: str) -> Any:
        """Return an existing idempotent job, if one exists."""
        return await self._repo.find_idempotent(scope, key)
