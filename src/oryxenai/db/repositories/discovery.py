"""Persistence helpers for the Discovery aggregate and source snapshots."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.agents.discovery.schemas import DiscoveryState
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.models.discovery_source_document import DiscoverySourceDocument
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.repositories.agent_runs import AgentRunRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository


class DiscoveryRepository:
    """Repository for Discovery state, source documents, and run history.

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
        return DiscoveryState.model_validate(raw)

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

    async def save_source(
        self,
        session_id: UUID,
        source_kind: str,
        content: str,
        content_hash: str,
        revision: int,
        *,
        language: str = "en",
        metadata: dict[str, object] | None = None,
    ) -> DiscoverySourceDocument:
        now = datetime.now(UTC)
        await self._session.execute(
            update(DiscoverySourceDocument)
            .where(
                DiscoverySourceDocument.portfolio_session_id == session_id,
                DiscoverySourceDocument.source_kind == source_kind,
                DiscoverySourceDocument.superseded_at.is_(None),
            )
            .values(superseded_at=now)
        )
        document = DiscoverySourceDocument(
            portfolio_session_id=session_id,
            source_kind=source_kind,
            revision=revision,
            content=content,
            content_hash=content_hash,
            language=language,
            source_metadata=metadata or {},
        )
        self._session.add(document)
        await self._session.flush()
        await self._session.refresh(document)
        return document

    async def get_current_source(
        self,
        session_id: UUID,
        source_kind: str,
    ) -> DiscoverySourceDocument | None:
        stmt = (
            select(DiscoverySourceDocument)
            .where(
                DiscoverySourceDocument.portfolio_session_id == session_id,
                DiscoverySourceDocument.source_kind == source_kind,
                DiscoverySourceDocument.superseded_at.is_(None),
            )
            .order_by(DiscoverySourceDocument.revision.desc())
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_sources_at_revision(
        self,
        session_id: UUID,
        revision: int,
    ) -> list[DiscoverySourceDocument]:
        stmt = (
            select(DiscoverySourceDocument)
            .where(
                DiscoverySourceDocument.portfolio_session_id == session_id,
                DiscoverySourceDocument.revision == revision,
            )
            .order_by(DiscoverySourceDocument.source_kind)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_latest_source_revision(self, session_id: UUID) -> int:
        stmt = (
            select(DiscoverySourceDocument.revision)
            .where(DiscoverySourceDocument.portfolio_session_id == session_id)
            .order_by(DiscoverySourceDocument.revision.desc())
        )
        value = (await self._session.execute(stmt)).scalar_one_or_none()
        return int(value or 0)

    async def create_run(self, run: AgentRun) -> AgentRun:
        return await self._runs.create(run)

    async def get_run(self, run_id: UUID) -> AgentRun | None:
        return await self._runs.get_by_id(run_id)

    async def find_run_by_idempotency(
        self,
        session_id: UUID,
        idempotency_key: str,
    ) -> AgentRun | None:
        return await self._runs.find_by_idempotency(session_id, "discovery", idempotency_key)

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
