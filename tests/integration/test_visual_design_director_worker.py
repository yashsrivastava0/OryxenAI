"""Durable Visual Design Director worker flow using the deterministic test mock client."""

from __future__ import annotations

from uuid import UUID

import pytest

from oryxenai.agents.content_architect.agent import ContentArchitectAgent
from oryxenai.agents.content_architect.service import ContentArchitectService
from oryxenai.agents.discovery.agent import DiscoveryAgent
from oryxenai.agents.discovery.schemas import DiscoveryAnswer
from oryxenai.agents.discovery.service import DiscoveryService
from oryxenai.agents.shared.providers.errors import ProviderTimeoutError
from oryxenai.agents.visual_design_director.service import (
    VisualDesignDirectorOperationError,
    VisualDesignDirectorService,
)
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.repositories.content_architect import ContentArchitectRepository
from oryxenai.db.repositories.discovery import DiscoveryRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository
from oryxenai.db.repositories.visual_design_director import VisualDesignDirectorRepository
from oryxenai.jobs.handlers.content_architect import ContentArchitectBuildHandler
from oryxenai.jobs.handlers.discovery import (
    DiscoveryBuildOrReviseBriefHandler,
    DiscoveryUnderstandAndQuestionHandler,
)
from oryxenai.jobs.handlers.visual_design_director import VisualDesignDirectorBuildHandler
from oryxenai.jobs.service import JobService
from tests.conftest import (
    _ContentArchitectMockModelClient,
    _MockModelClient,
    _VisualDesignDirectorMockModelClient,
)

pytestmark = pytest.mark.integration


class _BoomAgent:
    async def run(self, context):
        raise ProviderTimeoutError("simulated timeout")


def _mock_vdd_agent_factory(*args, **kwargs):
    from oryxenai.agents.visual_design_director.agent import VisualDesignDirectorAgent

    return VisualDesignDirectorAgent(model_client=_VisualDesignDirectorMockModelClient())


def _mock_ca_agent_factory(*args, **kwargs):
    return ContentArchitectAgent(model_client=_ContentArchitectMockModelClient())


def _mock_discovery_agent_factory(*args, **kwargs):
    return DiscoveryAgent(model_client=_MockModelClient())


async def _approve_discovery_and_content_architect(db_session, session_id, monkeypatch) -> None:
    """Drive Discovery then Content Architect to `approved` directly via
    their own services + handlers, all with deterministic mock clients."""
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

    monkeypatch.setattr(
        "oryxenai.jobs.handlers.content_architect._build_content_architect_agent",
        _mock_ca_agent_factory,
    )
    ca_service = ContentArchitectService(
        ContentArchitectRepository(db_session), JobService(db_session)
    )
    ca_started = await ca_service.start(session_id, {})
    await db_session.commit()
    ca_build_job = await JobService(db_session).get(UUID(ca_started["content_architect"]["job_id"]))
    await ContentArchitectBuildHandler().execute(ca_build_job.payload, "test-worker")
    await db_session.commit()
    db_session.expire_all()

    await ca_service.approve(session_id)
    await db_session.commit()


@pytest.mark.asyncio
async def test_full_worker_flow_single_page(db_session, monkeypatch) -> None:
    session = await PortfolioSessionRepository(db_session).create("Worker visual design director")
    session_id = session.id
    await _approve_discovery_and_content_architect(db_session, session_id, monkeypatch)

    service = VisualDesignDirectorService(
        VisualDesignDirectorRepository(db_session), JobService(db_session)
    )
    monkeypatch.setattr(
        "oryxenai.jobs.handlers.visual_design_director._build_visual_design_director_agent",
        _mock_vdd_agent_factory,
    )

    started = await service.start(session_id, {})
    await db_session.commit()
    assert started["visual_design_director"]["status"] == "build_running"

    build_job = await JobService(db_session).get(UUID(started["visual_design_director"]["job_id"]))
    result = await VisualDesignDirectorBuildHandler().execute(build_job.payload, "test-worker")
    assert result["status"] == "succeeded"
    await db_session.commit()

    db_session.expire_all()
    review = await service.get_visual_design_director_state(session_id)
    assert review["visual_design_director"]["status"] == "design_review"
    assert review["visual_design_director"]["stages_run"] == ["establish_visual_language"]
    assert review["visual_design_director"]["pages"][0]["route_id"] == "home"

    approved = await service.approve(session_id)
    assert approved["visual_design_director"]["status"] == "approved"
    assert approved["visual_design_director"]["approved"] is not None


