"""HTTP-level Discovery flow and conflict tests (Sections 25, 38-40).

Exercises the full flow through the ASGI app with the deterministic fake
client: intake -> questions -> answers -> brief -> edits -> approve, plus
409 conflict, idempotent NEXT, stale-version and stale-approval behavior.
"""

from __future__ import annotations

from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport

from oryxenai.agents.discovery.fake_client import FakeDiscoveryModelClient
from oryxenai.main import create_app

pytestmark = pytest.mark.integration

_INTAKE = {
    "main_prompt": "I am mainly looking for backend engineering roles.",
    "resume_text": (
        "Test User\nSoftware Engineer\nExample Corp\n"
        "Implemented retry handling and stale-job recovery for the PostgreSQL worker\n"
        "observability\nDocker\nPython, PostgreSQL, FastAPI\nmigrations\n"
    ),
    "resume_source": "pasted_text",
    "output_language": "en",
}


@pytest.fixture
async def client(test_engine, monkeypatch):
    app = create_app()
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from oryxenai.db.session import get_engine

    settings = app.state.settings
    app.state.engine = get_engine(settings)
    app.state.sessionmaker = async_sessionmaker(app.state.engine, expire_on_commit=False)

    monkeypatch.setattr(
        "oryxenai.jobs.handlers.discovery._build_discovery_agent",
        lambda: __import__(
            "oryxenai.agents.discovery.agent", fromlist=["DiscoveryAgent"]
        ).DiscoveryAgent(model_client=FakeDiscoveryModelClient()),
    )
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await app.state.engine.dispose()


async def _create_session(client) -> str:
    resp = await client.post("/api/v1/sessions", json={})
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


async def _run_worker_job(client, job_id: str) -> None:
    from oryxenai.jobs.handlers.discovery import (
        DiscoveryBuildBriefHandler,
        DiscoveryPrepareQuestionsHandler,
    )
    from oryxenai.jobs.service import JobService

    app = client._transport.app
    async with app.state.sessionmaker() as db:
        job = await JobService(db).get(UUID(job_id))
        assert job is not None
        kind = job.job_kind
        payload = job.payload
    if kind == "discovery.prepare_questions":
        await DiscoveryPrepareQuestionsHandler().execute(payload, "test-worker")
    elif kind == "discovery.build_brief":
        await DiscoveryBuildBriefHandler().execute(payload, "test-worker")


async def _full_flow(client, sid: str) -> dict:
    """Run intake -> Call A -> answers -> Call B; return the review state."""
    resp = await client.put(
        f"/api/v1/sessions/{sid}/discovery/input",
        json={"expected_revision": 0, **_INTAKE},
    )
    assert resp.status_code == 200, resp.text
    state = resp.json()
    assert state["discovery"]["status"] == "input_ready"

    resp = await client.post(
        f"/api/v1/sessions/{sid}/discovery/questions",
        json={"expected_revision": state["session_revision"]},
    )
    assert resp.status_code == 202, resp.text
    qjob = resp.json()
    await _run_worker_job(client, qjob["job_id"])

    resp = await client.get(f"/api/v1/sessions/{sid}/discovery")
    assert resp.status_code == 200
    state = resp.json()
    assert state["discovery"]["status"] == "questions_ready"
    questions = state["discovery"]["questions"]["items"]
    assert 0 < len(questions) <= 8

    answers = []
    for index, question in enumerate(questions):
        if index == 0:
            answers.append(
                {"question_id": question["local_key"], "mode": "answered", "value": "recruiters"}
            )
        elif question.get("allows_auto"):
            answers.append(
                {
                    "question_id": question["local_key"],
                    "mode": "auto",
                    "value": question.get("auto_answer"),
                }
            )
        else:
            answers.append({"question_id": question["local_key"], "mode": "skipped"})

    resp = await client.put(
        f"/api/v1/sessions/{sid}/discovery/answers",
        json={
            "expected_revision": state["session_revision"],
            "question_version": state["discovery"]["questions"]["version"],
            "complete": True,
            "answers": answers,
        },
    )
    assert resp.status_code == 200, resp.text
    state = resp.json()
    assert state["discovery"]["status"] == "answers_ready"

    resp = await client.post(
        f"/api/v1/sessions/{sid}/discovery/brief",
        json={"expected_revision": state["session_revision"]},
    )
    assert resp.status_code == 202, resp.text
    bjob = resp.json()
    await _run_worker_job(client, bjob["job_id"])

    resp = await client.get(f"/api/v1/sessions/{sid}/discovery")
    assert resp.status_code == 200
    return resp.json()


