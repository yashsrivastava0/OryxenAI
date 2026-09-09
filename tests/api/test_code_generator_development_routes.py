from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

from oryxenai.core.settings import Settings
from oryxenai.main import create_app
from tests.conftest import override_test_identity


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
    settings.auth.development_harness_mode = "detached"
    app = create_app(settings)
    override_test_identity(app, role="admin")
    assert "/api/v1/development/code-generator/fixtures" in app.openapi()["paths"]
    assert "/api/v1/development/code-generator/readiness" in app.openapi()["paths"]
    assert "/api/v1/development/code-generator/provider-preflight" in app.openapi()["paths"]
    assert "/api/v1/development/code-generator/toolchain-preflight" in app.openapi()["paths"]
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
    assert "Auto-advance" in response.text
    assert "auth-client.js" not in response.text
    assert "dev-auth-bootstrap.mjs" not in response.text
    assert "code-generator-development-detached-bootstrap.mjs" in response.text
    assert "Detached development" in response.text
    assert "generation-report.md" in response.text


@pytest.mark.asyncio
async def test_attached_development_shell_retains_future_auth_boundary() -> None:
    settings = Settings()
    settings.code_generator_development.enabled = True
    settings.auth.development_harness_mode = "attached"
    app = create_app(settings)
    override_test_identity(app, role="admin")
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/code-generator-development")
    assert response.status_code == 200
    assert "auth-client.js" in response.text
    assert "dev-auth-bootstrap.mjs" in response.text
    assert "code-generator-development-detached-bootstrap.mjs" not in response.text


@pytest.mark.asyncio
async def test_candidate_preview_serves_a_needs_attention_runs_own_export(tmp_path) -> None:
    """A needs_attention run's own already-built dist/ was previously
    invisible to a human -- the run-state API had nothing pointing at it and
    the dev harness only ever showed a promoted (ready) preview. This route
    serves that dist/ directly, unauthenticated (this whole harness has no
    auth boundary in detached mode already), for the frontend's unverified-
    candidate fallback."""
    settings = Settings()
    settings.code_generator_development.enabled = True
    settings.auth.development_harness_mode = "detached"
    settings.code_generator_verification.export_root = str(tmp_path)
    folder = "16-43-07-09-2026-0ffd6cec"
    dist_dir = tmp_path / folder / "dist"
    dist_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text(
        "<html><head><title>t</title></head><body>hi</body></html>", encoding="utf-8"
    )
    (dist_dir / "assets").mkdir()
    (dist_dir / "assets" / "app.js").write_text("console.log('hi')", encoding="utf-8")
    app = create_app(settings)
    override_test_identity(app, role="admin")
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        index = await client.get(f"/dev/code-generator-development/candidate-preview/{folder}/")
        asset = await client.get(
            f"/dev/code-generator-development/candidate-preview/{folder}/assets/app.js"
        )
        traversal = await client.get(
            "/dev/code-generator-development/candidate-preview/"
            f"{folder}/assets/../../../../etc/passwd"
        )
        missing_folder = await client.get(
            "/dev/code-generator-development/candidate-preview/does-not-exist/"
        )
    assert index.status_code == 200
    assert "oryxenai-preview-base" in index.text
    assert f"/candidate-preview/{folder}/" in index.text
    assert asset.status_code == 200
    assert asset.text == "console.log('hi')"
    assert traversal.status_code == 404
    assert missing_folder.status_code == 404
