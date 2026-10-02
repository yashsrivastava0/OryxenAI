"""Integration API tests for session endpoints — require PostgreSQL."""

from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

from oryxenai.main import create_app
from tests.conftest import install_test_identity

pytestmark = pytest.mark.integration


@pytest.fixture
async def client(test_engine):
    """Create a test client backed by the test database."""
    app = create_app()
    # Override the sessionmaker to use the test engine.
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from oryxenai.db.session import get_engine

    settings = app.state.settings
    app.state.engine = get_engine(settings)
    app.state.sessionmaker = async_sessionmaker(app.state.engine, expire_on_commit=False)
    await install_test_identity(app, test_engine, role="user")

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_create_session(client):
    """POST /sessions creates a portfolio session."""
    resp = await client.post(
        "/api/v1/sessions",
        json={"name": "Test session"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Test session"
    assert body["status"] == "active"
    assert body["revision"] == 0
    assert body["current_state"] == {}
    assert "id" in body
    assert "created_at" in body


async def test_create_session_default_name(client):
    """POST /sessions without a name uses the default."""
    resp = await client.post("/api/v1/sessions", json={})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Untitled session"


async def test_list_sessions(client):
    """GET /sessions returns the normal user's single entitlement session."""
    first = await client.post("/api/v1/sessions", json={"name": "A"})
    second = await client.post("/api/v1/sessions", json={"name": "B"})
    resp = await client.get("/api/v1/sessions")
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) == 1
    assert second.json()["id"] == first.json()["id"] == sessions[0]["id"]


async def test_get_session_by_id(client):
    """GET /sessions/{id} returns the session with state."""
    create = await client.post("/api/v1/sessions", json={"name": "Get me"})
    sid = create.json()["id"]
    resp = await client.get(f"/api/v1/sessions/{sid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == sid
    assert resp.json()["name"] == "Get me"


async def test_get_session_invalid_id(client):
    """Invalid UUID format returns a 400 validation error."""
    resp = await client.get("/api/v1/sessions/not-a-uuid")
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


async def test_get_session_not_found(client):
    """A valid but non-existent UUID returns 404."""
    resp = await client.get("/api/v1/sessions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "SESSION_NOT_FOUND"


async def test_create_session_name_too_long(client):
    """An excessively long session name returns a validation error."""
    long_name = "x" * 300
    resp = await client.post("/api/v1/sessions", json={"name": long_name})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


async def test_error_response_structure(client):
    """All errors use the consistent structured format."""
    resp = await client.get("/api/v1/sessions/not-a-uuid")
    body = resp.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]
    assert "requestId" in body["error"]


async def test_owner_can_reset_discovery_to_empty_session(client):
    created = await client.post("/api/v1/sessions", json={"name": "Portfolio workspace"})
    sid = created.json()["id"]
    started = await client.post(
        f"/api/v1/sessions/{sid}/discovery/start",
        json={"source_text": "Backend engineer with portfolio projects", "goal": "portfolio"},
    )
    assert started.status_code == 202

    reset = await client.post(f"/api/v1/sessions/{sid}/reset", json={})
    assert reset.status_code == 200
    assert reset.json()["id"] == sid
    assert reset.json()["current_state"] == {}
    discovery = await client.get(f"/api/v1/sessions/{sid}/discovery")
    assert discovery.status_code == 200
    assert discovery.json()["discovery"]["status"] == "not_started"


async def test_document_extraction_is_available_before_session_creation(client):
    extracted = await client.post(
        "/api/v1/discovery-documents/extract?filename=resume.md",
        content=b"# Resume\nBuilt reliable systems.",
        headers={"Content-Type": "application/octet-stream"},
    )
    assert extracted.status_code == 200
    assert extracted.json()["text"] == "# Resume\nBuilt reliable systems."

    created = await client.post("/api/v1/sessions", json={})
    sid = created.json()["id"]
    started = await client.post(
        f"/api/v1/sessions/{sid}/discovery/start",
        json={"document_text": extracted.json()["text"], "goal": "create my portfolio"},
    )
    assert started.status_code == 202
    assert any(
        document["original_text"] == "# Resume\nBuilt reliable systems."
        for document in started.json()["discovery"]["source_documents"]
    )

    invalid = await client.post(
        "/api/v1/discovery-documents/extract?filename=resume.pdf",
        content=b"not a PDF",
        headers={"Content-Type": "application/octet-stream"},
    )
    assert invalid.status_code == 400
