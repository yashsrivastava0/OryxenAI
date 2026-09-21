from __future__ import annotations

from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport

import oryxenai.web.routes as web_routes
from oryxenai.api.dependencies import get_current_user
from oryxenai.auth.domain import AccountStatus, AuthRole, CurrentUser
from oryxenai.core.settings import Settings
from oryxenai.main import create_app


def _settings() -> Settings:
    settings = Settings(
        _env_file=None,
        supabase_url="https://project.supabase.co",
        supabase_publishable_key="sb_publishable_test",
        supabase_secret_key="sb_secret_test",  # noqa: S106 - sentinel only
        admin_bootstrap_emails="admin1@example.com admin2@example.com",
        allowed_user_emails="user@example.com",
    )
    settings.auth.pipeline_mode = "attached"
    # Keep this helper independent of the integration overlay's restricted
    # allowlist policy; these shell tests assert the local base policy.
    settings.auth.admission_mode = "open"
    return settings


@pytest.mark.asyncio
async def test_me_requires_one_bearer_token_and_uses_structured_errors() -> None:
    app = create_app(_settings())
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost:8000"
    ) as client:
        response = await client.get("/api/v1/me")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "AUTH_REQUIRED"
    assert "requestId" in body["error"]
    assert "token" not in response.text.lower()


@pytest.mark.asyncio
async def test_all_phase1_pages_are_direct_html_and_shell_is_safe(monkeypatch) -> None:
    settings = _settings()
    monkeypatch.setattr(
        web_routes,
        "_resolve_product_entry",
        lambda: {"script": "/static/product/assets/main-test.js", "styles": []},
    )
    app = create_app(settings)
    paths = (
        "/",
        "/sign-in",
        "/auth/callback",
        "/access-not-approved",
        "/account-unavailable",
        "/onboarding",
        "/app",
        "/admin",
    )
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost:8000"
    ) as client:
        responses = [await client.get(path) for path in paths]
        dev_response = await client.get("/dev")

    assert all(response.status_code == 200 for response in responses)
    for response in responses:
        assert "<html" in response.text
        assert response.headers["cache-control"] == "no-store"
        assert "Content-Security-Policy" in response.headers
        assert response.headers["referrer-policy"] == "no-referrer"
        assert "camera=()" in response.headers["permissions-policy"]
        assert "admin1@example.com" not in response.text
        assert "sb_secret_test" not in response.text
        assert "access_token" not in response.text
        assert "refresh_token" not in response.text
        assert "Bearer " not in response.text
    assert dev_response.status_code == 404


@pytest.mark.asyncio
async def test_me_projection_contains_only_safe_local_fields() -> None:
    app = create_app(_settings())
    user = CurrentUser(
        id=UUID("22222222-2222-4222-8222-222222222222"),
        supabase_user_id=UUID("11111111-1111-4111-8111-111111111111"),
        username=None,
        role=AuthRole.USER,
        status=AccountStatus.ACTIVE,
    )

    async def fake_current_user() -> CurrentUser:
        return user

    app.dependency_overrides[get_current_user] = fake_current_user
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://localhost:8000"
        ) as client:
            response = await client.get("/api/v1/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": "22222222-2222-4222-8222-222222222222",
        "username": None,
        "role": "user",
        "status": "active",
        "onboarding_required": True,
        "admin_available": False,
    }


@pytest.mark.asyncio
async def test_unexpected_unsafe_origin_is_rejected_with_request_id() -> None:
    app = create_app(_settings())
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost:8000"
    ) as client:
        response = await client.put(
            "/api/v1/me/username",
            headers={"Origin": "https://evil.example"},
            json={"username": "safe-name"},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORIGIN_NOT_ALLOWED"
    assert response.json()["error"]["requestId"]


@pytest.mark.asyncio
async def test_product_shell_is_directly_refreshable_and_dev_routes_are_absent_in_production() -> (
    None
):
    settings = _settings()
    settings.app.enable_dev_ui = False
    settings.build_preparation.fixture_enabled = False
    settings.code_generator_development.enabled = False
    app = create_app(settings)
    paths = (
        "/",
        "/sign-in",
        "/auth/callback",
        "/access-not-approved",
        "/account-unavailable",
        "/onboarding",
        "/app",
        "/admin",
    )
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost:8000"
    ) as client:
        responses = [await client.get(path) for path in paths]
        auth_client = await client.get("/auth-static/auth-client.js")
        dev_pages = [
            await client.get("/dev"),
            await client.get("/build-preparation-fixture"),
            await client.get("/code-generator-development"),
        ]

    assert all(response.status_code == 200 for response in responses)
    assert auth_client.status_code == 200
    assert "OryxenAISupabaseClient" in auth_client.text
    assert all(response.status_code == 404 for response in dev_pages)
    sign_in = responses[1]
    assert sign_in.text.index("auth-client.js") < sign_in.text.index("auth-page.mjs")
    assert 'class="sign-in-showcase"' in sign_in.text
    assert sign_in.text.count('class="outcome-card"') == 3
    assert 'id="outcome-preview-dialog"' in sign_in.text
    assert sign_in.text.count("data-outcome-preview=") == 3
    assert sign_in.text.count('class="sample-site-nav') == 3
    assert sign_in.text.count("data-preview-screen=") == 12
    assert sign_in.text.count("data-preview-route=") == 15
    assert "Software developer" in sign_in.text
    assert "Business developer" in sign_in.text
    assert "Creative director" in sign_in.text
    assert "Example generated from a test brief." in sign_in.text
    assert "sign-in-showcase.mjs" in sign_in.text
    product = responses[6]
    assert "auth-client.js" in product.text
    assert "app-auth-bootstrap.mjs" in product.text
    assert product.text.index("auth-client.js") < product.text.index("app-auth-bootstrap.mjs")
    assert "/static/auth.css" not in product.text
    assert 'oryxenai-admission-mode" content="open"' in product.text
    assert "admin1@example.com" not in product.text
    assert "sb_secret_test" not in product.text
    assert product.headers["cache-control"] == "no-store"
    assert product.headers["referrer-policy"] == "no-referrer"
    csp = product.headers["content-security-policy"]
    assert "connect-src 'self' https://project.supabase.co wss://project.supabase.co" in csp
    assert "*" not in csp
