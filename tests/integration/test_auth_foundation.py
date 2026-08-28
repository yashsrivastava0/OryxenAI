from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from oryxenai.auth.domain import AuthRole, ProviderIdentity
from oryxenai.auth.errors import (
    AccessNotApprovedError,
    UserCapacityReachedError,
    UsernameTakenError,
)
from oryxenai.auth.jwt import VerifiedToken
from oryxenai.auth.models import AppUser
from oryxenai.auth.repository import AuthRepository
from oryxenai.auth.service import AuthService
from oryxenai.core.settings import AuthConfig

pytestmark = pytest.mark.integration

SUBJECT = UUID("11111111-1111-4111-8111-111111111111")


async def _admit(
    session: AsyncSession,
    *,
    subject: UUID,
    email: str,
    role: AuthRole = AuthRole.USER,
) -> tuple[AppUser, bool]:
    user, created = await AuthRepository(session).provision_or_get(
        subject=subject,
        email=email,
        role=role,
        normal_user_limit=15,
    )
    return user, created


@pytest.mark.integration
@pytest.mark.asyncio
async def test_normal_admission_at_14_15_and_16(db_session: AsyncSession) -> None:
    for index in range(14):
        await _admit(
            db_session,
            subject=uuid4(),
            email=f"user{index}@example.com",
        )
    await db_session.commit()

    await _admit(db_session, subject=uuid4(), email="user14@example.com")
    await db_session.commit()

    with pytest.raises(UserCapacityReachedError):
        await _admit(db_session, subject=uuid4(), email="user15@example.com")
    await db_session.rollback()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admins_do_not_consume_normal_capacity(db_session: AsyncSession) -> None:
    for index in range(15):
        await _admit(
            db_session,
            subject=uuid4(),
            email=f"user{index}@example.com",
        )
    await db_session.commit()

    admin, created = await _admit(
        db_session,
        subject=uuid4(),
        email="admin@example.com",
        role=AuthRole.ADMIN,
    )
    await db_session.commit()
    assert created is True
    assert admin.role == AuthRole.ADMIN.value


@pytest.mark.integration
@pytest.mark.asyncio
async def test_same_subject_concurrent_provisioning_is_idempotent(test_engine: AsyncEngine) -> None:
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def operation() -> tuple[bool, UUID]:
        async with factory() as session:
            try:
                user, created = await _admit(
                    session,
                    subject=SUBJECT,
                    email="same-subject@example.com",
                )
                await session.commit()
                return created, user.id
            except Exception:
                await session.rollback()
                raise

    first, second = await asyncio.gather(operation(), operation())
    assert sorted([first[0], second[0]]) == [False, True]
    assert first[1] == second[1]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_two_final_slot_attempts_admit_at_most_one(test_engine: AsyncEngine) -> None:
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as seed_session:
        for index in range(14):
            await _admit(
                seed_session,
                subject=uuid4(),
                email=f"seed{index}@example.com",
            )
        await seed_session.commit()

    async def operation(index: int) -> str:
        async with factory() as session:
            try:
                await _admit(
                    session,
                    subject=uuid4(),
                    email=f"final{index}@example.com",
                )
                await session.commit()
                return "admitted"
            except UserCapacityReachedError:
                await session.rollback()
                return "full"

    outcomes = await asyncio.gather(operation(1), operation(2))
    assert sorted(outcomes) == ["admitted", "full"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unapproved_identity_creates_no_local_row(db_session: AsyncSession) -> None:
    class Verifier:
        async def verify(self, token: str) -> VerifiedToken:
            return VerifiedToken(subject=SUBJECT)

    class Provider:
        async def get_user(self, token: str, expected_subject: UUID) -> ProviderIdentity:
            return ProviderIdentity(subject=expected_subject, email="not-approved@example.com")

    service = AuthService(
        db=db_session,
        config=AuthConfig(),
        verifier=Verifier(),
        provider=Provider(),
        admin_emails=("admin1@example.com", "admin2@example.com"),
        allowed_emails=("approved@example.com",),
    )
    with pytest.raises(AccessNotApprovedError):
        await service.current_user("token")

    count = await db_session.scalar(select(func.count(AppUser.id)))
    assert count == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_username_claim_has_one_winner(test_engine: AsyncEngine) -> None:
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as seed_session:
        first, _ = await _admit(seed_session, subject=uuid4(), email="first@example.com")
        second, _ = await _admit(seed_session, subject=uuid4(), email="second@example.com")
        await seed_session.commit()
        first_id, second_id = first.id, second.id

    async def operation(user_id: UUID) -> str:
        async with factory() as session:
            try:
                await AuthRepository(session).claim_username(user_id, "shared-name")
                await session.commit()
                return "claimed"
            except UsernameTakenError:
                await session.rollback()
                return "taken"

    outcomes = await asyncio.gather(operation(first_id), operation(second_id))
    assert sorted(outcomes) == ["claimed", "taken"]
