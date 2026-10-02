"""Persistence for the Code Generator: control-plane state, versions and chat.

Methods flush but never commit; the owning API request or worker step controls
the transaction. Anything that allocates a per-session counter (``seq``,
``version_number``) must run while holding the session row lock
(:meth:`lock_session`), the same lock the promote step and the reconciler take.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from oryxenai.agents.code_generator.state import CodeGeneratorState
from oryxenai.agents.content_architect.schemas import ContentArchitectState
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.models.site_version import PortfolioChatMessage, PortfolioSiteVersion
from oryxenai.db.repositories.agent_runs import AgentRunRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository

# Columns that can be large: never loaded for list views.
_HEAVY = (
    PortfolioSiteVersion.index_html,
    PortfolioSiteVersion.content_snapshot,
    PortfolioSiteVersion.manifest,
    PortfolioSiteVersion.trace,
    PortfolioSiteVersion.change_plan,
)


class SiteVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = PortfolioSessionRepository(session)
        self._runs = AgentRunRepository(session)

    # ── session + control-plane state ────────────────────────────────────────

    async def get_session(self, session_id: UUID) -> PortfolioSession | None:
        return await self._sessions.get_by_id(session_id)

    async def lock_session(self, session_id: UUID) -> PortfolioSession | None:
        """Reload the session row holding its mutation lock until commit."""
        stmt = (
            select(PortfolioSession)
            .where(PortfolioSession.id == session_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_state(self, session_id: UUID) -> CodeGeneratorState:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise LookupError("session_not_found")
        raw = session.current_state.get("code_generator")
        return (
            CodeGeneratorState.model_validate(raw)
            if isinstance(raw, dict)
            else CodeGeneratorState()
        )

    async def save_state(
        self, session_id: UUID, state: CodeGeneratorState, expected_revision: int
    ) -> PortfolioSession | None:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            return None
        new_state: dict[str, Any] = dict(session.current_state)
        new_state["code_generator"] = state.model_dump(mode="json")
        return await self._sessions.update_state(session_id, new_state, expected_revision)

    async def get_content_architect_state(self, session_id: UUID) -> ContentArchitectState:
        """Read-only view of the approved Content Architect result."""
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise LookupError("session_not_found")
        raw = session.current_state.get("content_architect")
        return (
            ContentArchitectState.model_validate(raw)
            if isinstance(raw, dict)
            else ContentArchitectState()
        )

    # ── runs ─────────────────────────────────────────────────────────────────

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

    async def mark_run_failed(self, run_id: UUID, error: dict[str, Any]) -> None:
        await self._runs.mark_failed(run_id, error)

    async def mark_run_cancelled(self, run_id: UUID, error: dict[str, Any]) -> None:
        await self._runs.mark_cancelled(run_id, error)

    # ── versions ─────────────────────────────────────────────────────────────

    async def next_seq(self, session_id: UUID) -> int:
        value = await self._session.scalar(
            select(func.coalesce(func.max(PortfolioSiteVersion.seq), 0)).where(
                PortfolioSiteVersion.portfolio_session_id == session_id
            )
        )
        return int(value or 0) + 1

    async def next_version_number(self, session_id: UUID) -> int:
        value = await self._session.scalar(
            select(func.coalesce(func.max(PortfolioSiteVersion.version_number), 0)).where(
                PortfolioSiteVersion.portfolio_session_id == session_id
            )
        )
        return int(value or 0) + 1

    async def get_version(
        self, version_id: UUID, *, session_id: UUID | None = None, light: bool = False
    ) -> PortfolioSiteVersion | None:
        stmt = select(PortfolioSiteVersion).where(PortfolioSiteVersion.id == version_id)
        if session_id is not None:
            stmt = stmt.where(PortfolioSiteVersion.portfolio_session_id == session_id)
        if light:
            stmt = stmt.options(*(defer(column) for column in _HEAVY))
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_versions(
        self, session_id: UUID, *, limit: int = 60
    ) -> list[PortfolioSiteVersion]:
        stmt = (
            select(PortfolioSiteVersion)
            .where(PortfolioSiteVersion.portfolio_session_id == session_id)
            .options(*(defer(column) for column in _HEAVY))
            .order_by(PortfolioSiteVersion.seq.desc())
            .limit(max(1, min(limit, 200)))
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def create_version(
        self,
        *,
        version_id: UUID,
        session_id: UUID,
        origin: str,
        status: str,
        instruction: str,
        content_snapshot: dict[str, Any],
        content_sha256: str,
        theme_id: str,
        run_id: UUID | None,
        job_id: UUID | None,
        parent_version_id: UUID | None = None,
        change_plan: dict[str, Any] | None = None,
    ) -> PortfolioSiteVersion:
        """Insert a version row; the caller holds the session lock (``seq`` is allocated here)."""
        row = PortfolioSiteVersion(
            id=version_id,
            portfolio_session_id=session_id,
            seq=await self.next_seq(session_id),
            origin=origin,
            status=status,
            instruction=instruction,
            parent_version_id=parent_version_id,
            change_plan=change_plan or {},
            content_snapshot=content_snapshot,
            content_sha256=content_sha256,
            theme_id=theme_id,
            run_id=run_id,
            job_id=job_id,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def set_version_status(
        self, version_id: UUID, status: str, *, trace: dict[str, Any] | None = None
    ) -> None:
        values: dict[str, Any] = {"status": status, "updated_at": datetime.now(UTC)}
        if trace is not None:
            values["trace"] = trace
        await self._session.execute(
            update(PortfolioSiteVersion)
            .where(
                PortfolioSiteVersion.id == version_id,
                PortfolioSiteVersion.status.notin_(("ready", "failed", "cancelled", "no_change")),
            )
            .values(**values)
        )

    async def mark_version_ready(
        self,
        version: PortfolioSiteVersion,
        *,
        version_number: int,
        lang: str,
        index_html: str,
        index_sha256: str,
        theme_sha256: str,
        manifest: dict[str, Any],
        receipt: dict[str, Any],
        trace: dict[str, Any],
    ) -> None:
        now = datetime.now(UTC)
        version.status = "ready"
        version.version_number = version_number
        version.lang = lang
        version.index_html = index_html
        version.index_sha256 = index_sha256
        version.theme_sha256 = theme_sha256
        version.manifest = manifest
        version.receipt = receipt
        version.trace = trace
        version.error = None
        version.completed_at = now
        version.updated_at = now
        await self._session.flush()

    async def mark_version_failed(
        self,
        version_id: UUID,
        *,
        error: dict[str, Any],
        trace: dict[str, Any] | None = None,
        receipt: dict[str, Any] | None = None,
        status: str = "failed",
    ) -> None:
        values: dict[str, Any] = {
            "status": status,
            "error": error,
            "completed_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        if trace is not None:
            values["trace"] = trace
        if receipt is not None:
            values["receipt"] = receipt
        await self._session.execute(
            update(PortfolioSiteVersion)
            .where(
                PortfolioSiteVersion.id == version_id,
                PortfolioSiteVersion.status.notin_(("ready", "no_change")),
            )
            .values(**values)
        )

    async def count_versions(self, session_id: UUID) -> int:
        value = await self._session.scalar(
            select(func.count())
            .select_from(PortfolioSiteVersion)
            .where(PortfolioSiteVersion.portfolio_session_id == session_id)
        )
        return int(value or 0)

    # ── chat ─────────────────────────────────────────────────────────────────

    async def append_chat(
        self,
        session_id: UUID,
        *,
        role: str,
        body: str,
        kind: str = "message",
        version_id: UUID | None = None,
        client_message_id: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> PortfolioChatMessage:
        """Append a transcript row; the caller holds the session lock.

        ``version_id`` is only linked when that version row exists: a build that
        never reached a worker has no row yet, and the message still belongs in
        the transcript.
        """
        if version_id is not None:
            exists = await self._session.scalar(
                select(PortfolioSiteVersion.id).where(PortfolioSiteVersion.id == version_id)
            )
            if exists is None:
                version_id = None
        seq = int(
            (
                await self._session.scalar(
                    select(func.coalesce(func.max(PortfolioChatMessage.seq), 0)).where(
                        PortfolioChatMessage.portfolio_session_id == session_id
                    )
                )
            )
            or 0
        )
        row = PortfolioChatMessage(
            portfolio_session_id=session_id,
            seq=seq + 1,
            role=role,
            kind=kind,
            body=body,
            version_id=version_id,
            client_message_id=client_message_id,
            meta=meta or {},
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_chat(self, session_id: UUID, *, limit: int = 60) -> list[PortfolioChatMessage]:
        stmt = (
            select(PortfolioChatMessage)
            .where(PortfolioChatMessage.portfolio_session_id == session_id)
            .order_by(PortfolioChatMessage.seq.desc())
            .limit(max(1, min(limit, 200)))
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        rows.reverse()
        return rows

    # ── cleanup ──────────────────────────────────────────────────────────────

    async def delete_for_session(self, session_id: UUID) -> None:
        """Remove every version and chat row (pipeline reset keeps the session row)."""
        await self._session.execute(
            delete(PortfolioChatMessage).where(
                PortfolioChatMessage.portfolio_session_id == session_id
            )
        )
        await self._session.execute(
            delete(PortfolioSiteVersion).where(
                PortfolioSiteVersion.portfolio_session_id == session_id
            )
        )
        await self._session.flush()
