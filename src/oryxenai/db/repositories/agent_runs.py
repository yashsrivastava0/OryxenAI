"""AgentRun repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.db.models.agent_run import AgentRun


class AgentRunRepository:
    """Repository for agent_runs table operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: AgentRun) -> AgentRun:
        self._session.add(run)
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def get_by_id(self, run_id: UUID) -> AgentRun | None:
        stmt = select(AgentRun).where(AgentRun.id == run_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_idempotency(
        self,
        session_id: UUID,
        agent_key: str,
        idempotency_key: str,
    ) -> AgentRun | None:
        """Return an existing run with the same idempotency key, if any."""
        stmt = select(AgentRun).where(
            AgentRun.portfolio_session_id == session_id,
            AgentRun.agent_key == agent_key,
            AgentRun.idempotency_key == idempotency_key,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_session(self, session_id: UUID, limit: int = 20) -> list[AgentRun]:
        limit = max(1, min(limit, 100))
        stmt = (
            select(AgentRun)
            .where(AgentRun.portfolio_session_id == session_id)
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_started(self, run_id: UUID) -> None:
        stmt = select(AgentRun).where(AgentRun.id == run_id)
        result = await self._session.execute(stmt)
        run = result.scalar_one_or_none()
        if run is not None:
            run.status = "running"
            run.started_at = datetime.now(UTC)
            await self._session.flush()

    async def mark_succeeded(
        self,
        run_id: UUID,
        output_payload: dict[str, object],
        state_after: dict[str, object],
        *,
        prompt_version: str | None = None,
        model_metadata: dict[str, object] | None = None,
    ) -> None:
        result = await self._session.execute(select(AgentRun).where(AgentRun.id == run_id))
        run = result.scalar_one_or_none()
        if run is not None:
            run.status = "succeeded"
            run.output_payload = output_payload
            run.state_after = state_after
            if prompt_version is not None:
                run.prompt_version = prompt_version
            if model_metadata is not None:
                run.model_metadata = model_metadata
            run.finished_at = datetime.now(UTC)
            await self._session.flush()

    async def mark_failed(
        self,
        run_id: UUID,
        error_payload: dict[str, object],
        *,
        model_metadata: dict[str, object] | None = None,
    ) -> None:
        result = await self._session.execute(select(AgentRun).where(AgentRun.id == run_id))
        run = result.scalar_one_or_none()
        if run is not None:
            run.status = "failed"
            run.error_payload = error_payload
            if model_metadata is not None:
                run.model_metadata = model_metadata
            run.finished_at = datetime.now(UTC)
            await self._session.flush()
