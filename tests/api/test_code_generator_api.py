"""HTTP-level Code Generator flow: start -> worker -> preview grant -> served page."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import select

from oryxenai.agents.code_generator.agent import CodeGeneratorAgent
from oryxenai.agents.code_generator.dev.mock_client import ReferenceModelClient
from oryxenai.agents.content_architect.schemas import (
    ContentArchitectApproval,
    ContentArchitectState,
    ContentArchitectStatus,
    PortfolioPageContent,
)
from oryxenai.auth.models import AppUser
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.repositories.content_architect import ContentArchitectRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository
from oryxenai.jobs.handlers.code_generator import CodeGeneratorBuildHandler
from oryxenai.jobs.repository import JobRepository
from oryxenai.main import create_app
from tests.conftest import install_test_identity
from tests.unit.agents.code_generator.helpers import sample_content

pytestmark = pytest.mark.integration

_MODEL = ReferenceModelClient()


@pytest.fixture
async def client(test_engine, monkeypatch):
    app = create_app()
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from oryxenai.db.session import get_engine

    app.state.engine = get_engine(app.state.settings)
    app.state.sessionmaker = async_sessionmaker(app.state.engine, expire_on_commit=False)
    await install_test_identity(app, test_engine, role="user")
    monkeypatch.setattr(
        "oryxenai.jobs.handlers.code_generator._build_code_generator_agent",
        lambda **kwargs: CodeGeneratorAgent(_MODEL),
    )
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await app.state.engine.dispose()


async def _create_session(client: httpx.AsyncClient) -> str:
    response = await client.post("/api/v1/sessions", json={})
    assert response.status_code in (200, 201), response.text
    return str(response.json()["id"])


async def _approve_content(client: httpx.AsyncClient, session_id: str) -> None:
    app = client._transport.app  # type: ignore[attr-defined]
    async with app.state.sessionmaker() as db:
        repo = ContentArchitectRepository(db)
        session = await repo.get_session(UUID(session_id))
        assert session is not None
        state = ContentArchitectState(
            status=ContentArchitectStatus.APPROVED,
            page_content=PortfolioPageContent.model_validate(sample_content("01_strong_profile")),
            approved=ContentArchitectApproval(
                approved_at="2026-10-02T00:00:00+00:00", content_hash="h1"
            ),
        )
        await repo.save_content_architect_state(UUID(session_id), state, session.revision)
        await db.commit()


async def _run_build(client: httpx.AsyncClient, started: dict[str, Any]) -> dict[str, Any]:
    app = client._transport.app  # type: ignore[attr-defined]
    job_id = UUID(started["code_generator"]["in_flight"]["job_id"])
    async with app.state.sessionmaker() as db:
        claimed = await JobRepository(db).claim_batch(
            "test-worker", 60.0, 5, allowed_job_kinds=["code_generator.build"]
        )
        await db.commit()
        job = next(item for item in claimed if item.id == job_id)
        payload = {
            **job.payload,
            "attempt": job.attempt,
            "max_attempts": job.max_attempts,
            "job_id": str(job.id),
            "job_kind": job.job_kind,
            "lease_token": job.lease_token,
        }
    return await CodeGeneratorBuildHandler().execute(payload, "test-worker")


@pytest.mark.asyncio
async def test_state_is_a_200_not_started_before_anything_happens(client) -> None:
    session_id = await _create_session(client)
    response = await client.get(f"/api/v1/sessions/{session_id}/code-generator")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code_generator"]["status"] == "not_started"
    assert (body["versions"], body["chat"], body["jobs"]) == ([], [], [])
    assert body["session_id"] == session_id
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.asyncio
async def test_start_before_content_is_approved_is_a_clear_conflict(client) -> None:
    session_id = await _create_session(client)
    response = await client.post(f"/api/v1/sessions/{session_id}/code-generator/start")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CODE_GENERATOR_CONTENT_NOT_APPROVED"


@pytest.mark.asyncio
async def test_unbuildable_content_returns_the_exact_failure_with_422(client) -> None:
    session_id = await _create_session(client)
    await _approve_content(client, session_id)
    app = client._transport.app  # type: ignore[attr-defined]
    async with app.state.sessionmaker() as db:
        repo = ContentArchitectRepository(db)
        state = await repo.get_content_architect_state(UUID(session_id))
        state.page_content.hero.intro = "x" * 5000
        session = await repo.get_session(UUID(session_id))
        assert session is not None
        await repo.save_content_architect_state(UUID(session_id), state, session.revision)
        await db.commit()
    response = await client.post(f"/api/v1/sessions/{session_id}/code-generator/start")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "CODE_GENERATOR_CONTENT_NOT_BUILDABLE"
    assert error["details"]["failure"]["where"][0]["ref"] == "hero.intro"


@pytest.mark.asyncio
async def test_full_flow_start_build_preview_and_serve(client) -> None:
    session_id = await _create_session(client)
    await _approve_content(client, session_id)
    base = f"/api/v1/sessions/{session_id}/code-generator"

    started = await client.post(f"{base}/start")
    assert started.status_code == 202, started.text
    assert started.json()["code_generator"]["status"] == "build_running"
    assert (await client.get(f"{base}/preview-grant")).status_code == 409  # nothing to preview yet

    result = await _run_build(client, started.json())
    assert result["status"] == "succeeded"

    state = (await client.get(base)).json()
    assert state["code_generator"]["status"] == "ready"
    version_id = state["code_generator"]["active_version_id"]
    assert state["versions"][0]["version_number"] == 1
    assert state["chat"][-1]["body"].startswith("Your portfolio is ready")

    grant = await client.get(f"{base}/preview-grant")
    assert grant.status_code == 200, grant.text
    assert grant.headers["cache-control"] == "no-store"
    url = grant.json()["url"]
    assert url.startswith("/preview/g/") and grant.json()["version_id"] == version_id

    page = await client.get(url)
    assert page.status_code == 200
    assert page.headers["content-type"] == "text/html; charset=utf-8"
    assert "sandbox" in page.headers["content-security-policy"]
    assert page.headers["referrer-policy"] == "no-referrer"
    assert sample_content("01_strong_profile")["hero"]["name"] in page.text
    css = await client.get(url.replace("index.html", "styles.css"))
    assert css.status_code == 200 and css.headers["content-type"].startswith("text/css")
    # The preview needs no Authorization header: the grant is the address.
    assert "authorization" not in {key.lower() for key in page.request.headers}

    detail = await client.get(f"{base}/versions/{version_id}", params={"include_html": "true"})
    assert detail.status_code == 200
    assert detail.json()["index_html"] == page.text
    assert detail.json()["receipt"]["validation"]["ok"] is True
    plain = await client.get(f"{base}/versions/{version_id}")
    assert "index_html" not in plain.json()


@pytest.mark.asyncio
async def test_a_failed_build_is_visible_with_the_exact_failure(client) -> None:
    name = sample_content("01_strong_profile")["hero"]["name"]
    previous = _MODEL.mutate
    _MODEL.mutate = lambda body: body.replace(name, name + "!", 1)
    try:
        session_id = await _create_session(client)
        await _approve_content(client, session_id)
        base = f"/api/v1/sessions/{session_id}/code-generator"
        started = await client.post(f"{base}/start")
        result = await _run_build(client, started.json())
    finally:
        _MODEL.mutate = previous
    assert result["status"] == "failed"
    state = (await client.get(base)).json()
    assert state["code_generator"]["status"] == "needs_attention"
    error = state["code_generator"]["last_error"]
    assert (error["code"], error["stage"]) == ("PAGE_COPY_MISMATCH", "validate")
    assert error["where"][0]["ref"].startswith("hero")
    assert state["versions"][0]["status"] == "failed"
    assert (await client.get(f"{base}/preview-grant")).status_code == 409

    # "Try again" is the same explicit start and makes a fresh build.
    again = await client.post(f"{base}/start")
    assert again.status_code == 202
    assert again.json()["code_generator"]["in_flight"]["origin"] == "retry"


@pytest.mark.asyncio
async def test_stop_endpoint_cancels_the_build(client) -> None:
    session_id = await _create_session(client)
    await _approve_content(client, session_id)
    base = f"/api/v1/sessions/{session_id}/code-generator"
    await client.post(f"{base}/start")
    stopped = await client.post(f"{base}/stop")
    assert stopped.status_code == 200
    assert stopped.json()["code_generator"]["last_error"]["code"] == "JOB_CANCELLED"
    # Stopping again is harmless.
    assert (await client.post(f"{base}/stop")).status_code == 200


@pytest.mark.asyncio
async def test_other_peoples_sessions_and_versions_are_not_reachable(client, test_engine) -> None:
    app = client._transport.app  # type: ignore[attr-defined]
    other_id = uuid4()
    async with app.state.sessionmaker() as db:
        db.add(
            AppUser(
                id=other_id,
                supabase_user_id=uuid4(),
                primary_email="other@example.com",
                username="other-user",
                role="user",
                status="active",
                onboarding_completed_at=datetime.now(UTC),
            )
        )
        await db.flush()
        other_session = await PortfolioSessionRepository(db).create_owned(other_id, "Other")
        other_session_id = other_session.id
        await db.commit()

    base = f"/api/v1/sessions/{other_session_id}/code-generator"
    for method, path in (
        ("GET", ""),
        ("POST", "/start"),
        ("POST", "/stop"),
        ("GET", "/preview-grant"),
    ):
        response = await client.request(method, base + path)
        assert response.status_code == 404, (method, path, response.text)
    assert (await client.get(f"{base}/versions/{uuid4()}")).status_code == 404
    assert (await client.get("/api/v1/sessions/not-a-uuid/code-generator")).status_code in {
        400,
        404,
        422,
    }


@pytest.mark.asyncio
async def test_grants_are_scoped_to_their_own_session_and_version(client) -> None:
    session_id = await _create_session(client)
    await _approve_content(client, session_id)
    base = f"/api/v1/sessions/{session_id}/code-generator"
    started = await client.post(f"{base}/start")
    await _run_build(client, started.json())
    version_id = (await client.get(base)).json()["code_generator"]["active_version_id"]

    assert (
        await client.get(f"{base}/preview-grant", params={"version_id": str(uuid4())})
    ).status_code == 404
    assert (
        await client.get(f"{base}/preview-grant", params={"version_id": "nope"})
    ).status_code in {400, 422}
    ok = await client.get(f"{base}/preview-grant", params={"version_id": version_id})
    assert ok.status_code == 200

    # A tampered token never serves anything.
    token = ok.json()["url"].split("/")[3]
    forged = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    assert (await client.get(f"/preview/g/{forged}/index.html")).status_code == 404


@pytest.mark.asyncio
async def test_run_history_never_exposes_the_page_content(client) -> None:
    session_id = await _create_session(client)
    await _approve_content(client, session_id)
    base = f"/api/v1/sessions/{session_id}/code-generator"
    started = await client.post(f"{base}/start")
    await _run_build(client, started.json())
    runs = await client.get(f"/api/v1/sessions/{session_id}/runs")
    assert runs.status_code == 200, runs.text
    generator_runs = [run for run in runs.json() if run.get("agent_key") == "code_generator"]
    assert generator_runs, runs.text
    for run in generator_runs:
        assert "page_content" not in (run.get("input_payload") or {})
        assert "index_html" not in (run.get("output_payload") or {})
    app = client._transport.app  # type: ignore[attr-defined]
    async with app.state.sessionmaker() as db:
        rows = (
            (await db.execute(select(AgentRun).where(AgentRun.agent_key == "code_generator")))
            .scalars()
            .all()
        )
        assert rows and "page_content" in rows[0].input_payload  # kept on the row itself
