from datetime import UTC, datetime
from uuid import uuid4

import pytest

from oryxenai.api.dependencies import (
    require_admin,
    require_onboarded_user,
    require_session_owner_or_admin,
)
from oryxenai.api.errors import AppError
from oryxenai.auth.authorization import PortfolioAccess
from oryxenai.auth.domain import AccountStatus, AuthRole, CurrentUser
from oryxenai.auth.errors import AdminRequiredError, OnboardingRequiredError
from oryxenai.db.models.portfolio_session import PortfolioSession


def _user(role: AuthRole) -> CurrentUser:
    subject = uuid4()
    return CurrentUser(
        id=uuid4(),
        supabase_user_id=subject,
        username="ready-user",
        role=role,
        status=AccountStatus.ACTIVE,
    )


def test_portfolio_access_is_immutable_and_admin_derived_from_local_role() -> None:
    session = PortfolioSession(
        owner_user_id=_user(AuthRole.USER).id,
        legacy_quarantined=False,
        name="Owned",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    normal_access = PortfolioAccess(actor=_user(AuthRole.USER), session=session)
    admin_access = PortfolioAccess(actor=_user(AuthRole.ADMIN), session=session)

    assert normal_access.is_admin is False
    assert admin_access.is_admin is True
    assert normal_access.session is session


@pytest.mark.asyncio
async def test_onboarded_and_admin_dependencies_use_local_projection() -> None:
    onboarded = _user(AuthRole.USER)
    assert await require_onboarded_user(onboarded) is onboarded

    onboarding = CurrentUser(
        id=onboarded.id,
        supabase_user_id=onboarded.supabase_user_id,
        username=None,
        role=AuthRole.USER,
        status=AccountStatus.ACTIVE,
    )
    with pytest.raises(OnboardingRequiredError):
        await require_onboarded_user(onboarding)

    admin = _user(AuthRole.ADMIN)
    assert await require_admin(admin) is admin
    with pytest.raises(AdminRequiredError):
        await require_admin(onboarded)


class _SessionRepo:
    def __init__(self, session: PortfolioSession | None) -> None:
        self.session = session
        self.owner_calls: list[tuple[object, object]] = []
        self.admin_calls: list[object] = []

    async def get_owned_by_id(self, session_id, owner_user_id):
        self.owner_calls.append((session_id, owner_user_id))
        if (
            self.session
            and self.session.id == session_id
            and self.session.owner_user_id == owner_user_id
        ):
            return self.session
        return None

    async def get_by_id_for_admin(self, session_id):
        self.admin_calls.append(session_id)
        if self.session and self.session.id == session_id:
            return self.session
        return None


@pytest.mark.asyncio
async def test_owner_access_matrix_is_database_scoped() -> None:
    owner = _user(AuthRole.USER)
    foreign = _user(AuthRole.USER)
    session = PortfolioSession(
        id=uuid4(),
        owner_user_id=owner.id,
        legacy_quarantined=False,
    )

    access = await require_session_owner_or_admin(
        str(session.id), user=owner, repo=_SessionRepo(session)
    )
    assert access.actor.id == owner.id
    assert access.session.id == session.id

    with pytest.raises(AppError) as foreign_error:
        await require_session_owner_or_admin(
            str(session.id), user=foreign, repo=_SessionRepo(session)
        )
    assert foreign_error.value.code == "SESSION_NOT_FOUND"

    legacy = PortfolioSession(id=uuid4(), owner_user_id=None, legacy_quarantined=True)
    admin = _user(AuthRole.ADMIN)
    admin_repo = _SessionRepo(legacy)
    admin_access = await require_session_owner_or_admin(str(legacy.id), user=admin, repo=admin_repo)
    assert admin_access.is_admin is True
    assert admin_access.session.id == legacy.id
    assert admin_repo.admin_calls == [legacy.id]

    with pytest.raises(AppError) as malformed_error:
        await require_session_owner_or_admin("not-a-uuid", user=owner, repo=_SessionRepo(None))
    assert malformed_error.value.code == "VALIDATION_ERROR"
