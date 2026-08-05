"""API tests for system endpoints — require PostgreSQL."""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker

from oryxenai.jobs.heartbeat import HeartbeatRepository

pytestmark = pytest.mark.integration


@pytest.fixture
async def api_client(test_engine):
    from oryxenai.main import create_app

    app = create_app()
    app.state.engine = test_engine
    app.state.sessionmaker = async_sessionmaker(test_engine, expire_on_commit=False)

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_system_status_db_up(api_client):
    resp = await api_client.get("/api/v1/system/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database"] == "up"


async def test_system_status_has_revision(api_client):
    resp = await api_client.get("/api/v1/system/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "migration_revision" in body


async def test_system_status_worker_absent(api_client):
    resp = await api_client.get("/api/v1/system/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["worker"] == "absent"


async def test_system_status_worker_ok(api_client, test_engine):
    from sqlalchemy.ext.asyncio import AsyncSession

    sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as session:
        repo = HeartbeatRepository(session)
        await repo.upsert(str(uuid4()), "oryxenai-worker")
        await session.commit()

    resp = await api_client.get("/api/v1/system/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["worker"] == "ok"


async def test_enqueue_probe(api_client):
    resp = await api_client.post(
        "/api/v1/system/worker-probes",
        json={"job_kind": "system.worker_probe", "payload": {"message": "hello"}},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["job_kind"] == "system.worker_probe"
    assert body["status"] == "queued"
    assert "id" in body


async def test_enqueue_probe_idempotent(api_client):
    payload = {
        "job_kind": "system.worker_probe",
        "payload": {"message": "idempotent"},
        "idempotency_scope": "test",
        "idempotency_key": "key-1",
    }
    resp1 = await api_client.post("/api/v1/system/worker-probes", json=payload)
    assert resp1.status_code == 201
    resp2 = await api_client.post("/api/v1/system/worker-probes", json=payload)
    assert resp2.status_code == 201
    assert resp1.json()["id"] == resp2.json()["id"]


async def test_enqueue_probe_invalid_kind(api_client):
    resp = await api_client.post(
        "/api/v1/system/worker-probes",
        json={"job_kind": "custom.agent", "payload": {}},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


async def test_get_probe_status(api_client):
    create = await api_client.post(
        "/api/v1/system/worker-probes",
        json={"job_kind": "system.worker_probe", "payload": {"message": "status-test"}},
    )
    job_id = create.json()["id"]
    resp = await api_client.get(f"/api/v1/system/worker-probes/{job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == job_id
    assert body["status"] == "queued"


async def test_get_probe_not_found(api_client):
    resp = await api_client.get("/api/v1/system/worker-probes/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "JOB_NOT_FOUND"


async def test_get_probe_invalid_id(api_client):
    resp = await api_client.get("/api/v1/system/worker-probes/not-a-uuid")
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


async def test_probe_payload_size_limit(api_client):
    large_message = "x" * 300000
    resp = await api_client.post(
        "/api/v1/system/worker-probes",
        json={"job_kind": "system.worker_probe", "payload": {"message": large_message}},
    )
    assert resp.status_code == 413
    body = resp.json()
    assert body["error"]["code"] == "PAYLOAD_TOO_LARGE"


async def test_system_status_with_recent_heartbeat(api_client, test_engine):
    from sqlalchemy.ext.asyncio import AsyncSession

    sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as session:
        repo = HeartbeatRepository(session)
        await repo.upsert(str(uuid4()), "oryxenai-worker")
        await session.commit()

    resp = await api_client.get("/api/v1/system/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["worker"] == "ok"
