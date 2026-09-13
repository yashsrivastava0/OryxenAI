"""The product shell is Preact-only; the retired legacy /dev shell is absent."""

from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

import oryxenai.web.routes as web_routes
from oryxenai.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, app


async def test_app_serves_preact_shell_when_enabled_and_built(client, monkeypatch):
    c, app = client
    app.state.settings.app.enable_product_preact_shell = True
    monkeypatch.setattr(
        web_routes,
        "_resolve_product_entry",
        lambda: {
            "script": "/static/product/assets/main-test.js",
            "styles": ["/static/product/assets/main-test.css"],
        },
    )
    resp = await c.get("/app")
    assert resp.status_code == 200
    assert 'id="product-root"' in resp.text
    assert (
        'meta name="oryxenai-product-entry" content="/static/product/assets/main-test.js"'
        in resp.text
    )
    assert "auth-bootstrap.css" in resp.text
    assert 'id="chat-card"' not in resp.text


async def test_app_returns_a_clear_error_when_bundle_is_not_built(client, monkeypatch):
    c, app = client
    app.state.settings.app.enable_product_preact_shell = True
    monkeypatch.setattr(web_routes, "_resolve_product_entry", lambda: None)
    resp = await c.get("/app")
    assert resp.status_code == 503
    assert "product frontend bundle is unavailable" in resp.text


async def test_app_returns_a_clear_error_when_preact_shell_is_disabled(client, monkeypatch):
    c, app = client
    app.state.settings.app.enable_product_preact_shell = False
    monkeypatch.setattr(
        web_routes,
        "_resolve_product_entry",
        lambda: {"script": "/static/product/assets/main-test.js", "styles": []},
    )
    resp = await c.get("/app")
    assert resp.status_code == 503
    assert "product frontend is disabled" in resp.text


async def test_legacy_dev_shell_is_removed(client, monkeypatch):
    c, app = client
    app.state.settings.app.enable_product_preact_shell = True
    monkeypatch.setattr(
        web_routes,
        "_resolve_product_entry",
        lambda: {"script": "/static/product/assets/main-test.js", "styles": []},
    )
    resp = await c.get("/dev")
    assert resp.status_code == 404
