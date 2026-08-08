"""Persistence helpers for the Visual Design Director aggregate."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.agents.content_architect.schemas import ContentArchitectState
from oryxenai.agents.visual_design_director.schemas import VisualDesignDirectorState
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.repositories.agent_runs import AgentRunRepository
from oryxenai.db.repositories.content_architect import ContentArchitectRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository


class VisualDesignDirectorRepository:
    """Repository for Visual Design Director state and run history.

    Methods flush but never commit. The owning API or worker service controls
    the transaction boundary. Composes a ContentArchitectRepository, used
    read-only by convention (only get_content_architect_state is ever
    called) to read the approved Content Architect snapshot — this
    repository never writes to Content Architect's state.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = PortfolioSessionRepository(session)
        self._runs = AgentRunRepository(session)
        self._content_architect = ContentArchitectRepository(session)

    async def get_session(self, session_id: UUID) -> PortfolioSession | None:
        return await self._sessions.get_by_id(session_id)

    async def get_content_architect_snapshot(self, session_id: UUID) -> ContentArchitectState:
        """Read-only access to Content Architect's current state for the same session."""
        return await self._content_architect.get_content_architect_state(session_id)

    async def get_visual_design_director_state(self, session_id: UUID) -> VisualDesignDirectorState:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise LookupError("session_not_found")
        raw = session.current_state.get("visual_design_director")
        if not isinstance(raw, dict):
            return VisualDesignDirectorState()
        return VisualDesignDirectorState.model_validate(raw)

    async def save_visual_design_director_state(
        self,
        session_id: UUID,
        state: VisualDesignDirectorState,
        expected_revision: int,
    ) -> PortfolioSession | None:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            return None
        new_state: dict[str, Any] = dict(session.current_state)
        new_state["visual_design_director"] = state.model_dump(mode="json")
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
