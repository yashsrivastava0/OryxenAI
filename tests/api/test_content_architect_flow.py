"""HTTP-level Content Architect flow tests.

Exercises the full flow through the ASGI app with the deterministic test
mock client: (Discovery approved) -> start -> build -> content_review ->
approve, plus revision, discovery-not-approved rejection, staleness
rejection, and idempotent start.
"""

from __future__ import annotations

from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport

from oryxenai.agents.content_architect.agent import ContentArchitectAgent
from oryxenai.agents.discovery.agent import DiscoveryAgent
from oryxenai.jobs.handlers.content_architect import ContentArchitectBuildHandler
from oryxenai.jobs.handlers.discovery import (
    DiscoveryBuildOrReviseBriefHandler,
    DiscoveryUnderstandAndQuestionHandler,
)
from oryxenai.main import create_app
from tests.conftest import _ContentArchitectMockModelClient, _MockModelClient

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
    monkeypatch.setattr(
        "oryxenai.jobs.handlers.content_architect._build_content_architect_agent",
        lambda *args, **kwargs: ContentArchitectAgent(
            model_client=_ContentArchitectMockModelClient()
        ),
    )
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await app.state.engine.dispose()


async def _create_session(client) -> str:
    resp = await client.post("/api/v1/sessions", json={})
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


async def _run_job(client, job_id: str, handlers: dict) -> None:
    from oryxenai.jobs.service import JobService

    app = client._transport.app
    async with app.state.sessionmaker() as db:
        job = await JobService(db).get(UUID(job_id))
        assert job is not None
        kind = job.job_kind
        payload = dict(job.payload)
    handler = handlers.get(kind)
    assert handler is not None, f"no handler for {kind}"
    await handler.execute(payload, "test-worker")


_DISCOVERY_HANDLERS = {
    "discovery.understand_and_question": DiscoveryUnderstandAndQuestionHandler(),
    "discovery.build_or_revise_brief": DiscoveryBuildOrReviseBriefHandler(),
}
_CONTENT_ARCHITECT_HANDLERS = {"content_architect.build": ContentArchitectBuildHandler()}


async def _approve_discovery(client) -> str:
    """Create a session and drive Discovery to `approved` via the real API."""
    sid = await _create_session(client)
    resp = await client.post(
        f"/api/v1/sessions/{sid}/discovery/start",
        json={
            "message": "Create a portfolio for me. I am a software developer.",
            "document_text": "Test User\nSoftware Engineer\nExample Corp\n",
            "goal": "get hired",
        },
    )
    assert resp.status_code == 202, resp.text
    started = resp.json()
    await _run_job(client, started["discovery"]["operation_a"]["job_id"], _DISCOVERY_HANDLERS)

    resp = await client.get(f"/api/v1/sessions/{sid}/discovery")
    state = resp.json()
    questions = state["discovery"]["operation_a"]["items"]
    answers = [{"question_id": q["id"], "mode": "answered", "value": "pick-one"} for q in questions]
    resp = await client.put(
        f"/api/v1/sessions/{sid}/discovery/answers", json={"complete": True, "answers": answers}
    )
    assert resp.status_code == 200, resp.text
    answered = resp.json()
    await _run_job(client, answered["discovery"]["brief"]["job_id"], _DISCOVERY_HANDLERS)

    resp = await client.post(f"/api/v1/sessions/{sid}/discovery/approve", json={})
    assert resp.status_code == 200, resp.text
    return sid


async def _build_content(client, sid: str) -> dict:
    resp = await client.post(f"/api/v1/sessions/{sid}/content-architect/start", json={})
    assert resp.status_code == 202, resp.text
    started = resp.json()
    assert started["content_architect"]["status"] == "build_running"

    await _run_job(client, started["content_architect"]["job_id"], _CONTENT_ARCHITECT_HANDLERS)

    resp = await client.get(f"/api/v1/sessions/{sid}/content-architect")
    assert resp.status_code == 200
    return resp.json()


