"""Durable Discovery worker flow using the deterministic test mock client."""

from __future__ import annotations

from uuid import UUID

import pytest

from oryxenai.agents.discovery.agent import DiscoveryAgent
from oryxenai.agents.discovery.schemas import DiscoveryAnswer
from oryxenai.agents.discovery.service import DiscoveryService
from oryxenai.agents.shared.providers.errors import ProviderTimeoutError
from oryxenai.db.repositories.discovery import DiscoveryRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository
from oryxenai.jobs.handlers.discovery import (
    DiscoveryBuildOrReviseBriefHandler,
    DiscoveryUnderstandAndQuestionHandler,
)
from oryxenai.jobs.service import JobService
from tests.conftest import _MockModelClient

pytestmark = pytest.mark.integration


class _BoomAgent:
    async def run(self, context):
        raise ProviderTimeoutError("simulated timeout")


def _mock_agent_factory(*args, **kwargs):
    return DiscoveryAgent(model_client=_MockModelClient())


@pytest.mark.asyncio
async def test_full_worker_flow_with_mock_client(db_session, monkeypatch) -> None:
    session = await PortfolioSessionRepository(db_session).create("Worker discovery")
    session_id = session.id
    service = DiscoveryService(DiscoveryRepository(db_session), JobService(db_session))
    monkeypatch.setattr(
        "oryxenai.jobs.handlers.discovery._build_discovery_agent",
        _mock_agent_factory,
    )

    started = await service.start(
        session_id,
        message="Create a portfolio for me. I am a software developer.",
        document_text=(
            "Test User\nSoftware Engineer\nExample Corp\n"
            "Implemented retry handling and stale-job recovery for the PostgreSQL worker\n"
        ),
        goal="get hired",
    )
    await db_session.commit()
    assert started["discovery"]["status"] == "questions_queued"
    assert started["discovery"]["max_attempts"] == 3

    question_job = await JobService(db_session).get(
        UUID(started["discovery"]["operation_a"]["job_id"])
    )
    assert question_job is not None
    result = await DiscoveryUnderstandAndQuestionHandler().execute(
        question_job.payload, "test-worker"
    )
    assert result["status"] == "succeeded"
    await db_session.commit()

    db_session.expire_all()
    state_data = await service.get_discovery_state(session_id)
    assert state_data["discovery"]["status"] == "questions_ready"
    assert state_data["discovery"]["operation_a"]["mode"] == "ASK_QUESTIONS"
    questions = state_data["discovery"]["operation_a"]["items"]
    assert len(questions) == 1

    answers = [
        DiscoveryAnswer(question_id=question["id"], mode="answered", value="pick-one")
        for question in questions
    ]
    answered = await service.save_answers(session_id, answers, complete=True)
    await db_session.commit()
    assert answered["discovery"]["status"] == "brief_running"

    brief_job = await JobService(db_session).get(UUID(answered["discovery"]["brief"]["job_id"]))
    assert brief_job is not None
    brief_result = await DiscoveryBuildOrReviseBriefHandler().execute(
        brief_job.payload, "test-worker"
    )
    assert brief_result["status"] == "succeeded"
    await db_session.commit()

    db_session.expire_all()
    review = await service.get_discovery_state(session_id)
    assert review["discovery"]["status"] == "brief_review"
    assert review["discovery"]["brief"]["title"]
    assert review["discovery"]["brief"]["markdown"].startswith("# Portfolio Discovery Brief")

    approved = await service.approve_brief(session_id)
    assert approved["discovery"]["status"] == "approved"
    assert approved["discovery"]["brief"]["approved"] is not None


@pytest.mark.asyncio
async def test_worker_failure_always_surfaces_in_state(db_session, monkeypatch) -> None:
    """A failure surfaces once retries are exhausted (the final attempt).

    Earlier attempts with retries remaining must NOT surface — the worker
    retries those with backoff on its own — see
    test_transient_failure_does_not_surface_while_retries_remain.
    """
    session = await PortfolioSessionRepository(db_session).create("Failure discovery")
    session_id = session.id
    service = DiscoveryService(DiscoveryRepository(db_session), JobService(db_session))

    started = await service.start(
        session_id,
        message="Create my portfolio",
        document_text="",
        goal="get hired",
    )
    await db_session.commit()
    max_attempts = started["discovery"]["max_attempts"]

    monkeypatch.setattr(
        "oryxenai.jobs.handlers.discovery._build_discovery_agent",
        lambda *args, **kwargs: _BoomAgent(),
    )

    question_job = await JobService(db_session).get(
        UUID(started["discovery"]["operation_a"]["job_id"])
    )
    payload = dict(question_job.payload)
    payload["attempt"] = max_attempts
    with pytest.raises(ProviderTimeoutError):
        await DiscoveryUnderstandAndQuestionHandler().execute(payload, "test-worker")
    await db_session.commit()

    db_session.expire_all()
    state_data = await service.get_discovery_state(session_id)
    assert state_data["discovery"]["status"] == "needs_attention"
    assert state_data["discovery"]["latest_error"]["code"] == "PROVIDER_TIMEOUT_ERROR"


@pytest.mark.asyncio
async def test_transient_failure_does_not_surface_while_retries_remain(
    db_session, monkeypatch
) -> None:
    session = await PortfolioSessionRepository(db_session).create("Transient failure discovery")
    session_id = session.id
    service = DiscoveryService(DiscoveryRepository(db_session), JobService(db_session))

    started = await service.start(
        session_id,
        message="Create my portfolio",
        document_text="",
        goal="get hired",
    )
    await db_session.commit()
    assert started["discovery"]["max_attempts"] > 1

    monkeypatch.setattr(
        "oryxenai.jobs.handlers.discovery._build_discovery_agent",
        lambda *args, **kwargs: _BoomAgent(),
    )

    question_job = await JobService(db_session).get(
        UUID(started["discovery"]["operation_a"]["job_id"])
    )
    payload = dict(question_job.payload)
    payload["attempt"] = 1
    with pytest.raises(ProviderTimeoutError):
        await DiscoveryUnderstandAndQuestionHandler().execute(payload, "test-worker")
    await db_session.commit()

    db_session.expire_all()
    state_data = await service.get_discovery_state(session_id)
    assert state_data["discovery"]["status"] == "questions_running"
    assert state_data["discovery"]["latest_error"] is None