class TestFullHttpFlow:
    async def test_full_flow_and_approval_stops(self, client):
        sid = await _create_session(client)
        review = await _full_flow(client, sid)
        assert review["discovery"]["status"] == "brief_review"
        assert review["discovery"]["brief"]["draft"]["schema_version"] == 2
        assert review["discovery"]["brief"]["draft"]["identity_and_goal"]["primary_target_role"][
            "label"
        ]

        resp = await client.post(
            f"/api/v1/sessions/{sid}/discovery/approve",
            json={"expected_revision": review["session_revision"]},
        )
        assert resp.status_code == 200, resp.text
        approved = resp.json()
        assert approved["discovery"]["status"] == "approved"
        assert approved["discovery"]["brief"]["approved_brief"] is not None

    async def test_approval_does_not_enqueue_later_agents(self, client):
        sid = await _create_session(client)
        review = await _full_flow(client, sid)
        resp = await client.post(
            f"/api/v1/sessions/{sid}/discovery/approve",
            json={"expected_revision": review["session_revision"]},
        )
        assert resp.status_code == 200

        from sqlalchemy import select

        from oryxenai.core.settings import get_settings
        from oryxenai.db.models.agent_run import AgentRun
        from oryxenai.db.session import get_sessionmaker

        sessionmaker = get_sessionmaker(get_settings())
        async with sessionmaker() as db:
            result = await db.execute(
                select(AgentRun.agent_key).where(AgentRun.portfolio_session_id == UUID(sid))
            )
            keys = {row[0] for row in result.all()}
        assert "content_architect" not in keys
        assert "visual_design_director" not in keys
        assert "code_generator" not in keys


class TestHttpConflictsAndIdempotency:
    async def test_stale_revision_returns_409(self, client):
        sid = await _create_session(client)
        resp = await client.put(
            f"/api/v1/sessions/{sid}/discovery/input",
            json={"expected_revision": 0, **_INTAKE},
        )
        assert resp.status_code == 200
        assert resp.json()["session_revision"] == 1
        # Second intake with a stale revision (still 0) must conflict.
        changed = dict(_INTAKE)
        changed["main_prompt"] = "A different prompt."
        resp = await client.put(
            f"/api/v1/sessions/{sid}/discovery/input",
            json={"expected_revision": 0, **changed},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "DISCOVERY_REVISION_CONFLICT"

    async def test_duplicate_approve_is_idempotent(self, client):
        sid = await _create_session(client)
        review = await _full_flow(client, sid)
        rev = review["session_revision"]
        resp1 = await client.post(
            f"/api/v1/sessions/{sid}/discovery/approve", json={"expected_revision": rev}
        )
        assert resp1.status_code == 200
        state1 = resp1.json()
        resp2 = await client.post(
            f"/api/v1/sessions/{sid}/discovery/approve",
            json={"expected_revision": state1["session_revision"]},
        )
        assert resp2.status_code == 200
        assert resp2.json()["discovery"]["status"] == "approved"

    async def test_stale_question_version_rejected(self, client):
        sid = await _create_session(client)
        resp = await client.put(
            f"/api/v1/sessions/{sid}/discovery/input",
            json={"expected_revision": 0, **_INTAKE},
        )
        state = resp.json()
        resp = await client.post(
            f"/api/v1/sessions/{sid}/discovery/questions",
            json={"expected_revision": state["session_revision"]},
        )
        assert resp.status_code == 202
        enqueued = resp.json()
        resp = await client.put(
            f"/api/v1/sessions/{sid}/discovery/answers",
            json={
                "expected_revision": enqueued["session_revision"],
                "question_version": 99,  # stale
                "complete": True,
                "answers": [],
            },
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "DISCOVERY_QUESTIONS_STALE"

    async def test_edit_invalidates_approval(self, client):
        sid = await _create_session(client)
        review = await _full_flow(client, sid)
        resp = await client.post(
            f"/api/v1/sessions/{sid}/discovery/approve",
            json={"expected_revision": review["session_revision"]},
        )
        assert resp.status_code == 200
        approved = resp.json()

        edits = {
            "identity_and_goal": {
                "primary_target_role": {
                    "label": "Platform Engineer",
                    "basis_fact_ids": [],
                    "decision_source": "user_edit",
                }
            }
        }
        resp = await client.patch(
            f"/api/v1/sessions/{sid}/discovery/brief",
            json={
                "expected_revision": approved["session_revision"],
                "edits": edits,
            },
        )
        assert resp.status_code == 200, resp.text
        edited = resp.json()
        # Approval invalidated; brief back in review.
        assert edited["discovery"]["status"] == "brief_review"
        assert edited["discovery"]["brief"]["approved"] is None
        # Re-approving a stale brief must be invalidated.
        resp = await client.post(
            f"/api/v1/sessions/{sid}/discovery/approve",
            json={"expected_revision": edited["session_revision"]},
        )
        assert resp.status_code == 200  # fresh approval after edit

    async def test_unsafe_url_rejected(self, client):
        sid = await _create_session(client)
        intake = dict(_INTAKE)
        intake["links"] = [{"url": "javascript:alert(1)", "label": "bad"}]
        resp = await client.put(
            f"/api/v1/sessions/{sid}/discovery/input",
            json={"expected_revision": 0, **intake},
        )
        assert resp.status_code == 422

    async def test_factual_question_never_allows_auto(self, client):
        sid = await _create_session(client)
        review = await _full_flow(client, sid)
        questions = review["discovery"]["questions"]["items"]
        factual = {
            "target_role",
            "project_selection",
            "personal_contribution",
            "confidentiality",
            "contact",
            "conflict_resolution",
        }
        for question in questions:
            if question["category"] in factual:
                assert question["allows_auto"] is False, question
