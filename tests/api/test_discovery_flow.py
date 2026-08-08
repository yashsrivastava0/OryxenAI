"""HTTP-level Discovery chat flow tests.

Exercises the full flow through the ASGI app with the deterministic test
mock client: start -> Operation A -> answers -> Operation B -> approve, plus
revision, error surfacing, and retry behavior.
"""

from __future__ import annotations

from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport

from oryxenai.agents.discovery.agent import DiscoveryAgent
from oryxenai.agents.shared.providers.errors import ProviderTimeoutError
from oryxenai.main import create_app
from tests.conftest import _MockModelClient

pytestmark = pytest.mark.integration


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
        lambda *args, **kwargs: DiscoveryAgent(model_client=_MockModelClient()),
    )
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await app.state.engine.dispose()


async def _create_session(client) -> str:
    resp = await client.post("/api/v1/sessions", json={})
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


async def _start(client, sid: str, **overrides) -> dict:
    body = {
        "message": "Create a portfolio for me. I am a software developer.",
        "document_text": (
            "Test User\nSoftware Engineer\nExample Corp\n"
            "Implemented retry handling for a PostgreSQL worker\n"
            "Python, PostgreSQL, FastAPI, Docker\n"
        ),
        "goal": "get hired",
    }
    body.update(overrides)
    resp = await client.post(f"/api/v1/sessions/{sid}/discovery/start", json=body)
    assert resp.status_code == 202, resp.text
    return resp.json()


async def _run_worker_job(client, job_id: str, *, attempt: int | None = None) -> None:
    """Run a job's handler directly, as worker.py::_execute_one would.

    `attempt` mirrors what the real worker injects into the payload from the
    claimed job row (payload["attempt"] = job.attempt) before invoking the
    handler — pass the session's max_attempts here to simulate the final,
    exhausted attempt.
    """
    from oryxenai.jobs.handlers.discovery import (
        DiscoveryBuildBriefHandler,
        DiscoveryBuildOrReviseBriefHandler,
        DiscoveryPrepareQuestionsHandler,
        DiscoveryUnderstandAndQuestionHandler,
    )
    from oryxenai.jobs.service import JobService

    app = client._transport.app
    async with app.state.sessionmaker() as db:
        job = await JobService(db).get(UUID(job_id))
        assert job is not None
        kind = job.job_kind
        payload = dict(job.payload)
        if attempt is not None:
            payload["attempt"] = attempt
    handlers = {
        "discovery.understand_and_question": DiscoveryUnderstandAndQuestionHandler(),
        "discovery.build_or_revise_brief": DiscoveryBuildOrReviseBriefHandler(),
        "discovery.prepare_questions": DiscoveryPrepareQuestionsHandler(),
        "discovery.build_brief": DiscoveryBuildBriefHandler(),
    }
    handler = handlers.get(kind)
    assert handler is not None, f"no handler for {kind}"
    await handler.execute(payload, "test-worker")


