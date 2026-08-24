"""PostgreSQL-backed ownership and route-isolation checks for Phase 2."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryxenai.api.dependencies import get_current_user, get_pipeline_user, require_onboarded_user
from oryxenai.auth.domain import AccountStatus, AuthRole, CurrentUser
from oryxenai.auth.models import AppUser
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository
from oryxenai.main import create_app

pytestmark = pytest.mark.integration


def _projection(user_id: UUID, subject: UUID, username: str, role: AuthRole) -> CurrentUser:
    return CurrentUser(
        id=user_id,
        supabase_user_id=subject,
        username=username,
        role=role,
        status=AccountStatus.ACTIVE,
    )


async def _insert_user(session: AsyncSession, user: CurrentUser, email: str) -> None:
    session.add(
        AppUser(
            id=user.id,
            supabase_user_id=user.supabase_user_id,
            primary_email=email,
            username=user.username,
            role=user.role.value,
            status=user.status.value,
            onboarding_completed_at=datetime.now(UTC),
        )
    )
    await session.flush()


@pytest.mark.asyncio
async def test_owner_and_admin_session_isolation(test_engine) -> None:
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    owner = _projection(uuid4(), uuid4(), "owner-a", AuthRole.USER)
    foreign = _projection(uuid4(), uuid4(), "owner-b", AuthRole.USER)
    admin = _projection(uuid4(), uuid4(), "admin-user", AuthRole.ADMIN)

    async with factory() as session:
        await _insert_user(session, owner, "owner-a@example.com")
        await _insert_user(session, foreign, "owner-b@example.com")
        await _insert_user(session, admin, "admin@example.com")
        repo = PortfolioSessionRepository(session)
        owner_session = await repo.create_owned(owner.id, name="Owner A")
        foreign_session = await repo.create_owned(foreign.id, name="Owner B")
        admin_session = await repo.create_owned(admin.id, name="Admin")
        legacy_session = await repo.create(name="Legacy")
        await session.commit()

    app = create_app()
    app.state.sessionmaker = factory

    def set_identity(user: CurrentUser) -> None:
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_pipeline_user] = lambda: user
        app.dependency_overrides[require_onboarded_user] = lambda: user

    set_identity(owner)
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        listed = await client.get("/api/v1/sessions")
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()] == [str(owner_session.id)]

        for inaccessible_id in (foreign_session.id, legacy_session.id, UUID(int=0)):
            response = await client.get(f"/api/v1/sessions/{inaccessible_id}")
            assert response.status_code == 404
            assert response.json()["error"]["code"] == "SESSION_NOT_FOUND"

        nested = await client.get(f"/api/v1/sessions/{foreign_session.id}/discovery")
        assert nested.status_code == 404
        assert nested.json()["error"]["code"] == "SESSION_NOT_FOUND"

        caller_owned = await client.post(
            "/api/v1/sessions",
            json={"name": "Caller-owned", "owner_user_id": str(foreign.id)},
        )
        assert caller_owned.status_code == 422

        created = await client.post("/api/v1/sessions", json={"name": "New owner A"})
        assert created.status_code == 201

        invalid_limit = await client.get("/api/v1/sessions?limit=101")
        assert invalid_limit.status_code == 400
        assert invalid_limit.json()["error"]["code"] == "VALIDATION_ERROR"

        set_identity(admin)
        admin_list = await client.get("/api/v1/sessions?limit=100")
        assert admin_list.status_code == 200
        admin_ids = {item["id"] for item in admin_list.json()}
        assert {
            str(owner_session.id),
            str(foreign_session.id),
            str(admin_session.id),
            str(legacy_session.id),
        } <= admin_ids

        legacy_read = await client.get(f"/api/v1/sessions/{legacy_session.id}")
        assert legacy_read.status_code == 200
        assert legacy_read.json()["id"] == str(legacy_session.id)

    async with factory() as session:
        created_row = await session.get(PortfolioSession, UUID(created.json()["id"]))
        assert created_row is not None
        assert created_row.owner_user_id == owner.id
        assert created_row.legacy_quarantined is False