@pytest.mark.asyncio
async def test_start_rejected_when_content_architect_not_approved(db_session) -> None:
    session = await PortfolioSessionRepository(db_session).create("Not approved yet")
    session_id = session.id
    service = VisualDesignDirectorService(
        VisualDesignDirectorRepository(db_session), JobService(db_session)
    )

    with pytest.raises(VisualDesignDirectorOperationError) as exc_info:
        await service.start(session_id, {})
    assert exc_info.value.code == "VISUAL_DESIGN_DIRECTOR_CONTENT_ARCHITECT_NOT_APPROVED"


@pytest.mark.asyncio
async def test_revision_re_runs_build(db_session, monkeypatch) -> None:
    session = await PortfolioSessionRepository(db_session).create("Revision visual design director")
    session_id = session.id
    await _approve_discovery_and_content_architect(db_session, session_id, monkeypatch)

    service = VisualDesignDirectorService(
        VisualDesignDirectorRepository(db_session), JobService(db_session)
    )
    monkeypatch.setattr(
        "oryxenai.jobs.handlers.visual_design_director._build_visual_design_director_agent",
        _mock_vdd_agent_factory,
    )

    started = await service.start(session_id, {})
    await db_session.commit()
    build_job = await JobService(db_session).get(UUID(started["visual_design_director"]["job_id"]))
    await VisualDesignDirectorBuildHandler().execute(build_job.payload, "test-worker")
    await db_session.commit()
    db_session.expire_all()

    revised = await service.revise(session_id, "Use a lighter palette")
    await db_session.commit()
    assert revised["visual_design_director"]["status"] == "build_running"

    revise_job = await JobService(db_session).get(UUID(revised["visual_design_director"]["job_id"]))
    result = await VisualDesignDirectorBuildHandler().execute(revise_job.payload, "test-worker")
    assert result["status"] == "succeeded"
    await db_session.commit()

    db_session.expire_all()
    review = await service.get_visual_design_director_state(session_id)
    assert review["visual_design_director"]["status"] == "design_review"
    assert "lighter" in review["visual_design_director"]["visual_language"]["color_behavior"]


@pytest.mark.asyncio
async def test_duplicate_start_does_not_create_second_run(db_session, monkeypatch) -> None:
    session = await PortfolioSessionRepository(db_session).create("Duplicate start")
    session_id = session.id
    await _approve_discovery_and_content_architect(db_session, session_id, monkeypatch)

    service = VisualDesignDirectorService(
        VisualDesignDirectorRepository(db_session), JobService(db_session)
    )
    first = await service.start(session_id, {})
    await db_session.commit()
    second = await service.start(session_id, {})
    await db_session.commit()

    assert first["visual_design_director"]["job_id"] == second["visual_design_director"]["job_id"]

    from sqlalchemy import select

    result = await db_session.execute(
        select(AgentRun.id).where(
            AgentRun.portfolio_session_id == session_id,
            AgentRun.agent_key == "visual_design_director",
        )
    )
    assert len(result.all()) == 1


