"""Durable Content Architect worker flow using the deterministic test mock client."""

from __future__ import annotations

from uuid import UUID

import pytest

from oryxenai.agents.content_architect.agent import ContentArchitectAgent
from oryxenai.agents.content_architect.service import (
    ContentArchitectOperationError,
    ContentArchitectService,
)
from oryxenai.agents.discovery.agent import DiscoveryAgent
from oryxenai.agents.discovery.schemas import DiscoveryAnswer
from oryxenai.agents.discovery.service import DiscoveryService
from oryxenai.agents.shared.providers.errors import ProviderTimeoutError
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.repositories.content_architect import ContentArchitectRepository
from oryxenai.db.repositories.discovery import DiscoveryRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository
from oryxenai.jobs.handlers.content_architect import ContentArchitectBuildHandler
from oryxenai.jobs.handlers.discovery import (
    DiscoveryBuildOrReviseBriefHandler,
    DiscoveryUnderstandAndQuestionHandler,
)
from oryxenai.jobs.service import JobService
from tests.conftest import _ContentArchitectMockModelClient, _MockModelClient

pytestmark = pytest.mark.integration


class _BoomAgent:
    async def run(self, context):
        raise ProviderTimeoutError("simulated timeout")


def _mock_ca_agent_factory(*args, **kwargs):
    return ContentArchitectAgent(model_client=_ContentArchitectMockModelClient())


def _mock_discovery_agent_factory(*args, **kwargs):
    return DiscoveryAgent(model_client=_MockModelClient())


async def _approve_discovery(db_session, session_id, monkeypatch) -> None:
    """Drive Discovery to `approved` directly via its own service + handlers.

    Must patch Discovery's real agent factory to the deterministic mock —
    without this, DiscoveryUnderstandAndQuestionHandler/
    DiscoveryBuildOrReviseBriefHandler build the LIVE provider adapter
    (jobs/handlers/discovery.py::_build_discovery_agent) and make real,
    billed OpenAI calls with non-deterministic output.
    """
    monkeypatch.setattr(
        "oryxenai.jobs.handlers.discovery._build_discovery_agent",
        _mock_discovery_agent_factory,
    )
    discovery_service = DiscoveryService(DiscoveryRepository(db_session), JobService(db_session))

    started = await discovery_service.start(
        session_id,
        message="Create a portfolio for me. I am a software developer.",
        document_text="Test User\nSoftware Engineer\nExample Corp\n",
        goal="get hired",
    )
    await db_session.commit()

    question_job = await JobService(db_session).get(
        UUID(started["discovery"]["operation_a"]["job_id"])
    )
    await DiscoveryUnderstandAndQuestionHandler().execute(question_job.payload, "test-worker")
    await db_session.commit()
    db_session.expire_all()

    state_data = await discovery_service.get_discovery_state(session_id)
    questions = state_data["discovery"]["operation_a"]["items"]
    answers = [
        DiscoveryAnswer(question_id=q["id"], mode="answered", value="pick-one") for q in questions
    ]
    answered = await discovery_service.save_answers(session_id, answers, complete=True)
    await db_session.commit()

    brief_job = await JobService(db_session).get(UUID(answered["discovery"]["brief"]["job_id"]))
    await DiscoveryBuildOrReviseBriefHandler().execute(brief_job.payload, "test-worker")
    await db_session.commit()
    db_session.expire_all()

    await discovery_service.approve_brief(session_id)
    await db_session.commit()


@pytest.mark.asyncio
async def test_full_worker_flow_single_page(db_session, monkeypatch) -> None:
    session = await PortfolioSessionRepository(db_session).create("Worker content architect")
    session_id = session.id
    await _approve_discovery(db_session, session_id, monkeypatch)

    service = ContentArchitectService(
        ContentArchitectRepository(db_session), JobService(db_session)
    )
    monkeypatch.setattr(
        "oryxenai.jobs.handlers.content_architect._build_content_architect_agent",
        _mock_ca_agent_factory,
    )

    started = await service.start(session_id, {})
    await db_session.commit()
    assert started["content_architect"]["status"] == "build_running"

    build_job = await JobService(db_session).get(UUID(started["content_architect"]["job_id"]))
    result = await ContentArchitectBuildHandler().execute(build_job.payload, "test-worker")
    assert result["status"] == "succeeded"
    await db_session.commit()

    db_session.expire_all()
    review = await service.get_content_architect_state(session_id)
    assert review["content_architect"]["status"] == "content_review"
    assert review["content_architect"]["stages_run"] == ["plan_content"]
    assert review["content_architect"]["unresolved_issues"] == ["no metrics supplied"]
    assert review["content_architect"]["route_plan"][0]["route_id"] == "home"

    approved = await service.approve(session_id)
    assert approved["content_architect"]["status"] == "approved"
    assert approved["content_architect"]["approved"] is not None


@pytest.mark.asyncio
async def test_start_rejected_when_discovery_not_approved(db_session) -> None:
    session = await PortfolioSessionRepository(db_session).create("Not approved yet")
    session_id = session.id
    service = ContentArchitectService(
        ContentArchitectRepository(db_session), JobService(db_session)
    )

    with pytest.raises(ContentArchitectOperationError) as exc_info:
        await service.start(session_id, {})
    assert exc_info.value.code == "CONTENT_ARCHITECT_DISCOVERY_NOT_APPROVED"


