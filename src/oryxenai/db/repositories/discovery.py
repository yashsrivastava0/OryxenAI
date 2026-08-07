"""Persistence helpers for the Discovery aggregate."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.agents.discovery.schemas import DiscoveryState
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.repositories.agent_runs import AgentRunRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository


class DiscoveryRepository:
    """Repository for Discovery state and run history.

    Methods flush but never commit. The owning API or worker service controls
    the transaction boundary.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = PortfolioSessionRepository(session)
        self._runs = AgentRunRepository(session)

    async def get_session(self, session_id: UUID) -> PortfolioSession | None:
        return await self._sessions.get_by_id(session_id)

    async def get_discovery_state(self, session_id: UUID) -> DiscoveryState:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise LookupError("session_not_found")
        raw = session.current_state.get("discovery")
        if not isinstance(raw, dict):
            return DiscoveryState()
        return DiscoveryState.model_validate(self._migrate_state_shape(raw))

    @staticmethod
    def _migrate_state_shape(raw: dict[str, Any]) -> dict[str, Any]:
        """One-time shape migration for in-flight sessions (v1 -> v2).

        Old state stored `questions` and `demo`; new state stores `operation_a`
        and `memory`. Old rows are adapted in place before validation.
        """
        if "operation_a" not in raw and "questions" in raw:
            questions = raw.get("questions")
            if isinstance(questions, dict):
                raw["operation_a"] = {"items": questions.get("items", [])}
        raw.pop("demo", None)
        return raw

    async def save_discovery_state(
        self,
        session_id: UUID,
        state: DiscoveryState,
        expected_revision: int,
    ) -> PortfolioSession | None:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            return None
        new_state: dict[str, Any] = dict(session.current_state)
        new_state["discovery"] = state.model_dump(mode="json")
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
