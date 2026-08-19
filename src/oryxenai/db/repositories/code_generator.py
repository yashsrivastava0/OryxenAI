"""Portfolio-session persistence for Code Generator attempts."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.agents.build_preparation.schemas import BuildPreparationState
from oryxenai.agents.code_generator.session_schemas import CodeGeneratorSessionState
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.repositories.code_generator_development import (
    CodeGeneratorDevelopmentRepository,
)
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository


class CodeGeneratorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.runs = CodeGeneratorDevelopmentRepository(session)
        self._sessions = PortfolioSessionRepository(session)

    async def get_session(self, session_id: UUID) -> PortfolioSession | None:
        return await self._sessions.get_by_id(session_id)

    async def get_build_preparation_state(self, session_id: UUID) -> BuildPreparationState:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise LookupError("session_not_found")
        raw = session.current_state.get("build_preparation")
        return BuildPreparationState.model_validate(raw if isinstance(raw, dict) else {})

    async def get_state(self, session_id: UUID) -> CodeGeneratorSessionState:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise LookupError("session_not_found")
        raw = session.current_state.get("code_generator")
        return CodeGeneratorSessionState.model_validate(raw if isinstance(raw, dict) else {})

    async def save_state(
        self,
        session_id: UUID,
        state: CodeGeneratorSessionState,
        expected_revision: int,
    ) -> PortfolioSession | None:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            return None
        new_state: dict[str, Any] = dict(session.current_state)
        new_state["code_generator"] = state.model_dump(mode="json")
        return await self._sessions.update_state(session_id, new_state, expected_revision)
