from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from oryxenai.auth.domain import AuthRole, ProviderIdentity
from oryxenai.auth.errors import AccessNotApprovedError, AccountSuspendedError
from oryxenai.auth.jwt import VerifiedToken
from oryxenai.auth.models import AppUser
from oryxenai.auth.service import AuthService
from oryxenai.core.settings import AuthConfig

SUBJECT = UUID("11111111-1111-4111-8111-111111111111")


def _user(*, role: str = "user", status: str = "active", username: str | None = None) -> AppUser:
    now = datetime.now(UTC)
    return AppUser(
        id=uuid4(),
        supabase_user_id=SUBJECT,
        primary_email="person@example.com",
        username=username,
        role=role,
        status=status,
        onboarding_completed_at=now if username else None,
        deleted_at=None,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )


class _Verifier:
    async def verify(self, token: str) -> VerifiedToken:
        return VerifiedToken(subject=SUBJECT)


class _Provider:
    def __init__(self, identity: ProviderIdentity) -> None:
        self.identity = identity
        self.calls = 0

    async def get_user(self, token: str, expected_subject: UUID) -> ProviderIdentity:
        self.calls += 1
        return self.identity


class _Repo:
    def __init__(self, existing: AppUser | None = None) -> None:
        self.user = existing
        self.provision_calls = 0

    async def get_by_subject(self, subject: UUID, *, lock: bool = False) -> AppUser | None:
        return self.user

    async def touch(self, user: AppUser) -> AppUser:
        return user

    async def provision_or_get(self, **kwargs: object) -> tuple[AppUser, bool]:
        self.provision_calls += 1
        self.user = _user(role=str(kwargs["role"]))
        return self.user, True

    async def claim_username(self, user_id: UUID, username: str) -> AppUser:
        assert self.user is not None
        self.user.username = username
        return self.user


def _service(monkeypatch: pytest.MonkeyPatch, repo: _Repo, provider: _Provider) -> AuthService:
    monkeypatch.setattr("oryxenai.auth.service.AuthRepository", lambda _db: repo)
    return AuthService(
        db=object(),
        config=AuthConfig(),
        verifier=_Verifier(),
        provider=provider,
        admin_emails=("admin@example.com", "second-admin@example.com"),
        allowed_emails=("person@example.com",),
    )


@pytest.mark.asyncio
async def test_new_admission_uses_verified_email_not_user_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _Provider(
        ProviderIdentity(subject=SUBJECT, email="person@example.com", display_name="Admin")
    )
    repo = _Repo()
    service = _service(monkeypatch, repo, provider)

    current = await service.current_user("token")

    assert current.role is AuthRole.USER
    assert repo.provision_calls == 1
    assert provider.calls == 1

    provider.identity = ProviderIdentity(subject=SUBJECT, email="not-approved@example.com")
    repo = _Repo()
    monkeypatch.setattr("oryxenai.auth.service.AuthRepository", lambda _db: repo)
    service = AuthService(
        db=object(),
        config=AuthConfig(),
        verifier=_Verifier(),
        provider=provider,
        admin_emails=("admin@example.com", "second-admin@example.com"),
        allowed_emails=("person@example.com",),
    )
    with pytest.raises(AccessNotApprovedError):
        await service.current_user("token")
    assert repo.provision_calls == 0


@pytest.mark.asyncio
async def test_bootstrap_email_gets_admin_role_once(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _Provider(
        ProviderIdentity(subject=SUBJECT, email="admin@example.com", display_name="Admin")
    )
    repo = _Repo()
    service = _service(monkeypatch, repo, provider)

    current = await service.current_user("token")

    assert current.role is AuthRole.ADMIN
    assert repo.user is not None
    assert repo.user.role == AuthRole.ADMIN.value


@pytest.mark.asyncio
async def test_open_admission_provisions_a_verified_non_allowlisted_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _Provider(ProviderIdentity(subject=SUBJECT, email="new-person@example.com"))
    repo = _Repo()
    monkeypatch.setattr("oryxenai.auth.service.AuthRepository", lambda _db: repo)
    service = AuthService(
        db=object(),
        config=AuthConfig(admission_mode="open"),
        verifier=_Verifier(),
        provider=provider,
        admin_emails=("admin@example.com", "second-admin@example.com"),
        allowed_emails=(),
    )

    current = await service.current_user("token")

    assert current.role is AuthRole.USER
    assert repo.provision_calls == 1


@pytest.mark.asyncio
async def test_existing_database_role_is_authoritative(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _Repo(existing=_user(role="admin", username="owner"))
    provider = _Provider(ProviderIdentity(subject=SUBJECT, email="person@example.com"))
    service = _service(monkeypatch, repo, provider)

    current = await service.current_user("token")

    assert current.role is AuthRole.ADMIN
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_suspended_local_account_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _Repo(existing=_user(status="suspended"))
    service = _service(
        monkeypatch, repo, _Provider(ProviderIdentity(SUBJECT, "person@example.com"))
    )

    with pytest.raises(AccountSuspendedError):
        await service.current_user("token")
