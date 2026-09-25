from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from oryxenai.auth.entitlements import PortfolioEntitlementRepository
from oryxenai.auth.errors import EntitlementBindingConflictError
from oryxenai.auth.models import AppUser, PortfolioEntitlement

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def _normal_user(session: AsyncSession, email: str = "phase3@example.com") -> AppUser:
    user = AppUser(
        supabase_user_id=uuid4(),
        primary_email=email,
        role="user",
        status="active",
    )
    session.add(user)
    await session.flush()
    return user


async def test_concurrent_normal_session_claims_return_one_binding(
    test_engine: AsyncEngine,
) -> None:
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as seed:
        user = await _normal_user(seed)
        await seed.commit()
        user_id = user.id

    async def claim(name: str):
        async with factory() as session:
            try:
                value = await PortfolioEntitlementRepository(session).get_or_create_session(
                    user_id=user_id,
                    name=name,
                )
                await session.commit()
                return value.id
            except Exception:
                await session.rollback()
                raise

    first, second = await asyncio.gather(claim("first"), claim("second"))
    assert first == second

    async with factory() as verify:
        assert (
            await verify.scalar(
                select(func.count(PortfolioEntitlement.user_id)).where(
                    PortfolioEntitlement.user_id == user_id
                )
            )
        ) == 1


@pytest.mark.parametrize("role", ["admin", "suspended"])
async def test_only_active_normal_users_can_receive_entitlements(
    db_session: AsyncSession,
    role: str,
) -> None:
    user = AppUser(
        supabase_user_id=uuid4(),
        primary_email=f"{role}-phase3@example.com",
        role="admin" if role == "admin" else "user",
        status="active" if role == "admin" else role,
    )
    db_session.add(user)
    await db_session.flush()

    with pytest.raises(EntitlementBindingConflictError):
        await PortfolioEntitlementRepository(db_session).ensure_for_normal_user(user.id)

    assert (
        await db_session.scalar(
            select(func.count(PortfolioEntitlement.user_id)).where(
                PortfolioEntitlement.user_id == user.id
            )
        )
    ) == 0
