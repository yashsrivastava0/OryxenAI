"""Durable Explorer worker flow using the deterministic test mock client."""

from __future__ import annotations

from uuid import UUID

import pytest

from oryxenai.agents.discovery.agent import DiscoveryAgent
from oryxenai.agents.discovery.schemas import DiscoveryAnswer
from oryxenai.agents.discovery.service import DiscoveryService
from oryxenai.agents.shared.contracts import AgentResult
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
    assert started["discovery"]["max_attempts"] == 2

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
    assert len(questions) == 2

    answers = [
        DiscoveryAnswer(
            question_id=question["id"],
            mode="answered",
            value={"choice_id": "forest_copper", "note": ""}
            if question["kind"] == "palette_select"
            else "pick-one",
        )
        for question in questions
    ]
    answered = await service.save_answers(
        session_id, answers, complete=True, continue_with_current_information=True
    )
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
    assert review["discovery"]["brief"]["markdown"].startswith("# Portfolio Explorer Brief")

    revised = await service.revise_brief(session_id, "Lead with QueueGuard")
    await db_session.commit()
    failed_job = await JobService(db_session).get(UUID(revised["discovery"]["brief"]["job_id"]))
    assert failed_job is not None
    monkeypatch.setattr(
        "oryxenai.jobs.handlers.discovery._build_discovery_agent",
        lambda *args, **kwargs: _BoomAgent(),
    )
    with pytest.raises(ProviderTimeoutError):
        await DiscoveryBuildOrReviseBriefHandler().execute(
            {**failed_job.payload, "attempt": failed_job.max_attempts},
            "test-worker",
        )
    await db_session.commit()
    db_session.expire_all()
    attention = (await service.get_discovery_state(session_id))["discovery"]
    assert attention["status"] == "needs_attention"
    assert attention["brief"]["revision_request"] == "Lead with QueueGuard"

    retried = await service.save_answers(
        session_id, [], complete=True, continue_with_current_information=True
    )
    await db_session.commit()
    retry_run = await DiscoveryRepository(db_session).get_run(
        UUID(retried["discovery"]["brief"]["run_id"])
    )
    assert retry_run is not None
    assert retry_run.input_payload["revision_request"] == "Lead with QueueGuard"
    monkeypatch.setattr(
        "oryxenai.jobs.handlers.discovery._build_discovery_agent", _mock_agent_factory
    )
    retry_job = await JobService(db_session).get(UUID(retried["discovery"]["brief"]["job_id"]))
    assert retry_job is not None
    assert (await DiscoveryBuildOrReviseBriefHandler().execute(retry_job.payload, "test-worker"))[
        "status"
    ] == "succeeded"
    await db_session.commit()
    db_session.expire_all()

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


@pytest.mark.asyncio
async def test_ready_for_brief_is_queued_by_worker(db_session, monkeypatch) -> None:
    class _ReadyAgent:
        async def run(self, context):
            return AgentResult(
                output={
                    "operation": "understand_and_question",
                    "mode": "READY_FOR_BRIEF",
                    "assistant_message": "I can prepare the brief.",
                    "questions": [],
                    "memory_update": {},
                }
            )

    session = await PortfolioSessionRepository(db_session).create("Automatic brief")
    session_id = session.id
    service = DiscoveryService(DiscoveryRepository(db_session), JobService(db_session))
    started = await service.start(
        session_id, message="Portfolio", document_text="", goal="get hired"
    )
    await db_session.commit()
    monkeypatch.setattr(
        "oryxenai.jobs.handlers.discovery._build_discovery_agent",
        lambda *args, **kwargs: _ReadyAgent(),
    )

    job = await JobService(db_session).get(UUID(started["discovery"]["operation_a"]["job_id"]))
    assert job is not None
    result = await DiscoveryUnderstandAndQuestionHandler().execute(job.payload, "test-worker")
    assert result["status"] == "succeeded"
    await db_session.commit()

    db_session.expire_all()
    current = (await service.get_discovery_state(session_id))["discovery"]
    assert current["status"] == "brief_running"
    followup = await JobService(db_session).get(UUID(current["brief"]["job_id"]))
    assert followup is not None
    assert followup.job_kind == "discovery.build_or_revise_brief"
    assert followup.status == "queued"


@pytest.mark.asyncio
async def test_redelivery_uses_current_session_revision(db_session, monkeypatch) -> None:
    session = await PortfolioSessionRepository(db_session).create("Redelivered question job")
    session_id = session.id
    service = DiscoveryService(DiscoveryRepository(db_session), JobService(db_session))
    started = await service.start(
        session_id, message="Portfolio", document_text="", goal="get hired"
    )
    await db_session.commit()
    job = await JobService(db_session).get(UUID(started["discovery"]["operation_a"]["job_id"]))
    assert job is not None

    monkeypatch.setattr(
        "oryxenai.jobs.handlers.discovery._build_discovery_agent",
        lambda *args, **kwargs: _BoomAgent(),
    )
    first = {**job.payload, "attempt": 1}
    with pytest.raises(ProviderTimeoutError):
        await DiscoveryUnderstandAndQuestionHandler().execute(first, "test-worker")

    monkeypatch.setattr(
        "oryxenai.jobs.handlers.discovery._build_discovery_agent", _mock_agent_factory
    )
    second = {**job.payload, "attempt": 2}
    result = await DiscoveryUnderstandAndQuestionHandler().execute(second, "test-worker")
    assert result["status"] == "succeeded"
    await db_session.commit()
    db_session.expire_all()
    current = (await service.get_discovery_state(session_id))["discovery"]
    assert current["status"] == "questions_ready"
    assert current["attempt"] == 2