async def _answer_all(client, sid: str, state: dict) -> dict:
    questions = state["discovery"]["operation_a"]["items"]
    answers = [
        {"question_id": question["id"], "mode": "answered", "value": "pick-one"}
        for question in questions
    ]
    resp = await client.put(
        f"/api/v1/sessions/{sid}/discovery/answers",
        json={"complete": True, "answers": answers},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _full_flow(client, sid: str) -> dict:
    started = await _start(client, sid)
    assert started["discovery"]["status"] == "questions_queued"
    assert started["discovery"]["intake"]["message"]
    assert started["discovery"]["started_at"] is not None

    await _run_worker_job(client, started["discovery"]["operation_a"]["job_id"])

    resp = await client.get(f"/api/v1/sessions/{sid}/discovery")
    assert resp.status_code == 200
    state = resp.json()
    assert state["discovery"]["status"] == "questions_ready"
    assert state["discovery"]["operation_a"]["mode"] == "ASK_QUESTIONS"
    questions = state["discovery"]["operation_a"]["items"]
    assert 0 < len(questions) <= 8

    answered = await _answer_all(client, sid, state)
    assert answered["discovery"]["status"] == "brief_running"

    await _run_worker_job(client, answered["discovery"]["brief"]["job_id"])

    resp = await client.get(f"/api/v1/sessions/{sid}/discovery")
    assert resp.status_code == 200
    return resp.json()


class TestFullHttpFlow:
    async def test_full_flow_and_approval(self, client):
        sid = await _create_session(client)
        review = await _full_flow(client, sid)
        assert review["discovery"]["status"] == "brief_review"
        brief = review["discovery"]["brief"]
        assert brief["title"]
        assert brief["markdown"]
        assert brief["user_summary"]
        assert brief["profile"]["name"]
        assert isinstance(brief["open_items"], list)

        resp = await client.post(f"/api/v1/sessions/{sid}/discovery/approve", json={})
        assert resp.status_code == 200, resp.text
        approved = resp.json()
        assert approved["discovery"]["status"] == "approved"
        assert approved["discovery"]["brief"]["approved"] is not None

    async def test_revision_endpoint_enqueues_brief_and_stays_in_review(self, client):
        sid = await _create_session(client)
        await _full_flow(client, sid)

        resp = await client.post(
            f"/api/v1/sessions/{sid}/discovery/revise",
            json={"revision_request": "Lead with the QueueGuard story"},
        )
        assert resp.status_code == 202, resp.text
        revised = resp.json()
        assert revised["discovery"]["status"] == "brief_running"

        await _run_worker_job(client, revised["discovery"]["brief"]["job_id"])

        resp = await client.get(f"/api/v1/sessions/{sid}/discovery")
        assert resp.status_code == 200
        review = resp.json()
        assert review["discovery"]["status"] == "brief_review"
        assert "QueueGuard" in review["discovery"]["brief"]["markdown"]
        assert "QueueGuard" in review["discovery"]["brief"]["user_summary"]
        assert review["discovery"]["brief"]["revision_request"] == "Lead with the QueueGuard story"

    async def test_revision_rejected_from_wrong_state(self, client):
        sid = await _create_session(client)
        await _start(client, sid)
        resp = await client.post(
            f"/api/v1/sessions/{sid}/discovery/revise",
            json={"revision_request": "change it"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "DISCOVERY_NOT_READY"

    async def test_approval_does_not_enqueue_later_agents(self, client):
        sid = await _create_session(client)
        await _full_flow(client, sid)
        resp = await client.post(f"/api/v1/sessions/{sid}/discovery/approve", json={})
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

    async def test_duplicate_approve_is_idempotent(self, client):
        sid = await _create_session(client)
        await _full_flow(client, sid)
        resp1 = await client.post(f"/api/v1/sessions/{sid}/discovery/approve", json={})
        assert resp1.status_code == 200
        resp2 = await client.post(f"/api/v1/sessions/{sid}/discovery/approve", json={})
        assert resp2.status_code == 200
        assert resp2.json()["discovery"]["status"] == "approved"


class TestInputAndErrors:
    async def test_any_input_accepted_without_validation(self, client):
        sid = await _create_session(client)
        started = await _start(
            client,
            sid,
            message="x" * 5000,
            document_text="\n".join(f"line {i}" for i in range(500)),
            goal="anything",
        )
        assert started["discovery"]["status"] == "questions_queued"

    async def test_transient_worker_failure_does_not_surface_while_retries_remain(
        self, client, monkeypatch
    ):
        """A retryable failure with attempts left must stay invisible to the user.

        The worker (worker.py) silently reschedules retryable failures with
        backoff. If discovery.status flipped to needs_attention on every
        attempt regardless of whether more retries are coming, the UI would
        show a dead-end error while the backend is about to retry on its own
        — and a user-triggered retry could then collide with that automatic
        retry once it lands (see test_worker_failure_surfaces_error for the
        final-attempt case this is contrasted with).
        """
        sid = await _create_session(client)
        started = await _start(client, sid)
        max_attempts = started["discovery"]["max_attempts"]
        assert max_attempts > 1

        def failing_agent(*args, **kwargs):
            agent = DiscoveryAgent(model_client=_MockModelClient())

            async def run(context):
                raise ProviderTimeoutError("simulated timeout")

            agent.run = run
            return agent

        monkeypatch.setattr(
            "oryxenai.jobs.handlers.discovery._build_discovery_agent", failing_agent
        )
        with pytest.raises(ProviderTimeoutError):
            await _run_worker_job(client, started["discovery"]["operation_a"]["job_id"], attempt=1)

        resp = await client.get(f"/api/v1/sessions/{sid}/discovery")
        state = resp.json()
        assert state["discovery"]["status"] == "questions_running"
        assert state["discovery"]["latest_error"] is None
        assert state["discovery"]["attempt"] == 1

    async def test_worker_failure_surfaces_error(self, client, monkeypatch):
        sid = await _create_session(client)
        started = await _start(client, sid)
        max_attempts = started["discovery"]["max_attempts"]

        def failing_agent(*args, **kwargs):
            agent = DiscoveryAgent(model_client=_MockModelClient())

            async def run(context):
                raise ProviderTimeoutError("simulated timeout")

            agent.run = run
            return agent

        monkeypatch.setattr(
            "oryxenai.jobs.handlers.discovery._build_discovery_agent", failing_agent
        )
        with pytest.raises(ProviderTimeoutError):
            await _run_worker_job(
                client, started["discovery"]["operation_a"]["job_id"], attempt=max_attempts
            )

        resp = await client.get(f"/api/v1/sessions/{sid}/discovery")
        state = resp.json()
        assert state["discovery"]["status"] == "needs_attention"
        assert state["discovery"]["latest_error"]["code"] == "PROVIDER_TIMEOUT_ERROR"

    async def test_retry_after_failure_restarts(self, client, monkeypatch):
        sid = await _create_session(client)
        started = await _start(client, sid)
        max_attempts = started["discovery"]["max_attempts"]

        def failing_agent(*args, **kwargs):
            agent = DiscoveryAgent(model_client=_MockModelClient())

            async def run(context):
                raise ProviderTimeoutError("simulated timeout")

            agent.run = run
            return agent

        monkeypatch.setattr(
            "oryxenai.jobs.handlers.discovery._build_discovery_agent", failing_agent
        )
        with pytest.raises(ProviderTimeoutError):
            await _run_worker_job(
                client, started["discovery"]["operation_a"]["job_id"], attempt=max_attempts
            )

        retried = await _start(client, sid)
        assert retried["discovery"]["status"] == "questions_queued"

        monkeypatch.setattr(
            "oryxenai.jobs.handlers.discovery._build_discovery_agent",
            lambda *args, **kwargs: DiscoveryAgent(model_client=_MockModelClient()),
        )
        await _run_worker_job(client, retried["discovery"]["operation_a"]["job_id"])
        resp = await client.get(f"/api/v1/sessions/{sid}/discovery")
        assert resp.json()["discovery"]["status"] == "questions_ready"

    async def test_start_is_idempotent_while_running(self, client):
        sid = await _create_session(client)
        started = await _start(client, sid)
        again = await _start(client, sid)
        assert again["discovery"]["status"] == "questions_queued"
        assert (
            again["discovery"]["operation_a"]["job_id"]
            == started["discovery"]["operation_a"]["job_id"]
        )

    async def test_answers_rejected_from_wrong_state(self, client):
        sid = await _create_session(client)
        await _start(client, sid)
        resp = await client.put(
            f"/api/v1/sessions/{sid}/discovery/answers",
            json={"complete": True, "answers": []},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "DISCOVERY_NOT_READY"
