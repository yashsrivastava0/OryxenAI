"""PostgreSQL constraints and repository isolation for Phase 2 ownership."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryxenai.auth.models import AppUser
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository

pytestmark = pytest.mark.integration


async def _add_user(session: AsyncSession, user_id: UUID, email: str) -> None:
    session.add(
        AppUser(
            id=user_id,
            supabase_user_id=uuid4(),
            primary_email=email,
            username=email.split("@", 1)[0],
            role="user",
            status="active",
            onboarding_completed_at=datetime.now(UTC),
        )
    )
    await session.flush()


async def test_owned_repository_queries_keep_legacy_rows_out_of_normal_scope(db_session) -> None:
    owner_id = uuid4()
    foreign_id = uuid4()
    await _add_user(db_session, owner_id, "owner@example.com")
    await _add_user(db_session, foreign_id, "foreign@example.com")

    repo = PortfolioSessionRepository(db_session)
    owned = await repo.create_owned(owner_id, name="Owned")
    foreign = await repo.create_owned(foreign_id, name="Foreign")
    legacy = await repo.create(name="Legacy")

    assert owned.owner_user_id == owner_id
    assert owned.legacy_quarantined is False
    assert legacy.owner_user_id is None
    assert legacy.legacy_quarantined is True
    assert await repo.get_owned_by_id(owned.id, owner_id) is not None
    assert await repo.get_owned_by_id(foreign.id, owner_id) is None
    assert await repo.get_owned_by_id(legacy.id, owner_id) is None
    assert [row.id for row in await repo.list_owned_recent(owner_id, limit=100)] == [owned.id]
    assert {row.id for row in await repo.list_recent_for_admin(limit=100)} >= {
        owned.id,
        foreign.id,
        legacy.id,
    }


@pytest.mark.asyncio
async def test_owner_checks_fk_and_restrict_deletion(test_engine) -> None:
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    owner_id = uuid4()
    async with factory() as session:
        await _add_user(session, owner_id, "owner@example.com")
        await session.commit()

    async def invalid_row(owner_user_id: UUID | None, legacy_quarantined: bool) -> None:
        async with factory() as session:
            session.add(
                PortfolioSession(
                    owner_user_id=owner_user_id,
                    legacy_quarantined=legacy_quarantined,
                )
            )
            with pytest.raises(IntegrityError):
                await session.flush()

    await invalid_row(owner_id, True)
    await invalid_row(None, False)
    await invalid_row(uuid4(), False)

    async with factory() as session:
        repo = PortfolioSessionRepository(session)
        owned = await repo.create_owned(owner_id, name="Protected")
        await session.commit()
        assert owned.owner_user_id == owner_id

    async with factory() as session:
        user = await session.get(AppUser, owner_id)
        assert user is not None
        await session.delete(user)
        with pytest.raises(IntegrityError):
            await session.flush()


@pytest.mark.asyncio
async def test_ownership_index_and_foreign_key_are_declared(test_engine) -> None:
    async with test_engine.connect() as connection:
        indexes, foreign_keys, checks = await connection.run_sync(
            lambda sync_connection: (
                inspect(sync_connection).get_indexes("portfolio_sessions"),
                inspect(sync_connection).get_foreign_keys("portfolio_sessions"),
                inspect(sync_connection).get_check_constraints("portfolio_sessions"),
            )
        )
    assert any(index["name"] == "ix_portfolio_sessions_owner_created" for index in indexes)
    assert any(
        foreign_key["name"] == "fk_portfolio_sessions_owner_user_id" for foreign_key in foreign_keys
    )
    assert any(
        check["name"] == "ck_portfolio_sessions_owner_legacy_consistency" for check in checks
    )
