"""Persistence helpers for the Content Architect aggregate."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.agents.content_architect.schemas import ContentArchitectState
from oryxenai.agents.discovery.schemas import DiscoveryState
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.repositories.agent_runs import AgentRunRepository
from oryxenai.db.repositories.discovery import DiscoveryRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository


class ContentArchitectRepository:
    """Repository for Content Architect state and run history.

    Methods flush but never commit. The owning API or worker service controls
    the transaction boundary. Composes a read-only DiscoveryRepository to
    read the approved Discovery snapshot — this repository never writes to
    Discovery's state.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = PortfolioSessionRepository(session)
        self._runs = AgentRunRepository(session)
        self._discovery = DiscoveryRepository(session)

    async def get_session(self, session_id: UUID) -> PortfolioSession | None:
        return await self._sessions.get_by_id(session_id)

    async def get_discovery_snapshot(self, session_id: UUID) -> DiscoveryState:
        """Read-only access to Discovery's current state for the same session."""
        return await self._discovery.get_discovery_state(session_id)

    async def get_content_architect_state(self, session_id: UUID) -> ContentArchitectState:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise LookupError("session_not_found")
        raw = session.current_state.get("content_architect")
        if not isinstance(raw, dict):
            return ContentArchitectState()
        return ContentArchitectState.model_validate(raw)

    async def save_content_architect_state(
        self,
        session_id: UUID,
        state: ContentArchitectState,
        expected_revision: int,
    ) -> PortfolioSession | None:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            return None
        new_state: dict[str, Any] = dict(session.current_state)
        new_state["content_architect"] = state.model_dump(mode="json")
        return await self._sessions.update_state(session_id, new_state, expected_revision)

    async def create_run(self, run: AgentRun) -> AgentRun:
        return await self._runs.create(run)

    async def get_run(self, run_id: UUID) -> AgentRun | None:
        return await self._runs.get_by_id(run_id)

    async def mark_run_started(self, run_id: UUID) -> None:
        await self._runs.mark_started(run_id)

    async def mark_run_succeeded(
        self,
        run_id: UUID,
        output: dict[str, Any],
        state_after: dict[str, Any],
        *,
        prompt_version: str | None = None,
        model_metadata: dict[str, Any] | None = None,
    ) -> None:
        await self._runs.mark_succeeded(
            run_id,
            output,
            state_after,
            prompt_version=prompt_version,
            model_metadata=model_metadata,
        )

    async def mark_run_failed(
        self,
        run_id: UUID,
        error_payload: dict[str, Any],
        *,
        model_metadata: dict[str, Any] | None = None,
    ) -> None:
        await self._runs.mark_failed(run_id, error_payload, model_metadata=model_metadata)
