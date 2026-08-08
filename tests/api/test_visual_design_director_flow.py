"""HTTP-level Visual Design Director flow tests.

Exercises the full flow through the ASGI app with the deterministic test
mock client: (Discovery approved -> Content Architect approved) -> start ->
build -> design_review -> approve, plus revision, content-architect-not-approved
rejection, staleness rejection, and idempotent start.
"""

from __future__ import annotations

from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport

from oryxenai.agents.content_architect.agent import ContentArchitectAgent
from oryxenai.agents.discovery.agent import DiscoveryAgent
from oryxenai.agents.visual_design_director.agent import VisualDesignDirectorAgent
from oryxenai.jobs.handlers.content_architect import ContentArchitectBuildHandler
from oryxenai.jobs.handlers.discovery import (
    DiscoveryBuildOrReviseBriefHandler,
    DiscoveryUnderstandAndQuestionHandler,
)
from oryxenai.jobs.handlers.visual_design_director import VisualDesignDirectorBuildHandler
from oryxenai.main import create_app
from tests.conftest import (
    _ContentArchitectMockModelClient,
    _MockModelClient,
    _VisualDesignDirectorMockModelClient,
)

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
    monkeypatch.setattr(
        "oryxenai.jobs.handlers.visual_design_director._build_visual_design_director_agent",
        lambda *args, **kwargs: VisualDesignDirectorAgent(
            model_client=_VisualDesignDirectorMockModelClient()
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
_VISUAL_DESIGN_DIRECTOR_HANDLERS = {
    "visual_design_director.build": VisualDesignDirectorBuildHandler()
}


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


async def _approve_content_architect(client, sid: str) -> dict:
    """Drive Content Architect to `approved` via the real API."""
    resp = await client.post(f"/api/v1/sessions/{sid}/content-architect/start", json={})
    assert resp.status_code == 202, resp.text
    started = resp.json()
    await _run_job(client, started["content_architect"]["job_id"], _CONTENT_ARCHITECT_HANDLERS)

    resp = await client.post(f"/api/v1/sessions/{sid}/content-architect/approve")
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _build_visual_design(client, sid: str) -> dict:
    resp = await client.post(f"/api/v1/sessions/{sid}/visual-design-director/start", json={})
    assert resp.status_code == 202, resp.text
    started = resp.json()
    assert started["visual_design_director"]["status"] == "build_running"

    await _run_job(
        client, started["visual_design_director"]["job_id"], _VISUAL_DESIGN_DIRECTOR_HANDLERS
    )

    resp = await client.get(f"/api/v1/sessions/{sid}/visual-design-director")
    assert resp.status_code == 200
    return resp.json()


async def _mutate_content_architect_hash(client, sid: str, new_hash: str) -> None:
    from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository

    app = client._transport.app
    async with app.state.sessionmaker() as db:
        repo = PortfolioSessionRepository(db)
        session = await repo.get_by_id(UUID(sid))
        new_state = dict(session.current_state)
        new_state["content_architect"]["approved"]["content_hash"] = new_hash
        await repo.update_state(UUID(sid), new_state, session.revision)
        await db.commit()


async def _approved_session(client) -> str:
    sid = await _approve_discovery(client)
    await _approve_content_architect(client, sid)
    return sid


class TestFullHttpFlow:
    async def test_full_flow_and_approval(self, client):
        sid = await _approved_session(client)
        review = await _build_visual_design(client, sid)
        assert review["visual_design_director"]["status"] == "design_review"
        assert review["visual_design_director"]["visual_language"]
        assert review["visual_design_director"]["pages"]
        assert review["visual_design_director"]["stages_run"] == ["establish_visual_language"]

        resp = await client.post(f"/api/v1/sessions/{sid}/visual-design-director/approve")
        assert resp.status_code == 200, resp.text
        approved = resp.json()
        assert approved["visual_design_director"]["status"] == "approved"
        assert approved["visual_design_director"]["approved"]["visual_direction_hash"]

    async def test_start_requires_content_architect_approved(self, client):
        sid = await _approve_discovery(client)
        resp = await client.post(f"/api/v1/sessions/{sid}/visual-design-director/start", json={})
        assert resp.status_code == 409
        assert (
            resp.json()["error"]["code"] == "VISUAL_DESIGN_DIRECTOR_CONTENT_ARCHITECT_NOT_APPROVED"
        )

    async def test_revision_endpoint_reruns_build(self, client):
        sid = await _approved_session(client)
        await _build_visual_design(client, sid)

        resp = await client.post(
            f"/api/v1/sessions/{sid}/visual-design-director/revise",
            json={"revision_request": "Use a lighter palette"},
        )
        assert resp.status_code == 202, resp.text
        revised = resp.json()
        assert revised["visual_design_director"]["status"] == "build_running"
        assert revised["visual_design_director"]["revision_request"] == "Use a lighter palette"

        await _run_job(
            client,
            revised["visual_design_director"]["job_id"],
            _VISUAL_DESIGN_DIRECTOR_HANDLERS,
        )

        resp = await client.get(f"/api/v1/sessions/{sid}/visual-design-director")
        review = resp.json()
        assert review["visual_design_director"]["status"] == "design_review"
        assert "lighter" in review["visual_design_director"]["visual_language"]["color_behavior"]

    async def test_revision_rejected_from_wrong_state(self, client):
        sid = await _approved_session(client)
        resp = await client.post(
            f"/api/v1/sessions/{sid}/visual-design-director/revise",
            json={"revision_request": "change it"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "VISUAL_DESIGN_DIRECTOR_NOT_READY"

    async def test_revise_rejected_when_content_architect_source_is_stale(self, client):
        sid = await _approved_session(client)
        await _build_visual_design(client, sid)

        await _mutate_content_architect_hash(client, sid, "a-different-hash")

        resp = await client.post(
            f"/api/v1/sessions/{sid}/visual-design-director/revise",
            json={"revision_request": "change it"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "VISUAL_DESIGN_DIRECTOR_STALE_SOURCE"

    async def test_duplicate_start_is_idempotent(self, client):
        sid = await _approved_session(client)
        resp1 = await client.post(f"/api/v1/sessions/{sid}/visual-design-director/start", json={})
        resp2 = await client.post(f"/api/v1/sessions/{sid}/visual-design-director/start", json={})
        assert resp1.status_code == 202
        assert resp2.status_code == 202
        assert (
            resp1.json()["visual_design_director"]["job_id"]
            == resp2.json()["visual_design_director"]["job_id"]
        )

        from sqlalchemy import select

        from oryxenai.db.models.agent_run import AgentRun

        app = client._transport.app
        async with app.state.sessionmaker() as db:
            result = await db.execute(
                select(AgentRun.id).where(
                    AgentRun.portfolio_session_id == UUID(sid),
                    AgentRun.agent_key == "visual_design_director",
                )
            )
            run_ids = result.all()
        assert len(run_ids) == 1

    async def test_duplicate_approve_is_idempotent(self, client):
        sid = await _approved_session(client)
        await _build_visual_design(client, sid)
        resp1 = await client.post(f"/api/v1/sessions/{sid}/visual-design-director/approve")
        assert resp1.status_code == 200
        resp2 = await client.post(f"/api/v1/sessions/{sid}/visual-design-director/approve")
        assert resp2.status_code == 200
