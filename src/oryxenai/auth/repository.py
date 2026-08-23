"""Short-transaction repositories for local auth admission and onboarding."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.auth.domain import AuthRole
from oryxenai.auth.errors import (
    AccessNotApprovedError,
    AccountDeletedError,
    UserCapacityReachedError,
    UsernameLockedError,
    UsernameTakenError,
)
from oryxenai.auth.models import AppUser, AppUserCapacity

CAPACITY_SCOPE = "normal-users"


class AuthRepository:
    """Database operations for the immutable-subject auth boundary."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_subject(self, subject: UUID, *, lock: bool = False) -> AppUser | None:
        stmt = select(AppUser).where(AppUser.supabase_user_id == subject)
        if lock:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, *, lock: bool = False) -> AppUser | None:
        stmt = select(AppUser).where(AppUser.primary_email == email)
        if lock:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def touch(self, user: AppUser) -> AppUser:
        now = datetime.now(UTC)
        user.last_seen_at = now
        user.updated_at = now
        await self._session.flush()
        return user

    async def _lock_capacity(self, expected_limit: int) -> AppUserCapacity:
        """Ensure and lock the singleton row before counting normal users."""
        result = await self._session.execute(
            select(AppUserCapacity).where(AppUserCapacity.scope == CAPACITY_SCOPE)
        )
        capacity = result.scalar_one_or_none()
        if capacity is None:
            try:
                async with self._session.begin_nested():
                    self._session.add(
                        AppUserCapacity(
                            scope=CAPACITY_SCOPE,
                            normal_user_limit=expected_limit,
                            revision=0,
                        )
                    )
                    await self._session.flush()
            except IntegrityError:
                # Another admission transaction initialized the singleton.
                pass
            result = await self._session.execute(
                select(AppUserCapacity).where(AppUserCapacity.scope == CAPACITY_SCOPE)
            )
            capacity = result.scalar_one_or_none()
        if capacity is None:
            raise RuntimeError("Authentication capacity row could not be initialized.")
        capacity = await self._session.get(AppUserCapacity, CAPACITY_SCOPE, with_for_update=True)
        if capacity is None:
            raise RuntimeError("Authentication capacity row disappeared during admission.")
        if capacity.normal_user_limit != expected_limit:
            raise RuntimeError("Authentication capacity policy does not match configuration.")
        return capacity

    async def provision_or_get(
        self,
        *,
        subject: UUID,
        email: str,
        role: AuthRole,
        normal_user_limit: int,
    ) -> tuple[AppUser, bool]:
        """Upsert a subject while serializing the normal-user admission gate."""
        # Lock order begins with capacity for every admission path. Admins do
        # not consume it, but sharing the lock makes same-subject provisioning
        # deterministic across callback tabs without holding an HTTP call.
        await self._lock_capacity(normal_user_limit)
        existing = await self.get_by_subject(subject, lock=True)
        if existing is not None:
            return existing, False

        tombstone = await self.get_by_email(email, lock=True)
        if tombstone is not None and tombstone.status == "deleted":
            raise AccountDeletedError()

        if role is AuthRole.USER:
            count_result = await self._session.execute(
                select(func.count(AppUser.id)).where(
                    AppUser.role == AuthRole.USER.value,
                    AppUser.status.in_(("active", "suspended", "deletion_pending")),
                )
            )
            count = int(count_result.scalar_one())
            if count >= normal_user_limit:
                raise UserCapacityReachedError()

        now = datetime.now(UTC)
        user = AppUser(
            supabase_user_id=subject,
            primary_email=email,
            role=role.value,
            status="active",
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(user)
                await self._session.flush()
        except IntegrityError as exc:
            # The capacity lock makes this uncommon, but preserve a safe
            # idempotent result if a database constraint wins a race.
            existing = await self.get_by_subject(subject, lock=True)
            if existing is not None:
                return existing, False
            existing_email = await self.get_by_email(email, lock=True)
            if existing_email is not None:
                if existing_email.status == "deleted":
                    raise AccountDeletedError() from exc
                raise AccessNotApprovedError() from exc
            raise
        await self._session.refresh(user)
        return user, True

    async def claim_username(self, user_id: UUID, username: str) -> AppUser:
        """Atomically claim the globally unique onboarding username."""
        user = await self._session.get(AppUser, user_id, with_for_update=True)
        if user is None:
            raise RuntimeError("The authenticated local user disappeared.")
        if user.username is not None:
            if user.username == username:
                await self.touch(user)
                return user
            raise UsernameLockedError()

        try:
            async with self._session.begin_nested():
                user.username = username
                user.onboarding_completed_at = datetime.now(UTC)
                user.updated_at = datetime.now(UTC)
                await self._session.flush()
        except IntegrityError as exc:
            raise UsernameTakenError() from exc
        await self._session.refresh(user)
        return user
