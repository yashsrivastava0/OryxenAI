"""Durable Discovery worker flow using the deterministic fake client."""

from __future__ import annotations

from uuid import UUID

import pytest

from oryxenai.agents.discovery.agent import DiscoveryAgent
from oryxenai.agents.discovery.fake_client import FakeDiscoveryModelClient
from oryxenai.agents.discovery.schemas import DiscoveryAnswer, DiscoveryIntake, ResumeSource
from oryxenai.agents.discovery.service import DiscoveryService
from oryxenai.db.repositories.discovery import DiscoveryRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository
from oryxenai.jobs.handlers.discovery import (
    DiscoveryBuildBriefHandler,
    DiscoveryPrepareQuestionsHandler,
)
from oryxenai.jobs.service import JobService

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_call_a_call_b_and_approval_use_worker_path(db_session, monkeypatch) -> None:
    session = await PortfolioSessionRepository(db_session).create("Worker discovery")
    session_id = session.id
    service = DiscoveryService(DiscoveryRepository(db_session), JobService(db_session))
    intake = DiscoveryIntake(
        main_prompt="I am mainly looking for backend engineering roles.",
        resume_text=(
            "Test User\n"
            "Software Engineer\n"
            "Example Corp\n"
            "Senior Software Engineer\n"
            "Implemented retry handling and stale-job recovery for the PostgreSQL worker\n"
            "observability\n"
            "Docker\n"
            "Python, PostgreSQL, FastAPI\n"
            "migrations\n"
        ),
        resume_source=ResumeSource.PASTED_TEXT,
        output_language="en",
    )
    await service.process_intake(session_id, intake, expected_revision=0)
    await db_session.commit()

    queued = await service.enqueue_questions(session_id, expected_revision=1)
    await db_session.commit()
    question_job = await JobService(db_session).get(UUID(queued["job_id"]))
    assert question_job is not None

    monkeypatch.setattr(
        "oryxenai.jobs.handlers.discovery._build_discovery_agent",
        lambda: DiscoveryAgent(model_client=FakeDiscoveryModelClient()),
    )
    await DiscoveryPrepareQuestionsHandler().execute(question_job.payload, "test-worker")

    db_session.expire_all()
    state_data = await service.get_discovery_state(session_id)
    assert state_data["discovery"]["status"] == "questions_ready"
    questions = state_data["discovery"]["questions"]["items"]
    answers = [
        DiscoveryAnswer(question_id=questions[0]["local_key"], mode="answered", value="recruiters"),
        DiscoveryAnswer(question_id=questions[1]["local_key"], mode="skipped"),
        DiscoveryAnswer(question_id=questions[2]["local_key"], mode="auto", value="technical"),
    ]
    answer_state = await service.save_answers(
        session_id,
        answers,
        question_version=state_data["discovery"]["questions"]["version"],
        complete=True,
        expected_revision=state_data["session_revision"],
    )
    await db_session.commit()
    brief_job_data = await service.enqueue_brief(
        session_id,
        expected_revision=answer_state["session_revision"],
    )
    await db_session.commit()
    brief_job = await JobService(db_session).get(UUID(brief_job_data["job_id"]))
    assert brief_job is not None
    result = await DiscoveryBuildBriefHandler().execute(brief_job.payload, "test-worker")
    assert result["status"] == "succeeded"

    db_session.expire_all()
    review = await service.get_discovery_state(session_id)
    assert review["discovery"]["status"] == "brief_review"
    approved = await service.approve_brief(session_id, expected_revision=review["session_revision"])
    assert approved["discovery"]["status"] == "approved"
    assert approved["discovery"]["brief"]["approved_brief"] is not None
