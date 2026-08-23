"""Just-in-time admission and safe local user projections."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.auth.domain import (
    AccountStatus,
    AuthInputError,
    AuthRole,
    CurrentUser,
    ProviderIdentity,
    normalize_username,
)
from oryxenai.auth.errors import (
    AccessNotApprovedError,
    AccountDeletedError,
    AccountSuspendedError,
)
from oryxenai.auth.jwt import VerifiedToken
from oryxenai.auth.models import AppUser
from oryxenai.auth.provider import ProviderIdentityClient
from oryxenai.auth.repository import AuthRepository
from oryxenai.core.settings import AuthConfig


class JwtVerifierClient(Protocol):
    async def verify(self, token: str) -> VerifiedToken: ...


class AuthService:
    """Application auth service; provider identity is resolved before DB locks."""

    def __init__(
        self,
        *,
        db: AsyncSession,
        config: AuthConfig,
        verifier: JwtVerifierClient,
        provider: ProviderIdentityClient,
        admin_emails: tuple[str, ...],
        allowed_emails: tuple[str, ...],
    ) -> None:
        self._repo = AuthRepository(db)
        self._config = config
        self._verifier = verifier
        self._provider = provider
        self._admin_emails = frozenset(admin_emails)
        self._allowed_emails = frozenset(allowed_emails)

    async def current_user(self, token: str) -> CurrentUser:
        verified = await self._verifier.verify(token)
        # A first-login provider lookup must happen before any database row
        # lock. Existing users are reloaded under a lock so database role and
        # status remain authoritative for the rest of this short transaction.
        user = await self._repo.get_by_subject(verified.subject)
        if user is not None:
            locked_user = await self._repo.get_by_subject(verified.subject, lock=True)
            user = locked_user
        if user is None:
            # This HTTP call is intentionally before provision_or_get's
            # capacity/app-user locks.
            identity = await self._provider.get_user(token, verified.subject)
            if identity.subject != verified.subject:
                raise AccessNotApprovedError()
            role = self._role_for(identity)
            user, _ = await self._repo.provision_or_get(
                subject=verified.subject,
                email=identity.email,
                role=role,
                normal_user_limit=self._config.normal_user_limit,
            )
        else:
            await self._repo.touch(user)
        return self._to_current_user(user)

    def _role_for(self, identity: ProviderIdentity) -> AuthRole:
        if identity.email in self._admin_emails:
            return AuthRole.ADMIN
        if identity.email in self._allowed_emails:
            return AuthRole.USER
        raise AccessNotApprovedError()

    @staticmethod
    def _to_current_user(user: AppUser) -> CurrentUser:
        try:
            role = AuthRole(user.role)
            status = AccountStatus(user.status)
        except ValueError as exc:
            raise RuntimeError("Invalid local authentication state.") from exc
        if status is AccountStatus.DELETED:
            raise AccountDeletedError()
        if status in {AccountStatus.SUSPENDED, AccountStatus.DELETION_PENDING}:
            raise AccountSuspendedError()
        return CurrentUser(
            id=user.id,
            supabase_user_id=user.supabase_user_id,
            username=user.username,
            role=role,
            status=status,
        )

    async def claim_username(self, token: str, raw_username: str) -> CurrentUser:
        current = await self.current_user(token)
        try:
            username = normalize_username(raw_username)
        except AuthInputError as exc:
            # Keep the existing structured envelope while not exposing regex
            # implementation details or another user's identity.
            from oryxenai.api.errors import ValidationError

            raise ValidationError(str(exc), details={"field": "username"}) from exc
        user = await self._repo.claim_username(current.id, username)
        return self._to_current_user(user)
