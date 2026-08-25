"""API coverage for the temporary anonymous main pipeline."""

from __future__ import annotations

import hashlib
from uuid import UUID, uuid4

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.models.background_job import BackgroundJob
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.main import create_app
from oryxenai.storage.artifacts import ArtifactReference, MemoryArtifactStore

pytestmark = pytest.mark.integration


@pytest.fixture
async def detached_client(test_engine):
    app = create_app()
    app.state.settings.auth.pipeline_mode = "detached"
    app.state.sessionmaker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    app.state.artifact_store = MemoryArtifactStore()
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client, app


async def test_detached_pipeline_does_not_require_auth(detached_client):
    client, _app = detached_client
    created = await client.post("/api/v1/sessions", json={})
    assert created.status_code == 201
    body = created.json()
    assert body["session_mode"] == "detached"

    state = await client.get(f"/api/v1/sessions/{body['id']}/discovery")
    assert state.status_code == 200
    assert state.json()["discovery"]["status"] == "not_started"


async def test_detached_model_profiles_are_safe_and_preflighted(detached_client):
    client, app = detached_client
    calls: list[tuple[list[str], str]] = []

    class FakeRuntime:
        async def preflight(self, engines, override):
            calls.append((engines, override))
            return {
                "status": "ready",
                "private_context_sent": False,
                "profiles": [{"profile_id": "safe-profile"}],
            }

    app.state.model_runtime = FakeRuntime()
    listing = await client.get("/api/v1/pipeline/model-profiles")
    assert listing.status_code == 200
    assert listing.json()["options"]
    assert "provider" not in listing.text.casefold()
    assert "model" not in {
        key.casefold() for option in listing.json()["options"] for key in option if key != "id"
    }
    assert "api_key" not in listing.text.casefold()
    assert "base_url" not in listing.text.casefold()

    response = await client.post(
        "/api/v1/pipeline/model-profiles/preflight",
        json={"model_profile": ""},
    )
    assert response.status_code == 200
    assert response.json()["private_context_sent"] is False
    assert calls == [
        (
            [
                "discovery",
                "content_architect",
                "visual_design_director",
                "build_preparation",
            ],
            "",
        )
    ]


async def test_pipeline_model_profiles_fail_closed_in_attached_mode(detached_client):
    client, app = detached_client
    app.state.settings.auth.pipeline_mode = "attached"

    listing = await client.get("/api/v1/pipeline/model-profiles")
    preflight = await client.post(
        "/api/v1/pipeline/model-profiles/preflight", json={"model_profile": ""}
    )

    assert listing.status_code == 404
    assert preflight.status_code == 404


async def test_restart_deletes_durable_rows_and_recreates_empty_session(detached_client):
    client, app = detached_client
    created = await client.post("/api/v1/sessions", json={"name": "Reset me"})
    old_id = UUID(created.json()["id"])
    replacement_id = uuid4()

    reference = ArtifactReference(
        provider="memory",
        key=f"temporary/{old_id}/source/run.zip",
        sha256=hashlib.sha256(b"").hexdigest(),
        size_bytes=0,
        expires_at="2099-01-01T00:00:00+00:00",
    )
    await app.state.artifact_store.put_verified(
        key=reference.key,
        data=b"",
        sha256=reference.sha256,
        expires_at=reference.expires_at,
    )

    async with app.state.sessionmaker() as db:
        session = await db.get(PortfolioSession, old_id)
        assert session is not None
        session.current_state = {
            "discovery": {"status": "needs_attention", "latest_error": {"message": "old error"}},
            "build_preparation": {"package": {"artifact": reference.model_dump(mode="json")}},
        }
        db.add(
            AgentRun(
                portfolio_session_id=old_id,
                agent_key="discovery",
                status="failed",
                input_payload={},
                state_before={},
            )
        )
        db.add(
            BackgroundJob(
                job_kind="discovery.understand_and_question",
                portfolio_session_id=old_id,
                payload={"portfolio_session_id": str(old_id)},
                status="queued",
            )
        )
        await db.commit()

    restarted = await client.post(
        f"/api/v1/sessions/{old_id}/restart",
        json={"replacement_session_id": str(replacement_id)},
    )
    assert restarted.status_code == 200
    result = restarted.json()
    assert result["id"] == str(replacement_id)
    assert result["revision"] == 0
    assert result["current_state"] == {}
    assert result["session_mode"] == "detached"

    old_response = await client.get(f"/api/v1/sessions/{old_id}")
    assert old_response.status_code == 404
    assert await app.state.artifact_store.head(reference) is None

    async with app.state.sessionmaker() as db:
        assert await db.get(PortfolioSession, old_id) is None
        assert await db.get(PortfolioSession, replacement_id) is not None
        assert (
            await db.scalar(
                select(func.count())
                .select_from(AgentRun)
                .where(AgentRun.portfolio_session_id == old_id)
            )
        ) == 0
        assert (
            await db.scalar(
                select(func.count())
                .select_from(BackgroundJob)
                .where(BackgroundJob.portfolio_session_id == old_id)
            )
        ) == 0


async def test_restart_is_retryable_with_the_same_replacement_id(detached_client):
    client, _app = detached_client
    created = await client.post("/api/v1/sessions", json={})
    old_id = created.json()["id"]
    replacement_id = str(uuid4())

    first = await client.post(
        f"/api/v1/sessions/{old_id}/restart",
        json={"replacement_session_id": replacement_id},
    )
    second = await client.post(
        f"/api/v1/sessions/{old_id}/restart",
        json={"replacement_session_id": replacement_id},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] == replacement_id
