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

    async def create(self, name: str = "Untitled session") -> PortfolioSession:
        obj = PortfolioSession(name=name)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def get_by_id(self, session_id: UUID) -> PortfolioSession | None:
        stmt = select(PortfolioSession).where(PortfolioSession.id == session_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 20) -> list[PortfolioSession]:
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
