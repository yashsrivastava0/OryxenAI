"""Concurrent first-time reservations must share capacity-window rows safely."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryxenai.agents.shared.contracts import ResolvedModelRoute
from oryxenai.agents.shared.model_usage import ModelUsageLedger, context_from_request
from oryxenai.db.models.model_usage import ModelCapacityWindow

pytestmark = [pytest.mark.integration, pytest.mark.worker]


async def test_parallel_first_reservations_do_not_collide_on_window_rows(test_engine):
    sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    route = ResolvedModelRoute(
        profile_name="experiential_luna_6",
        provider="experiential",
        model="gpt-6-luna",
        credential_alias="EXPLABS",
        capacity_source_id="EXPLABS",
        quota_group="EXPLABS",
        profile_fingerprint="fingerprint",
        policy_version="test",
        input_policy="any",
        pricing_card_ref="",
        alternatives=(),
    )
    ledger = ModelUsageLedger(sessionmaker)

    async def reserve(index: int) -> str:
        context = context_from_request(
            engine="discovery",
            operation="understand_and_question",
            request_context={
                "operation_id": f"run-{index}:discovery",
                "run_id": f"run-{index}",
                "normal_calls": 1,
                "recovery_allowance": 1,
            },
            input_classification="any",
        )
        return await ledger.reserve(
            route=route,
            context=context,
            attempt_kind="normal",
            request_attempt=1,
            fallback_attempt=0,
            input_tokens_reserved=1000,
        )

    attempt_ids = await asyncio.gather(*(reserve(index) for index in range(8)))

    assert len(set(attempt_ids)) == 8
    async with sessionmaker() as db:
        rows = (
            await db.execute(
                select(ModelCapacityWindow.window_kind, func.count()).group_by(
                    ModelCapacityWindow.window_kind
                )
            )
        ).all()
        # One shared row per window kind, however many jobs reserved at once.
        assert rows
        assert all(count == 1 for _kind, count in rows)
