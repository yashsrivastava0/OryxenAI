from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport

from oryxenai.main import create_app


def _fixture_input() -> dict[str, object]:
    return {
        "pages": [
            {"route_id": "home", "path": "/", "publication_status": "approved", "scenes": []}
        ],
        "asset_briefs": [],
        "resource_candidates": [],
    }


def _content_architect_input() -> dict[str, object]:
    return {
        "route_plan": [{"route_id": "home", "path": "/", "title": "Home"}],
        "page_content_packs": [
            {
                "route_id": "home",
                "sections": [
                    {
                        "section_id": "intro",
                        "heading": "A public heading",
                        "internal_notes": "must not be emitted",
                    }
                ],
            }
        ],
        "public_content_manifest": {"approved": True},
    }


@pytest.mark.asyncio
async def test_build_preparation_routes_are_exposed() -> None:
    app = create_app()
    app.state.settings.build_preparation.fixture_enabled = True
    assert "/api/v1/sessions/{session_id}/build-preparation" in app.openapi()["paths"]
    assert "/api/v1/sessions/{session_id}/build-preparation/start" in app.openapi()["paths"]
    assert "/api/v1/sessions/{session_id}/build-preparation/regenerate" in app.openapi()["paths"]
    assert "/api/v1/build-preparation/fixture/run" in app.openapi()["paths"]


@pytest.mark.asyncio
async def test_fixture_run_is_detached_and_deterministic() -> None:
    app = create_app()
    app.state.settings.build_preparation.fixture_enabled = True
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/build-preparation/fixture/run",
            json={"output": _fixture_input()},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "phase_3"
    assert body["status"] == "ready"
    assert body["model_calls"] == 0
    assert body["events"][-1]["event_id"] == "phase_3_complete"
    assert body["package"]["archive_sha256"]


@pytest.mark.asyncio
async def test_fixture_rejects_ambiguous_input() -> None:
    app = create_app()
    app.state.settings.build_preparation.fixture_enabled = True
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/build-preparation/fixture/run",
            json={"output": _fixture_input(), "output_json": "{}"},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FIXTURE_INPUT_AMBIGUOUS"


@pytest.mark.asyncio
async def test_fixture_accepts_optional_content_architect_json() -> None:
    app = create_app()
    app.state.settings.build_preparation.fixture_enabled = True
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/build-preparation/fixture/run",
            json={
                "output": _fixture_input(),
                "content_architect_json": json.dumps(_content_architect_input()),
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert [route["route_id"] for route in body["routes"]] == ["home"]
    assert "routes/home/data.json" in {
        item["relative_path"] for item in body["materialization"]["files"]
    }
    route_data = json.loads(
        (Path(body["materialization"]["root_path"]) / "routes/home/data.json").read_text(
            encoding="utf-8"
        )
    )
    assert route_data["sections"][0]["heading"] == "A public heading"
    assert "internal_notes" not in route_data["sections"][0]


@pytest.mark.asyncio
async def test_fixture_rejects_ambiguous_content_architect_input() -> None:
    app = create_app()
    app.state.settings.build_preparation.fixture_enabled = True
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/build-preparation/fixture/run",
            json={
                "output": _fixture_input(),
                "content_architect": _content_architect_input(),
                "content_architect_json": "{}",
            },
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FIXTURE_INPUT_AMBIGUOUS"


@pytest.mark.asyncio
async def test_fixture_rejects_invalid_content_architect_json() -> None:
    app = create_app()
    app.state.settings.build_preparation.fixture_enabled = True
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/build-preparation/fixture/run",
            json={"content_architect_json": "not-json"},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FIXTURE_INPUT_INVALID"


@pytest.mark.asyncio
async def test_two_harness_pages_are_available() -> None:
    app = create_app()
    app.state.settings.build_preparation.fixture_enabled = True
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        input_page = await client.get("/build-preparation-fixture")
        progress_page = await client.get("/build-preparation-fixture/progress")
    assert input_page.status_code == 200
    assert "Run Phase 3" in input_page.text
    assert "Content Architect JSON" in input_page.text
    assert "content-architect-input" in input_page.text
    assert progress_page.status_code == 200
    assert "Full output" in progress_page.text
