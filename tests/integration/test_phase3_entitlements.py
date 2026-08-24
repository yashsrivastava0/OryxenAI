from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from oryxenai.auth.entitlements import PortfolioEntitlementRepository
from oryxenai.auth.errors import EntitlementBindingConflictError, PortfolioReadOnlyError
from oryxenai.auth.models import AppUser, PortfolioEntitlement
from oryxenai.db.models.code_generator_development import CodeGeneratorDevelopmentRun
from oryxenai.jobs.repository import JobRepository

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


async def test_success_consumes_once_and_blocks_same_run_retry(db_session: AsyncSession) -> None:
    user = await _normal_user(db_session, "success-phase3@example.com")
    entitlements = PortfolioEntitlementRepository(db_session)
    session = await entitlements.get_or_create_session(user_id=user.id, name="One portfolio")
    await db_session.flush()
    entitlement = await entitlements.get_for_user(user.id, lock=True)
    assert entitlement is not None
    binding_revision = entitlement.revision

    run = CodeGeneratorDevelopmentRun(
        run_mode="session",
        portfolio_session_id=session.id,
        owner_user_id=user.id,
        actor_user_id=user.id,
        authorization_context_version=1,
        entitlement_revision=binding_revision + 1,
    )
    db_session.add(run)
    await db_session.flush()
    bound = await entitlements.bind_generation_run(
        user_id=user.id,
        session_id=session.id,
        run_id=run.id,
        revision=binding_revision,
        actor_user_id=user.id,
    )
    consumed = await entitlements.finalize_promoted_success(
        user_id=user.id,
        session_id=session.id,
        run_id=run.id,
        revision=bound.revision,
    )
    assert consumed.successful_run_id == run.id
    assert consumed.consumed_at is not None

    with pytest.raises(PortfolioReadOnlyError):
        await entitlements.assert_bound_retry(
            user_id=user.id,
            session_id=session.id,
            run_id=run.id,
            revision=consumed.revision,
        )

    with pytest.raises(PortfolioReadOnlyError):
        await entitlements.get_or_create_session(user_id=user.id, name="A second portfolio")


async def test_generation_lane_claims_one_credit_job_but_allows_system_probe(
    test_engine: AsyncEngine,
) -> None:
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        repo = JobRepository(session)
        await repo.enqueue(
            "code_generator.plan",
            {},
            execution_lane="model-generation",
        )
        await repo.enqueue(
            "content_architect.build",
            {},
            execution_lane="model-generation",
        )
        await repo.enqueue("system.worker_probe", {})
        await session.commit()

    async with factory() as session:
        claimed = await JobRepository(session).claim_batch("phase3-worker-a", 60, 10)
        await session.commit()

    assert sum(job.execution_lane == "model-generation" for job in claimed) == 1
    assert sum(job.job_kind == "system.worker_probe" for job in claimed) == 1

    async with factory() as session:
        next_claim = await JobRepository(session).claim_batch("phase3-worker-b", 60, 10)
        await session.commit()
    assert not any(job.execution_lane == "model-generation" for job in next_claim)
