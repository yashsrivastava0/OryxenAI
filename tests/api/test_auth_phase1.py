from __future__ import annotations

from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport

from oryxenai.api.dependencies import get_current_user
from oryxenai.auth.domain import AccountStatus, AuthRole, CurrentUser
from oryxenai.core.settings import Settings
from oryxenai.main import create_app


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        supabase_url="https://project.supabase.co",
        supabase_publishable_key="sb_publishable_test",
        supabase_secret_key="sb_secret_test",  # noqa: S106 - sentinel only
        admin_bootstrap_emails="admin1@example.com admin2@example.com",
        allowed_user_emails="user@example.com",
    )


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
async def test_all_phase1_pages_are_direct_html_and_shell_is_safe() -> None:
    settings = _settings()
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
        "/dev",
    )
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost:8000"
    ) as client:
        responses = [await client.get(path) for path in paths]

    assert all(response.status_code == 200 for response in responses)
    for response in responses[:-1]:
        assert "<html" in response.text
        assert response.headers["cache-control"] == "no-store"
        assert "Content-Security-Policy" in response.headers
        assert "admin1@example.com" not in response.text
        assert "sb_secret_test" not in response.text
    assert responses[-1].status_code == 200
    assert "Build your portfolio" in responses[-1].text


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
        dev_pages = [
            await client.get("/dev"),
            await client.get("/build-preparation-fixture"),
            await client.get("/code-generator-development"),
        ]

    assert all(response.status_code == 200 for response in responses)
    assert all(response.status_code == 404 for response in dev_pages)
    product = responses[6]
    assert "app-auth-bootstrap.mjs" in product.text
    assert "admin1@example.com" not in product.text
    assert "sb_secret_test" not in product.text
    assert product.headers["cache-control"] == "no-store"
    csp = product.headers["content-security-policy"]
    assert "connect-src 'self' https://project.supabase.co wss://project.supabase.co" in csp
    assert "*" not in csp
