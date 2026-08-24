"""Normal-user portfolio entitlement and one-time success binding."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.auth.domain import AuthRole, EntitlementProjection
from oryxenai.auth.errors import (
    EntitlementBindingConflictError,
    PortfolioReadOnlyError,
)
from oryxenai.auth.models import AppUser, PortfolioEntitlement
from oryxenai.db.models.code_generator_development import CodeGeneratorDevelopmentRun
from oryxenai.db.models.portfolio_session import PortfolioSession


def admin_entitlement_projection() -> EntitlementProjection:
    """Return an explicit unlimited-capability projection for an active admin."""

    return EntitlementProjection(
        policy="unlimited_admin",
        portfolio_session_id=None,
        generation_run_id=None,
        successful_run_id=None,
        deleted_portfolio_session_id=None,
        consumed_at=None,
        project_deleted_at=None,
        can_create_portfolio=True,
        can_start_generation=True,
        can_retry_generation=True,
        can_regenerate=True,
        read_only=False,
        revision=0,
    )


class PortfolioEntitlementRepository:
    """Short transaction operations for the normal-user entitlement row."""

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
        """Lock an existing normal entitlement without repairing or creating it."""

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
            # A concurrent first login may have won the singleton insert.  The
            # savepoint is rolled back; the outer request transaction remains
            # usable and can take the authoritative row lock.
            current = await self.get_for_user(user_id, lock=True)
            if current is None:
                raise
            return current
        await self._session.refresh(row)
        return row

    async def get_or_create_session(
        self,
        *,
        user_id: UUID,
        name: str,
    ) -> PortfolioSession:
        entitlement = await self.ensure_for_normal_user(user_id)
        # The entitlement row is the first lock in the normal-user admission
        # path.  The session is created only after that lock is held.
        if entitlement.successful_run_id is not None:
            raise PortfolioReadOnlyError()
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

    async def bind_generation_run(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        run_id: UUID,
        revision: int,
        actor_user_id: UUID | None = None,
    ) -> PortfolioEntitlement:
        entitlement = await self.ensure_for_normal_user(user_id)
        if entitlement.portfolio_session_id != session_id:
            raise EntitlementBindingConflictError()
        if entitlement.successful_run_id is not None:
            raise PortfolioReadOnlyError()
        if entitlement.generation_run_id is not None:
            if entitlement.generation_run_id == run_id:
                return entitlement
            raise EntitlementBindingConflictError()
        if revision != entitlement.revision:
            raise EntitlementBindingConflictError()
        session_result = await self._session.execute(
            select(PortfolioSession)
            .where(
                PortfolioSession.id == session_id,
                PortfolioSession.owner_user_id == user_id,
                PortfolioSession.legacy_quarantined.is_(False),
            )
            .with_for_update()
        )
        if session_result.scalar_one_or_none() is None:
            raise EntitlementBindingConflictError()
        run_result = await self._session.execute(
            select(CodeGeneratorDevelopmentRun)
            .where(CodeGeneratorDevelopmentRun.id == run_id)
            .with_for_update()
        )
        run = run_result.scalar_one_or_none()
        if (
            run is None
            or str(run.run_mode) != "session"
            or run.portfolio_session_id != session_id
            or run.owner_user_id != user_id
            or run.actor_user_id is None
            or actor_user_id is None
            or run.actor_user_id != actor_user_id
            or run.authorization_context_version != 1
            or run.entitlement_revision != entitlement.revision + 1
        ):
            raise EntitlementBindingConflictError()
        entitlement.generation_run_id = run_id
        entitlement.revision += 1
        entitlement.updated_at = datetime.now(UTC)
        await self._session.flush()
        return entitlement

    async def assert_bound_retry(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        run_id: UUID,
        revision: int,
    ) -> PortfolioEntitlement:
        entitlement = await self.ensure_for_normal_user(user_id)
        if (
            entitlement.portfolio_session_id != session_id
            or entitlement.generation_run_id != run_id
            or entitlement.revision != revision
        ):
            raise EntitlementBindingConflictError()
        if entitlement.successful_run_id is not None:
            raise PortfolioReadOnlyError()
        return entitlement

    async def finalize_promoted_success(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        run_id: UUID,
        revision: int,
    ) -> PortfolioEntitlement:
        """Consume success exactly once after pointer/readback verification."""

        entitlement = await self.ensure_for_normal_user(user_id)
        if (
            entitlement.portfolio_session_id != session_id
            or entitlement.generation_run_id != run_id
            or entitlement.revision != revision
        ):
            raise EntitlementBindingConflictError()
        if entitlement.successful_run_id is not None:
            if entitlement.successful_run_id == run_id:
                return entitlement
            raise EntitlementBindingConflictError()
        entitlement.successful_run_id = run_id
        entitlement.consumed_at = datetime.now(UTC)
        entitlement.revision += 1
        entitlement.updated_at = datetime.now(UTC)
        await self._session.flush()
        return entitlement

    async def project_for_user(self, user_id: UUID) -> EntitlementProjection:
        entitlement = await self.ensure_for_normal_user(user_id)
        if entitlement.deleted_portfolio_session_id is not None:
            if entitlement.project_deleted_at is None:
                raise EntitlementBindingConflictError()
            return EntitlementProjection(
                policy="single_portfolio",
                portfolio_session_id=None,
                generation_run_id=None,
                successful_run_id=None,
                deleted_portfolio_session_id=entitlement.deleted_portfolio_session_id,
                consumed_at=entitlement.consumed_at,
                project_deleted_at=entitlement.project_deleted_at,
                can_create_portfolio=False,
                can_start_generation=False,
                can_retry_generation=False,
                can_regenerate=False,
                read_only=False,
                revision=entitlement.revision,
            )
        if (entitlement.successful_run_id is None) != (entitlement.consumed_at is None):
            raise EntitlementBindingConflictError()
        if (
            entitlement.successful_run_id is not None
            and entitlement.successful_run_id != entitlement.generation_run_id
        ):
            raise EntitlementBindingConflictError()
        if entitlement.portfolio_session_id is not None:
            session_result = await self._session.execute(
                select(PortfolioSession).where(
                    PortfolioSession.id == entitlement.portfolio_session_id
                )
            )
            session = session_result.scalar_one_or_none()
            if session is None or session.legacy_quarantined or session.owner_user_id != user_id:
                raise EntitlementBindingConflictError()
        run = None
        if entitlement.generation_run_id is not None:
            result = await self._session.execute(
                select(CodeGeneratorDevelopmentRun).where(
                    CodeGeneratorDevelopmentRun.id == entitlement.generation_run_id
                )
            )
            run = result.scalar_one_or_none()
            if (
                run is None
                or str(run.run_mode) != "session"
                or run.portfolio_session_id != entitlement.portfolio_session_id
                or run.owner_user_id != user_id
                or run.actor_user_id != user_id
                or run.authorization_context_version != 1
                or run.entitlement_revision is None
                or (
                    run.entitlement_revision != entitlement.revision
                    and not (
                        entitlement.successful_run_id == run.id
                        and run.entitlement_revision + 1 == entitlement.revision
                    )
                )
            ):
                raise EntitlementBindingConflictError()
        read_only = entitlement.successful_run_id is not None
        retryable_statuses = {"needs_attention", "preview_pending"}
        return EntitlementProjection(
            policy="single_portfolio",
            portfolio_session_id=entitlement.portfolio_session_id,
            generation_run_id=entitlement.generation_run_id,
            successful_run_id=entitlement.successful_run_id,
            deleted_portfolio_session_id=entitlement.deleted_portfolio_session_id,
            consumed_at=entitlement.consumed_at,
            project_deleted_at=entitlement.project_deleted_at,
            can_create_portfolio=entitlement.portfolio_session_id is None and not read_only,
            can_start_generation=entitlement.generation_run_id is None and not read_only,
            can_retry_generation=(
                run is not None and run.status in retryable_statuses and not read_only
            ),
            can_regenerate=False,
            read_only=read_only,
            revision=entitlement.revision,
        )


def mutable_entitlement_or_raise(projection: EntitlementProjection | None) -> None:
    """Shared dependency guard for product mutations."""

    if projection is not None and projection.read_only:
        raise PortfolioReadOnlyError()


def entitlement_for_role(role: AuthRole) -> EntitlementProjection | None:
    return admin_entitlement_projection() if role is AuthRole.ADMIN else None
