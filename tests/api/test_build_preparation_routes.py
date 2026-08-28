from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport

from oryxenai.core.settings import Settings
from oryxenai.main import create_app
from tests.conftest import override_test_identity


def _fixture_input() -> dict[str, object]:
    return {
        "approved": {"visual_direction_hash": "visual-hash"},
        "source_ref": {"content_architect_content_hash": "content-hash"},
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
                        "content": {"heading": "A public heading"},
                        "internal_notes": "must not be emitted",
                    }
                ],
            }
        ],
        "public_content_manifest": {"approved": True},
    }


def _fixture_app(tmp_path: Path):
    settings = Settings()
    settings.auth.pipeline_mode = "attached"
    settings.build_preparation.fixture_enabled = True
    app = create_app(settings)
    override_test_identity(app, role="admin")
    app.state.settings.build_preparation.fixture_upload = False
    app.state.settings.build_preparation.fixture_output_dir = str(tmp_path)
    return app


def _detached_fixture_app(tmp_path: Path):
    settings = Settings()
    settings.auth.pipeline_mode = "detached"
    settings.build_preparation.fixture_enabled = True
    settings.build_preparation.fixture_upload = False
    settings.build_preparation.fixture_output_dir = str(tmp_path)
    return create_app(settings)


async def _completed_run(client: httpx.AsyncClient, run_id: str) -> dict[str, object]:
    for _ in range(40):
        response = await client.get(f"/api/v1/build-preparation/fixture/runs/{run_id}")
        assert response.status_code == 200
        result = response.json()
        if result["status"] != "running":
            return result
        await asyncio.sleep(0.05)
    raise AssertionError("Fixture run did not finish in time.")


@pytest.mark.asyncio
async def test_build_preparation_routes_are_exposed() -> None:
    settings = Settings()
    settings.build_preparation.fixture_enabled = True
    app = create_app(settings)
    assert "/api/v1/sessions/{session_id}/build-preparation" in app.openapi()["paths"]
    assert "/api/v1/sessions/{session_id}/build-preparation/start" in app.openapi()["paths"]
    assert "/api/v1/sessions/{session_id}/build-preparation/regenerate" in app.openapi()["paths"]
    assert "/api/v1/sessions/{session_id}/build-preparation/download" in app.openapi()["paths"]
    assert "/api/v1/build-preparation/fixture/run" in app.openapi()["paths"]


@pytest.mark.asyncio
async def test_fixture_run_is_detached_and_deterministic(tmp_path: Path) -> None:
    app = _fixture_app(tmp_path)
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/build-preparation/fixture/run",
            json={
                "output": _fixture_input(),
                "content_architect": _content_architect_input(),
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "phase_3"
    assert body["status"] == "needs_attention"
    assert body["model_calls"] == 0
    assert body["events"][-1]["event_id"] == "phase_3_complete"
    assert body["package"]["archive_sha256"]


@pytest.mark.asyncio
async def test_fixture_rejects_ambiguous_input(tmp_path: Path) -> None:
    app = _fixture_app(tmp_path)
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
async def test_fixture_accepts_optional_content_architect_json(tmp_path: Path) -> None:
    app = _fixture_app(tmp_path)
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
    assert "routes/home-4ea140588150/data.json" in {
        item["relative_path"] for item in body["materialization"]["files"]
    }
    route_data = json.loads(
        (
            Path(body["materialization"]["root_path"]) / "routes/home-4ea140588150/data.json"
        ).read_text(encoding="utf-8")
    )
    assert route_data["sections"][0]["content"]["heading"] == "A public heading"
    assert "internal_notes" not in route_data["sections"][0]


@pytest.mark.asyncio
async def test_fixture_rejects_ambiguous_content_architect_input(tmp_path: Path) -> None:
    app = _fixture_app(tmp_path)
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
async def test_fixture_rejects_invalid_content_architect_json(tmp_path: Path) -> None:
    app = _fixture_app(tmp_path)
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
async def test_two_harness_pages_are_available(tmp_path: Path) -> None:
    app = _fixture_app(tmp_path)
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        input_page = await client.get("/build-preparation-fixture")
        progress_page = await client.get("/build-preparation-fixture/progress")
    assert input_page.status_code == 200
    assert "Run diagnostic build" in input_page.text
    assert "Content Architect JSON" in input_page.text
    assert "content-architect-input" in input_page.text
    assert input_page.text.index("auth-client.js") < input_page.text.index("dev-auth-bootstrap.mjs")
    assert progress_page.status_code == 200
    assert "Diagnostics" in progress_page.text
    assert progress_page.text.index("auth-client.js") < progress_page.text.index(
        "dev-auth-bootstrap.mjs"
    )


@pytest.mark.asyncio
async def test_detached_fixture_bypasses_auth_and_sign_in_redirects(tmp_path: Path) -> None:
    app = _detached_fixture_app(tmp_path)
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        preflight = await client.get("/api/v1/build-preparation/fixture/preflight")
        input_page = await client.get("/build-preparation-fixture")
        progress_page = await client.get("/build-preparation-fixture/progress")
        sign_in = await client.get("/sign-in")

    assert preflight.status_code == 200
    assert 'name="oryxenai-pipeline-mode" content="detached"' in input_page.text
    assert 'name="oryxenai-pipeline-mode" content="detached"' in progress_page.text
    assert sign_in.status_code == 307
    assert sign_in.headers["location"] == "/app"


@pytest.mark.asyncio
async def test_fixture_run_api_persists_local_package_and_offers_download(tmp_path: Path) -> None:
    app = _fixture_app(tmp_path)
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        preflight = await client.get("/api/v1/build-preparation/fixture/preflight")
        assert preflight.status_code == 200
        assert preflight.json()["local"]["status"] == "ready"
        assert preflight.json()["r2"]["status"] == "not_requested"
        start = await client.post(
            "/api/v1/build-preparation/fixture/runs",
            json={
                "output": _fixture_input(),
                "content_architect": _content_architect_input(),
            },
        )
        assert start.status_code == 202
        run_id = start.json()["run_id"]
        result = await _completed_run(client, run_id)
        assert result["status"] == "needs_attention"
        assert result["summary"]["handoff_eligible"] is False
        assert result["summary"]["execution_gap_count"] > 0
        assert result["local_result"]["archive_available"] is True
        assert (
            Path(result["local_result"]["result_folder"])
            .resolve()
            .is_relative_to(tmp_path.resolve())
        )
        download = await client.get(result["download_url"])
    assert download.status_code == 200
    assert download.content.startswith(b"PK")
    assert (tmp_path / "build-preparation").is_dir()
