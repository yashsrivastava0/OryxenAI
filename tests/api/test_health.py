"""API tests for health endpoints."""

from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

from oryxenai.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_liveness_ok(client):
    """Liveness always returns 200 and does not depend on PostgreSQL."""
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "alive"


async def test_agent_listing(client):
    """The agents endpoint returns all five registered agents."""
    resp = await client.get("/api/v1/agents")
    assert resp.status_code == 200
    agents = resp.json()
    keys = {a["key"] for a in agents}
    assert keys == {
        "discovery",
        "content_architect",
        "visual_design_director",
        "build_preparation",
        "code_generator",
    }
    for a in agents:
        assert a["mock"] is True
        assert a["name"]
        assert a["description"]


async def test_readiness_returns_status(client):
    """Readiness returns 200 (DB up) or 503 (DB down) — never 500."""
    resp = await client.get("/health/ready")
    assert resp.status_code in (200, 503)
    body = resp.json()
    assert "status" in body
    assert "database" in body
