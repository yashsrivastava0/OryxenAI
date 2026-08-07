"""Persistence tests for Discovery state and intake."""

from __future__ import annotations

import pytest

from oryxenai.agents.discovery.schemas import DiscoveryState, DiscoveryStatus
from oryxenai.agents.discovery.service import DiscoveryService
from oryxenai.db.repositories.discovery import DiscoveryRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository
from oryxenai.jobs.service import JobService

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_start_persists_intake_in_state(db_session) -> None:
    session = await PortfolioSessionRepository(db_session).create("Persistence")
    session_id = session.id
    service = DiscoveryService(DiscoveryRepository(db_session), JobService(db_session))

    started = await service.start(
        session_id,
        message="Create a portfolio for me.",
        document_text="Resume text line 1\nResume text line 2",
        goal="get hired",
    )
    await db_session.commit()
    assert started["discovery"]["status"] == "questions_queued"
    assert started["discovery"]["intake"]["message"] == "Create a portfolio for me."
    assert started["discovery"]["intake"]["document_text"].startswith("Resume text")
    assert started["discovery"]["intake"]["goal"] == "get hired"

    db_session.expire_all()
    reloaded = await service.get_discovery_state(session_id)
    assert reloaded["discovery"]["intake"]["message"] == "Create a portfolio for me."


@pytest.mark.asyncio
async def test_state_round_trips_through_session_current_state(db_session) -> None:
    session = await PortfolioSessionRepository(db_session).create("Round trip")
    session_id = session.id
    service = DiscoveryService(DiscoveryRepository(db_session), JobService(db_session))

    await service.start(session_id, message="hi", document_text="", goal="")
    await db_session.commit()

    db_session.expire_all()
    repo = DiscoveryRepository(db_session)
    state = await repo.get_discovery_state(session_id)
    assert state.status.value == "questions_queued"
    assert state.intake.message == "hi"
    assert state.started_at is not None


@pytest.mark.asyncio
async def test_start_after_needs_attention_replaces_intake(db_session) -> None:
    session = await PortfolioSessionRepository(db_session).create("Retry intake")
    session_id = session.id
    service = DiscoveryService(DiscoveryRepository(db_session), JobService(db_session))

    await service.start(session_id, message="first", document_text="", goal="")
    await db_session.commit()

    repo = DiscoveryRepository(db_session)
    state = await repo.get_discovery_state(session_id)
    failed = DiscoveryState.model_validate(state.model_dump())
    failed.status = DiscoveryStatus.NEEDS_ATTENTION
    failed.latest_error = {"code": "X", "message": "boom", "retryable": False}
    await repo.save_discovery_state(session_id, failed, session.revision)
    await db_session.commit()

    retried = await service.start(session_id, message="second", document_text="", goal="new goal")
    await db_session.commit()
    assert retried["discovery"]["status"] == "questions_queued"
    assert retried["discovery"]["intake"]["message"] == "second"
    assert retried["discovery"]["intake"]["goal"] == "new goal"