@pytest.mark.asyncio
async def test_revision_re_runs_build(db_session, monkeypatch) -> None:
    session = await PortfolioSessionRepository(db_session).create("Revision content architect")
    session_id = session.id
    await _approve_discovery(db_session, session_id, monkeypatch)

    service = ContentArchitectService(
        ContentArchitectRepository(db_session), JobService(db_session)
    )
    monkeypatch.setattr(
        "oryxenai.jobs.handlers.content_architect._build_content_architect_agent",
        _mock_ca_agent_factory,
    )

    started = await service.start(session_id, {})
    await db_session.commit()
    build_job = await JobService(db_session).get(UUID(started["content_architect"]["job_id"]))
    await ContentArchitectBuildHandler().execute(build_job.payload, "test-worker")
    await db_session.commit()
    db_session.expire_all()

    revised = await service.revise(session_id, "Lead with QueueGuard")
    await db_session.commit()
    assert revised["content_architect"]["status"] == "build_running"

    revise_job = await JobService(db_session).get(UUID(revised["content_architect"]["job_id"]))
    result = await ContentArchitectBuildHandler().execute(revise_job.payload, "test-worker")
    assert result["status"] == "succeeded"
    await db_session.commit()

    db_session.expire_all()
    review = await service.get_content_architect_state(session_id)
    assert review["content_architect"]["status"] == "content_review"
    assert (
        "QueueGuard leads" in review["content_architect"]["site_story_strategy"]["narrative_thesis"]
    )


@pytest.mark.asyncio
async def test_duplicate_start_does_not_create_second_run(db_session, monkeypatch) -> None:
    session = await PortfolioSessionRepository(db_session).create("Duplicate start")
    session_id = session.id
    await _approve_discovery(db_session, session_id, monkeypatch)

    service = ContentArchitectService(
        ContentArchitectRepository(db_session), JobService(db_session)
    )
    first = await service.start(session_id, {})
    await db_session.commit()
    second = await service.start(session_id, {})
    await db_session.commit()

    assert first["content_architect"]["job_id"] == second["content_architect"]["job_id"]

    from sqlalchemy import select

    result = await db_session.execute(
        select(AgentRun.id).where(
            AgentRun.portfolio_session_id == session_id,
            AgentRun.agent_key == "content_architect",
        )
    )
    assert len(result.all()) == 1


@pytest.mark.asyncio
async def test_worker_failure_surfaces_only_after_retries_exhausted(
    db_session, monkeypatch
) -> None:
    session = await PortfolioSessionRepository(db_session).create("Failure content architect")
    session_id = session.id
    await _approve_discovery(db_session, session_id, monkeypatch)

    service = ContentArchitectService(
        ContentArchitectRepository(db_session), JobService(db_session)
    )
    started = await service.start(session_id, {})
    await db_session.commit()
    max_attempts = started["content_architect"]["max_attempts"]

    monkeypatch.setattr(
        "oryxenai.jobs.handlers.content_architect._build_content_architect_agent",
        lambda *args, **kwargs: _BoomAgent(),
    )

    build_job = await JobService(db_session).get(UUID(started["content_architect"]["job_id"]))
    payload = dict(build_job.payload)
    payload["attempt"] = max_attempts
    with pytest.raises(ProviderTimeoutError):
        await ContentArchitectBuildHandler().execute(payload, "test-worker")
    await db_session.commit()

    db_session.expire_all()
    state_data = await service.get_content_architect_state(session_id)
    assert state_data["content_architect"]["status"] == "needs_attention"
    assert state_data["content_architect"]["latest_error"]["code"] == "PROVIDER_TIMEOUT_ERROR"


@pytest.mark.asyncio
async def test_transient_failure_does_not_surface_while_retries_remain(
    db_session, monkeypatch
) -> None:
    session = await PortfolioSessionRepository(db_session).create(
        "Transient failure content architect"
    )
    session_id = session.id
    await _approve_discovery(db_session, session_id, monkeypatch)

    service = ContentArchitectService(
        ContentArchitectRepository(db_session), JobService(db_session)
    )
    started = await service.start(session_id, {})
    await db_session.commit()
    assert started["content_architect"]["max_attempts"] > 1

    monkeypatch.setattr(
        "oryxenai.jobs.handlers.content_architect._build_content_architect_agent",
        lambda *args, **kwargs: _BoomAgent(),
    )

    build_job = await JobService(db_session).get(UUID(started["content_architect"]["job_id"]))
    payload = dict(build_job.payload)
    payload["attempt"] = 1
    with pytest.raises(ProviderTimeoutError):
        await ContentArchitectBuildHandler().execute(payload, "test-worker")
    await db_session.commit()

    db_session.expire_all()
    state_data = await service.get_content_architect_state(session_id)
    assert state_data["content_architect"]["status"] == "build_running"
    assert state_data["content_architect"]["latest_error"] is None
