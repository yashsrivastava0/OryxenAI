"""Integration API tests for the admin-only pipeline reset endpoint."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.models.background_job import BackgroundJob
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.session import get_engine
from oryxenai.main import create_app
from tests.conftest import install_test_identity

pytestmark = pytest.mark.integration


@pytest.fixture
async def admin_client(test_engine: Any) -> Any:
    """Create a test client authenticated as an administrator."""
    app = create_app()
    settings = app.state.settings
    app.state.engine = get_engine(settings)
    app.state.sessionmaker = async_sessionmaker(app.state.engine, expire_on_commit=False)
    await install_test_identity(app, test_engine, role="admin")

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, app


@pytest.fixture
async def user_client(test_engine: Any) -> Any:
    """Create a test client authenticated as a normal non-admin user."""
    app = create_app()
    settings = app.state.settings
    app.state.engine = get_engine(settings)
    app.state.sessionmaker = async_sessionmaker(app.state.engine, expire_on_commit=False)
    await install_test_identity(app, test_engine, role="user")

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, app


async def test_admin_can_reset_pipeline(admin_client: Any) -> None:
    """An admin can reset a pipeline session back to zero, purging jobs, runs, and memory."""
    client, app = admin_client

    # 1. Admin creates session
    create_resp = await client.post("/api/v1/sessions", json={"name": "Admin Portfolio"})
    assert create_resp.status_code == 201
    sid = create_resp.json()["id"]
    session_uuid = UUID(sid)

    # 2. Populate session with dummy pipeline state, job, and agent run
    async with app.state.sessionmaker() as db:
        session = await db.get(PortfolioSession, session_uuid)
        assert session is not None
        session.current_state = {
            "discovery": {
                "status": "approved",
                "intake": {"message": "Original resume text"},
                "brief": {"approved": True, "title": "Portfolio Brief"},
            },
            "content_architect": {
                "status": "approved",
                "plan": {"routes": [{"id": "home"}]},
            },
        }
        session.revision = 3

        # Add an associated background job
        job = BackgroundJob(
            portfolio_session_id=session_uuid,
            job_kind="discovery.understand_and_question",
            status="completed",
            payload={"portfolio_session_id": sid},
        )
        db.add(job)

        # Add an associated agent run
        run = AgentRun(
            portfolio_session_id=session_uuid,
            agent_key="discovery",
            status="completed",
            input_payload={"message": "Original resume"},
            output_payload={"questions": []},
            state_before={},
            state_after={},
        )
        db.add(run)
        await db.commit()

    # 3. Call the admin reset endpoint
    reset_resp = await client.post(f"/api/v1/sessions/{sid}/reset")
    assert reset_resp.status_code == 200
    reset_body = reset_resp.json()
    assert reset_body["id"] == sid
    assert reset_body["status"] == "active"
    assert reset_body["current_state"] == {}
    assert reset_body["revision"] > 3

    # 4. Verify DB: jobs and runs are deleted, session is reset to empty
    async with app.state.sessionmaker() as db:
        job_count = await db.scalar(
            select(func.count())
            .select_from(BackgroundJob)
            .where(BackgroundJob.portfolio_session_id == session_uuid)
        )
        assert job_count == 0

        run_count = await db.scalar(
            select(func.count())
            .select_from(AgentRun)
            .where(AgentRun.portfolio_session_id == session_uuid)
        )
        assert run_count == 0

        reloaded = await db.get(PortfolioSession, session_uuid)
        assert reloaded is not None
        assert reloaded.current_state == {}
        assert reloaded.status == "active"

    # 5. Verify Discovery state returns not_started ("available")
    disc_resp = await client.get(f"/api/v1/sessions/{sid}/discovery")
    assert disc_resp.status_code == 200
    assert disc_resp.json()["discovery"]["status"] == "not_started"


async def test_normal_user_forbidden_from_resetting(user_client: Any) -> None:
    """A normal user receives 403 Forbidden when attempting to reset a pipeline."""
    client, _app = user_client
    create_resp = await client.post("/api/v1/sessions", json={"name": "User Portfolio"})
    assert create_resp.status_code == 201
    sid = create_resp.json()["id"]

    reset_resp = await client.post(f"/api/v1/sessions/{sid}/reset")
    assert reset_resp.status_code == 403
    assert reset_resp.json()["error"]["code"] == "ADMIN_REQUIRED"


async def test_unauthenticated_cannot_reset_pipeline() -> None:
    """An unauthenticated request receives 401 Unauthorized."""
    app = create_app()
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        fake_id = str(uuid4())
        resp = await client.post(f"/api/v1/sessions/{fake_id}/reset")
        assert resp.status_code == 401


async def test_admin_reset_nonexistent_session_returns_404(admin_client: Any) -> None:
    """Resetting a non-existent session returns 404 Not Found."""
    client, _app = admin_client
    non_existent = str(uuid4())
    resp = await client.post(f"/api/v1/sessions/{non_existent}/reset")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "SESSION_NOT_FOUND"
