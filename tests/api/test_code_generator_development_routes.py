from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

from oryxenai.core.settings import Settings
from oryxenai.main import create_app


@pytest.mark.asyncio
async def test_development_routes_are_absent_when_feature_is_disabled() -> None:
    settings = Settings()
    settings.code_generator_development.enabled = False
    app = create_app(settings)
    assert "/api/v1/development/code-generator/fixtures" not in app.openapi()["paths"]
    assert "/api/v1/development/code-generator/runs/{run_id}/acquire" not in app.openapi()["paths"]
    assert "/api/v1/development/code-generator/runs/{run_id}/generate" not in app.openapi()["paths"]
    assert "/api/v1/development/code-generator/runs/{run_id}/verify" not in app.openapi()["paths"]
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/api/v1/development/code-generator/fixtures")).status_code == 404
        assert (await client.get("/code-generator-development")).status_code == 404


@pytest.mark.asyncio
async def test_development_page_and_routes_are_mounted_when_enabled() -> None:
    settings = Settings()
    settings.code_generator_development.enabled = True
    app = create_app(settings)
    assert "/api/v1/development/code-generator/fixtures" in app.openapi()["paths"]
    assert "/api/v1/development/code-generator/readiness" in app.openapi()["paths"]
    assert "/api/v1/development/code-generator/provider-preflight" in app.openapi()["paths"]
    assert "/api/v1/development/code-generator/runs/{run_id}/acquire" in app.openapi()["paths"]
    assert "/api/v1/development/code-generator/runs/{run_id}/acquisition" in app.openapi()["paths"]
    assert "/api/v1/development/code-generator/runs/{run_id}/generate" in app.openapi()["paths"]
    assert "/api/v1/development/code-generator/runs/{run_id}/generation" in app.openapi()["paths"]
    assert "/api/v1/development/code-generator/runs/{run_id}/verify" in app.openapi()["paths"]
    assert "/api/v1/development/code-generator/runs/{run_id}/verification" in app.openapi()["paths"]
    assert "/api/v1/development/code-generator/runs/{run_id}/preview" in app.openapi()["paths"]
    assert "/api/v1/development/code-generator/runs/{run_id}/source-file" in app.openapi()["paths"]
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        readiness = await client.get("/api/v1/development/code-generator/readiness")
        response = await client.get("/code-generator-development")
    assert readiness.status_code == 200
    assert "can_start_latest" in readiness.json()
    assert "readiness_blockers" in readiness.json()
    assert response.status_code == 200
    assert "Generate portfolio" in response.text
    assert "Live preview" in response.text
    assert "Advanced / debug controls" in response.text
    assert "Auto-advance stages" in response.text