@pytest.mark.asyncio
async def test_worker_failure_surfaces_only_after_retries_exhausted(
    db_session, monkeypatch
) -> None:
    session = await PortfolioSessionRepository(db_session).create("Failure visual design director")
    session_id = session.id
    await _approve_discovery_and_content_architect(db_session, session_id, monkeypatch)

    service = VisualDesignDirectorService(
        VisualDesignDirectorRepository(db_session), JobService(db_session)
    )
    started = await service.start(session_id, {})
    await db_session.commit()
    max_attempts = started["visual_design_director"]["max_attempts"]

    monkeypatch.setattr(
        "oryxenai.jobs.handlers.visual_design_director._build_visual_design_director_agent",
        lambda *args, **kwargs: _BoomAgent(),
    )

    build_job = await JobService(db_session).get(UUID(started["visual_design_director"]["job_id"]))
    payload = dict(build_job.payload)
    payload["attempt"] = max_attempts
    with pytest.raises(ProviderTimeoutError):
        await VisualDesignDirectorBuildHandler().execute(payload, "test-worker")
    await db_session.commit()

    db_session.expire_all()
    state_data = await service.get_visual_design_director_state(session_id)
    assert state_data["visual_design_director"]["status"] == "needs_attention"
    assert state_data["visual_design_director"]["latest_error"]["code"] == "PROVIDER_TIMEOUT_ERROR"


@pytest.mark.asyncio
async def test_transient_failure_does_not_surface_while_retries_remain(
    db_session, monkeypatch
) -> None:
    session = await PortfolioSessionRepository(db_session).create(
        "Transient failure visual design director"
    )
    session_id = session.id
    await _approve_discovery_and_content_architect(db_session, session_id, monkeypatch)

    service = VisualDesignDirectorService(
        VisualDesignDirectorRepository(db_session), JobService(db_session)
    )
    started = await service.start(session_id, {})
    await db_session.commit()
    assert started["visual_design_director"]["max_attempts"] > 1

    monkeypatch.setattr(
        "oryxenai.jobs.handlers.visual_design_director._build_visual_design_director_agent",
        lambda *args, **kwargs: _BoomAgent(),
    )

    build_job = await JobService(db_session).get(UUID(started["visual_design_director"]["job_id"]))
    payload = dict(build_job.payload)
    payload["attempt"] = 1
    with pytest.raises(ProviderTimeoutError):
        await VisualDesignDirectorBuildHandler().execute(payload, "test-worker")
    await db_session.commit()

    db_session.expire_all()
    state_data = await service.get_visual_design_director_state(session_id)
    assert state_data["visual_design_director"]["status"] == "build_running"
    assert state_data["visual_design_director"]["latest_error"] is None


@pytest.mark.asyncio
async def test_stale_source_rejected_before_persisting_success(db_session, monkeypatch) -> None:
    """Content Architect being re-approved with different content while a
    Visual Design Director build is in flight must be caught at the
    pre-persist re-check, not just at the API-level revise() check."""
    session = await PortfolioSessionRepository(db_session).create(
        "Stale source visual design director"
    )
    session_id = session.id
    await _approve_discovery_and_content_architect(db_session, session_id, monkeypatch)

    service = VisualDesignDirectorService(
        VisualDesignDirectorRepository(db_session), JobService(db_session)
    )
    monkeypatch.setattr(
        "oryxenai.jobs.handlers.visual_design_director._build_visual_design_director_agent",
        _mock_vdd_agent_factory,
    )

    started = await service.start(session_id, {})
    await db_session.commit()
    build_job = await JobService(db_session).get(UUID(started["visual_design_director"]["job_id"]))
    payload = dict(build_job.payload)

    # Mutate Content Architect's approved content hash directly, simulating a
    # re-approval that happened while this build was still running.
    session_row = await PortfolioSessionRepository(db_session).get_by_id(session_id)
    new_state = dict(session_row.current_state)
    new_state["content_architect"]["approved"]["content_hash"] = "a-different-hash"
    await PortfolioSessionRepository(db_session).update_state(
        session_id, new_state, session_row.revision
    )
    await db_session.commit()
    db_session.expire_all()

    result = await VisualDesignDirectorBuildHandler().execute(payload, "test-worker")
    assert result["status"] == "failed"
    await db_session.commit()

    db_session.expire_all()
    state_data = await service.get_visual_design_director_state(session_id)
    assert state_data["visual_design_director"]["status"] == "needs_attention"
    assert (
        state_data["visual_design_director"]["latest_error"]["code"]
        == "VISUAL_DESIGN_DIRECTOR_STALE_SOURCE"
    )
