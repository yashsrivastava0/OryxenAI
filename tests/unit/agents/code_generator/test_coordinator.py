"""`advance_after`'s durable stage advancement, including `stage_durations_ms`.

This file is scoped narrowly to the observed-duration write added alongside
`design.md`'s Fix Implementation item 2: when `advance_after` finalizes a
completed stage attempt, it must persist that stage's elapsed milliseconds
into the run's `stage_durations_ms` dict without disturbing any other
pre-existing entry, using the exact same `compare_and_swap` call the
function already performs for `coordinator_stage`/`status`/`job_field`.

Uses a real database session (via the `db_session` fixture) rather than a
mocked repository, matching this codebase's own precedent for exercising
`CodeGeneratorDevelopmentRepository`-backed flows
(`tests/integration/test_code_generator_development_worker.py`).
`advance_after` itself expects an async-context-manager *factory*
(`sessionmaker`), not a bare session, so a tiny local wrapper adapts the
single per-test `db_session` to that shape.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.agents.code_generator.core.coordinator import advance_after
from oryxenai.core.settings import get_settings
from oryxenai.db.repositories.code_generator_development import CodeGeneratorDevelopmentRepository


def _sessionmaker_over(db_session: AsyncSession):
    """Adapt a single per-test session to the `sessionmaker()` shape
    `advance_after` expects (`async with sessionmaker() as db: ...`)."""

    @asynccontextmanager
    async def _factory() -> AsyncIterator[AsyncSession]:
        yield db_session

    return _factory


async def _create_acquired_run(db_session: AsyncSession, *, prior_durations: dict[str, float]):
    """Create a run already sitting at the "acquired" stage with an active
    "acquire" stage attempt, plus a pre-existing `stage_durations_ms` entry
    for an unrelated stage -- the fixture this file's tests need to assert
    that entry survives untouched."""

    repo = CodeGeneratorDevelopmentRepository(db_session)
    run = await repo.create(
        input_reference={"kind": "test-fixture"}, idempotency_key=None, auto_advance=True
    )
    updated = await repo.compare_and_swap(
        run.id,
        expected_revision=run.revision,
        values={
            "status": "acquired",
            "resource_ledger": {"ledger_hash": "ledger-hash-1"},
            "stage_durations_ms": dict(prior_durations),
        },
    )
    assert updated is not None
    attempt = await repo.create_stage_attempt(
        run.id,
        stage="acquire",
        input_fingerprint="fingerprint-acquire-1",
        idempotency_key=f"test:{run.id}:acquire:1",
        expected_run_revision=updated.revision,
    )
    await db_session.commit()
    return updated, attempt


@pytest.mark.integration
async def test_advance_after_writes_a_non_negative_duration_for_the_completed_stage(
    db_session: AsyncSession,
) -> None:
    get_settings()
    run, _attempt = await _create_acquired_run(db_session, prior_durations={})

    advanced = await advance_after(
        _sessionmaker_over(db_session), run.id, completed_stage="acquired"
    )

    assert advanced is True
    refreshed = await CodeGeneratorDevelopmentRepository(db_session).get(run.id)
    assert refreshed is not None
    await db_session.refresh(refreshed)
    durations = refreshed.stage_durations_ms
    assert isinstance(durations, dict)
    assert "acquire" in durations
    assert durations["acquire"] >= 0.0


@pytest.mark.integration
async def test_advance_after_leaves_other_stage_durations_untouched(
    db_session: AsyncSession,
) -> None:
    prior = {"plan": 12_345.0}
    run, _attempt = await _create_acquired_run(db_session, prior_durations=prior)

    advanced = await advance_after(
        _sessionmaker_over(db_session), run.id, completed_stage="acquired"
    )

    assert advanced is True
    refreshed = await CodeGeneratorDevelopmentRepository(db_session).get(run.id)
    assert refreshed is not None
    await db_session.refresh(refreshed)
    durations = refreshed.stage_durations_ms
    # The pre-existing "plan" entry must be byte-identical -- untouched by
    # this call's "acquire" write. This is the concrete, checkable form of
    # the preservation requirement: only the just-completed stage's key is
    # written; every other key in the dict survives as-is.
    assert durations["plan"] == 12_345.0
    assert "acquire" in durations


@pytest.mark.integration
async def test_advance_after_writes_the_duration_through_the_existing_compare_and_swap(
    db_session: AsyncSession,
) -> None:
    """The duration write must ride along with the existing CAS call already
    used for `coordinator_stage`/`status`/`job_field` -- not a second,
    separate write. Verified indirectly here: both the duration and the
    stage-transition fields land in the same refreshed row at the same
    revision increment (a second write would bump the revision twice)."""

    run, _attempt = await _create_acquired_run(db_session, prior_durations={})
    revision_before = run.revision

    advanced = await advance_after(
        _sessionmaker_over(db_session), run.id, completed_stage="acquired"
    )

    assert advanced is True
    refreshed = await CodeGeneratorDevelopmentRepository(db_session).get(run.id)
    assert refreshed is not None
    await db_session.refresh(refreshed)
    assert refreshed.revision == revision_before + 1
    assert refreshed.coordinator_stage == "generate"
    assert refreshed.status == "queued"
    assert "acquire" in refreshed.stage_durations_ms
