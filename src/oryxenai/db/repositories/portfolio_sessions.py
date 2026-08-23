"""PortfolioSession repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.db.models.portfolio_session import PortfolioSession


class PortfolioSessionRepository:
    """Repository for portfolio_sessions table operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_owned(
        self,
        owner_user_id: UUID,
        name: str = "Untitled session",
    ) -> PortfolioSession:
        """Create a product session owned by the authenticated local user."""
        obj = PortfolioSession(
            owner_user_id=owner_user_id,
            legacy_quarantined=False,
            name=name,
        )
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def create(self, name: str = "Untitled session") -> PortfolioSession:
        """Create a quarantined legacy row for trusted internal callers.

        Product API routes must use :meth:`create_owned`.  This compatibility
        method keeps fixtures and older internal tooling from accidentally
        assigning ownership to a caller-controlled value.
        """
        obj = PortfolioSession(name=name)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def get_by_id(self, session_id: UUID) -> PortfolioSession | None:
        """Legacy internal aggregate lookup.

        Route handlers must use an authorization-scoped method below.  Agent
        services and workers still need the aggregate lookup until the later
        worker-fencing phase adds owner/actor snapshots to their jobs.
        """
        return await self.get_by_id_internal(session_id)

    async def get_by_id_internal(self, session_id: UUID) -> PortfolioSession | None:
        stmt = select(PortfolioSession).where(PortfolioSession.id == session_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 20) -> list[PortfolioSession]:
        """Legacy internal list retained for non-product callers."""
        return await self.list_recent_for_admin(limit=limit)

    async def get_owned_by_id(
        self,
        session_id: UUID,
        owner_user_id: UUID,
    ) -> PortfolioSession | None:
        stmt = select(PortfolioSession).where(
            PortfolioSession.id == session_id,
            PortfolioSession.owner_user_id == owner_user_id,
            PortfolioSession.legacy_quarantined.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_admin(self, session_id: UUID) -> PortfolioSession | None:
        """Return any session, including quarantined legacy rows."""
        return await self.get_by_id_internal(session_id)

    async def list_owned_recent(
        self,
        owner_user_id: UUID,
        limit: int = 20,
    ) -> list[PortfolioSession]:
        limit = max(1, min(limit, 100))
        stmt = (
            select(PortfolioSession)
            .where(
                PortfolioSession.owner_user_id == owner_user_id,
                PortfolioSession.legacy_quarantined.is_(False),
            )
            .order_by(PortfolioSession.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_recent_for_admin(self, limit: int = 20) -> list[PortfolioSession]:
        limit = max(1, min(limit, 100))
        stmt = select(PortfolioSession).order_by(PortfolioSession.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_state(
        self,
        session_id: UUID,
        new_state: dict[str, object],
        expected_revision: int,
    ) -> PortfolioSession | None:
        """Optimistically update current_state and increment revision.

        Returns the updated session, or None if the revision no longer
        matches (concurrent modification).
        """
        stmt = (
            update(PortfolioSession)
            .where(
                PortfolioSession.id == session_id,
                PortfolioSession.revision == expected_revision,
            )
            .values(
                current_state=new_state,
                revision=expected_revision + 1,
                updated_at=datetime.now(UTC),
            )
            .returning(PortfolioSession)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            await self._session.refresh(row)
        return row
