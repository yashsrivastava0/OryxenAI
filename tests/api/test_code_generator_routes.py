from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from httpx import ASGITransport

from oryxenai.api.dependencies import get_code_generator_service
from oryxenai.main import create_app


class _Service:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    async def get_state(self, session_id):
        self.calls.append(("get", str(session_id), ""))
        return _payload(session_id)

    async def start(self, session_id, *, idempotency_key: str, model_profile: str = ""):
        self.calls.append(("start", str(session_id), idempotency_key))
        return _payload(session_id, status="queued")

    async def regenerate(self, session_id, *, idempotency_key: str, model_profile: str = ""):
        self.calls.append(("regenerate", str(session_id), idempotency_key))
        return _payload(session_id, status="queued")


def _payload(session_id, *, status: str = "not_started"):
    return {
        "session_id": str(session_id),
        "session_revision": 1,
        "code_generator": {"status": status},
        "jobs": [],
    }


@pytest.mark.asyncio
async def test_production_code_generator_routes_are_exposed_and_forward_idempotency() -> None:
    app = create_app()
    service = _Service()
    app.dependency_overrides[get_code_generator_service] = lambda: service
    session_id = uuid4()
    paths = app.openapi()["paths"]

    assert "/api/v1/sessions/{session_id}/code-generator" in paths
    assert "/api/v1/sessions/{session_id}/code-generator/start" in paths
    assert "/api/v1/sessions/{session_id}/code-generator/regenerate" in paths

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        start = await client.post(
            f"/api/v1/sessions/{session_id}/code-generator/start",
            headers={"Idempotency-Key": "first-attempt"},
            json={},
        )
        state = await client.get(f"/api/v1/sessions/{session_id}/code-generator")
        regenerate = await client.post(
            f"/api/v1/sessions/{session_id}/code-generator/regenerate",
            headers={"Idempotency-Key": "second-attempt"},
            json={},
        )
        override = await client.post(
            f"/api/v1/sessions/{session_id}/code-generator/start",
            json={"model_profile": "request-controlled-profile"},
        )

    assert start.status_code == 202
    assert state.status_code == 200
    assert regenerate.status_code == 202
    assert override.status_code == 422
    assert service.calls == [
        ("start", str(session_id), "first-attempt"),
        ("get", str(session_id), ""),
        ("regenerate", str(session_id), "second-attempt"),
    ]
