"""Normal-user single-portfolio entitlement and lifecycle binding."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.auth.domain import AuthRole, EntitlementProjection
from oryxenai.auth.errors import EntitlementBindingConflictError
from oryxenai.auth.models import AppUser, PortfolioEntitlement
from oryxenai.db.models.portfolio_session import PortfolioSession


def admin_entitlement_projection() -> EntitlementProjection:
    """Return the unlimited portfolio capability for an active administrator."""

    return EntitlementProjection(
        policy="unlimited_admin",
        portfolio_session_id=None,
        deleted_portfolio_session_id=None,
        project_deleted_at=None,
        can_create_portfolio=True,
        revision=0,
    )


class PortfolioEntitlementRepository:
    """Short transaction operations for one user's portfolio slot."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_user(
        self, user_id: UUID, *, lock: bool = False
    ) -> PortfolioEntitlement | None:
        stmt = select(PortfolioEntitlement).where(PortfolioEntitlement.user_id == user_id)
        if lock:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def lock_for_normal_user(self, user_id: UUID) -> PortfolioEntitlement:
        entitlement = await self.get_for_user(user_id, lock=True)
        if entitlement is None:
            raise EntitlementBindingConflictError()
        return entitlement

    async def ensure_for_normal_user(self, user_id: UUID) -> PortfolioEntitlement:
        user_result = await self._session.execute(
            select(AppUser.role, AppUser.status).where(AppUser.id == user_id)
        )
        user_row = user_result.one_or_none()
        if user_row is None or user_row[0] != AuthRole.USER.value or user_row[1] != "active":
            raise EntitlementBindingConflictError()
        current = await self.get_for_user(user_id, lock=True)
        if current is not None:
            return current
        row = PortfolioEntitlement(user_id=user_id)
        try:
            async with self._session.begin_nested():
                self._session.add(row)
                await self._session.flush()
        except IntegrityError:
            current = await self.get_for_user(user_id, lock=True)
            if current is None:
                raise
            return current
        await self._session.refresh(row)
        return row

    async def get_or_create_session(self, *, user_id: UUID, name: str) -> PortfolioSession:
        entitlement = await self.ensure_for_normal_user(user_id)
        if entitlement.deleted_portfolio_session_id is not None:
            raise EntitlementBindingConflictError()
        if entitlement.portfolio_session_id is not None:
            result = await self._session.execute(
                select(PortfolioSession)
                .where(
                    PortfolioSession.id == entitlement.portfolio_session_id,
                    PortfolioSession.owner_user_id == user_id,
                    PortfolioSession.legacy_quarantined.is_(False),
                )
                .with_for_update()
            )
            session = result.scalar_one_or_none()
            if session is None:
                raise EntitlementBindingConflictError()
            return session

        session = PortfolioSession(
            owner_user_id=user_id,
            legacy_quarantined=False,
            session_mode="owned",
            name=name,
        )
        self._session.add(session)
        await self._session.flush()
        entitlement.portfolio_session_id = session.id
        entitlement.revision += 1
        entitlement.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(session)
        return session

    async def project_for_user(self, user_id: UUID) -> EntitlementProjection:
        entitlement = await self.ensure_for_normal_user(user_id)
        if entitlement.deleted_portfolio_session_id is not None:
            if (
                entitlement.project_deleted_at is None
                or entitlement.portfolio_session_id is not None
            ):
                raise EntitlementBindingConflictError()
            return EntitlementProjection(
                policy="single_portfolio",
                portfolio_session_id=None,
                deleted_portfolio_session_id=entitlement.deleted_portfolio_session_id,
                project_deleted_at=entitlement.project_deleted_at,
                can_create_portfolio=False,
                revision=entitlement.revision,
            )

        if entitlement.portfolio_session_id is not None:
            result = await self._session.execute(
                select(PortfolioSession).where(
                    PortfolioSession.id == entitlement.portfolio_session_id
                )
            )
            session = result.scalar_one_or_none()
            if session is None or session.legacy_quarantined or session.owner_user_id != user_id:
                raise EntitlementBindingConflictError()

        return EntitlementProjection(
            policy="single_portfolio",
            portfolio_session_id=entitlement.portfolio_session_id,
            deleted_portfolio_session_id=None,
            project_deleted_at=None,
            can_create_portfolio=entitlement.portfolio_session_id is None,
            revision=entitlement.revision,
        )