async def _mutate_discovery_brief_hash(client, sid: str, new_hash: str) -> None:
    from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository

    app = client._transport.app
    async with app.state.sessionmaker() as db:
        repo = PortfolioSessionRepository(db)
        session = await repo.get_by_id(UUID(sid))
        new_state = dict(session.current_state)
        new_state["discovery"]["brief"]["approved"]["brief_hash"] = new_hash
        await repo.update_state(UUID(sid), new_state, session.revision)
        await db.commit()


class TestFullHttpFlow:
    async def test_full_flow_and_approval(self, client):
        sid = await _approve_discovery(client)
        review = await _build_content(client, sid)
        assert review["content_architect"]["status"] == "content_review"
        assert review["content_architect"]["site_story_strategy"]
        assert review["content_architect"]["route_plan"]
        assert review["content_architect"]["page_content_packs"]
        assert review["content_architect"]["stages_run"] == ["plan_content"]

        resp = await client.post(f"/api/v1/sessions/{sid}/content-architect/approve")
        assert resp.status_code == 200, resp.text
        approved = resp.json()
        assert approved["content_architect"]["status"] == "approved"
        assert approved["content_architect"]["approved"]["content_hash"]

    async def test_start_requires_discovery_approved(self, client):
        sid = await _create_session(client)
        resp = await client.post(f"/api/v1/sessions/{sid}/content-architect/start", json={})
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CONTENT_ARCHITECT_DISCOVERY_NOT_APPROVED"

    async def test_revision_endpoint_reruns_build(self, client):
        sid = await _approve_discovery(client)
        await _build_content(client, sid)

        resp = await client.post(
            f"/api/v1/sessions/{sid}/content-architect/revise",
            json={"revision_request": "Lead with QueueGuard"},
        )
        assert resp.status_code == 202, resp.text
        revised = resp.json()
        assert revised["content_architect"]["status"] == "build_running"
        assert revised["content_architect"]["revision_request"] == "Lead with QueueGuard"

        await _run_job(client, revised["content_architect"]["job_id"], _CONTENT_ARCHITECT_HANDLERS)

        resp = await client.get(f"/api/v1/sessions/{sid}/content-architect")
        review = resp.json()
        assert review["content_architect"]["status"] == "content_review"
        assert (
            "QueueGuard leads"
            in review["content_architect"]["site_story_strategy"]["narrative_thesis"]
        )

    async def test_revision_rejected_from_wrong_state(self, client):
        sid = await _approve_discovery(client)
        resp = await client.post(
            f"/api/v1/sessions/{sid}/content-architect/revise",
            json={"revision_request": "change it"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CONTENT_ARCHITECT_NOT_READY"

    async def test_revise_rejected_when_discovery_source_is_stale(self, client):
        sid = await _approve_discovery(client)
        await _build_content(client, sid)

        await _mutate_discovery_brief_hash(client, sid, "a-different-hash")

        resp = await client.post(
            f"/api/v1/sessions/{sid}/content-architect/revise",
            json={"revision_request": "change it"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CONTENT_ARCHITECT_STALE_SOURCE"

    async def test_duplicate_start_is_idempotent(self, client):
        sid = await _approve_discovery(client)
        resp1 = await client.post(f"/api/v1/sessions/{sid}/content-architect/start", json={})
        resp2 = await client.post(f"/api/v1/sessions/{sid}/content-architect/start", json={})
        assert resp1.status_code == 202
        assert resp2.status_code == 202
        assert (
            resp1.json()["content_architect"]["job_id"]
            == resp2.json()["content_architect"]["job_id"]
        )

        from sqlalchemy import select

        from oryxenai.db.models.agent_run import AgentRun

        app = client._transport.app
        async with app.state.sessionmaker() as db:
            result = await db.execute(
                select(AgentRun.id).where(
                    AgentRun.portfolio_session_id == UUID(sid),
                    AgentRun.agent_key == "content_architect",
                )
            )
            run_ids = result.all()
        assert len(run_ids) == 1

    async def test_duplicate_approve_is_idempotent(self, client):
        sid = await _approve_discovery(client)
        await _build_content(client, sid)
        resp1 = await client.post(f"/api/v1/sessions/{sid}/content-architect/approve")
        assert resp1.status_code == 200
        resp2 = await client.post(f"/api/v1/sessions/{sid}/content-architect/approve")
        assert resp2.status_code == 200
