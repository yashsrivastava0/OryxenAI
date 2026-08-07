"""Integration API tests for mock agent runs — require PostgreSQL."""

from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

from oryxenai.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
async def client(test_engine):
    app = create_app()
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from oryxenai.db.session import get_engine

    settings = app.state.settings
    app.state.engine = get_engine(settings)
    app.state.sessionmaker = async_sessionmaker(app.state.engine, expire_on_commit=False)

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _create_session(client) -> str:
    resp = await client.post("/api/v1/sessions", json={})
    return resp.json()["id"]


async def test_valid_mock_run(client):
    """A valid mock run persists output and updates session state."""
    sid = await _create_session(client)
    resp = await client.post(
        f"/api/v1/sessions/{sid}/runs/mock",
        json={
            "agentKey": "discovery",
            "input": {"prompt": "test portfolio"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "succeeded"
    assert body["agent_key"] == "discovery"
    assert body["output_payload"] is not None
    assert body["output_payload"].get("operation") in {
        "understand_and_question",
        "build_or_revise_brief",
    }
    assert "questions" in body["output_payload"]
    assert body["state_before"] == {}
    assert body["state_after"] is not None
    assert body["error_payload"] is None

    # Session state updated.
    session = await client.get(f"/api/v1/sessions/{sid}")
    session_body = session.json()
    assert session_body["revision"] == 1
    assert "agents" in session_body["current_state"]
    assert "discovery" in session_body["current_state"]["agents"]


async def test_unknown_agent(client):
    """An unknown agent key returns a controlled error."""
    sid = await _create_session(client)
    resp = await client.post(
        f"/api/v1/sessions/{sid}/runs/mock",
        json={"agentKey": "nonexistent", "input": {}},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "AGENT_NOT_FOUND"


async def test_each_agent_succeeds(client):
    """All four registered agents execute a mock run."""
    sid = await _create_session(client)
    for agent_key in ["discovery", "content_architect", "visual_design_director", "code_generator"]:
        resp = await client.post(
            f"/api/v1/sessions/{sid}/runs/mock",
            json={"agentKey": agent_key, "input": {}},
        )
        assert resp.status_code == 200, f"agent {agent_key} failed"
        assert resp.json()["status"] == "succeeded"


async def test_run_history(client):
    """Run history is retrievable and ordered."""
    sid = await _create_session(client)
    await client.post(
        f"/api/v1/sessions/{sid}/runs/mock",
        json={"agentKey": "discovery", "input": {}},
    )
    await client.post(
        f"/api/v1/sessions/{sid}/runs/mock",
        json={"agentKey": "content_architect", "input": {}},
    )
    resp = await client.get(f"/api/v1/sessions/{sid}/runs")
    assert resp.status_code == 200
    runs = resp.json()
    assert len(runs) == 2
    # Most recent first.
    assert runs[0]["created_at"] >= runs[1]["created_at"]


async def test_empty_run_history(client):
    """An empty run history returns []."""
    sid = await _create_session(client)
    resp = await client.get(f"/api/v1/sessions/{sid}/runs")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_duplicate_idempotency_key(client):
    """A duplicate idempotency key returns the original run."""
    sid = await _create_session(client)
    payload = {
        "agentKey": "discovery",
        "input": {"prompt": "first run"},
        "idempotencyKey": "test-key-123",
    }
    first = await client.post(f"/api/v1/sessions/{sid}/runs/mock", json=payload)
    assert first.status_code == 200
    first_run = first.json()

    # Same idempotency key — should return the same run.
    second = await client.post(f"/api/v1/sessions/{sid}/runs/mock", json=payload)
    assert second.status_code == 200
    second_run = second.json()
    assert first_run["id"] == second_run["id"]


async def test_invalid_session_id_for_run(client):
    """A malformed session ID returns a validation error."""
    resp = await client.post(
        "/api/v1/sessions/not-a-uuid/runs/mock",
        json={"agentKey": "discovery", "input": {}},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_run_for_nonexistent_session(client):
    """A run for a non-existent session returns 404."""
    resp = await client.post(
        "/api/v1/sessions/00000000-0000-0000-0000-000000000000/runs/mock",
        json={"agentKey": "discovery", "input": {}},
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "SESSION_NOT_FOUND"
