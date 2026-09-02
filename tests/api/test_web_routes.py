"""/app serves the Preact studio only when enabled and actually built, and
/dev never serves it regardless — see docs/Frontend/05 §19 Phase 1 and
docs/Frontend/06-cross-model-review-and-decisions.md §3.3.
"""

from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

from oryxenai.main import create_app
import oryxenai.web.routes as web_routes


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
        lambda: {"script": "/static/product/assets/main-test.js", "styles": ["/static/product/assets/main-test.css"]},
    )
    resp = await c.get("/app")
    assert resp.status_code == 200
    assert 'id="product-root"' in resp.text
    assert 'meta name="oryxenai-product-entry" content="/static/product/assets/main-test.js"' in resp.text
    assert 'id="chat-card"' not in resp.text


async def test_app_falls_back_to_legacy_ui_when_bundle_not_built(client, monkeypatch):
    c, app = client
    app.state.settings.app.enable_product_preact_shell = True
    monkeypatch.setattr(web_routes, "_resolve_product_entry", lambda: None)
    resp = await c.get("/app")
    assert resp.status_code == 200
    assert 'id="chat-card"' in resp.text
    assert 'id="product-root"' not in resp.text


async def test_app_falls_back_to_legacy_ui_when_flag_disabled(client, monkeypatch):
    c, app = client
    app.state.settings.app.enable_product_preact_shell = False
    monkeypatch.setattr(
        web_routes,
        "_resolve_product_entry",
        lambda: {"script": "/static/product/assets/main-test.js", "styles": []},
    )
    resp = await c.get("/app")
    assert resp.status_code == 200
    assert 'id="chat-card"' in resp.text


async def test_dev_never_serves_the_preact_shell(client, monkeypatch):
    c, app = client
    app.state.settings.app.enable_product_preact_shell = True
    monkeypatch.setattr(
        web_routes,
        "_resolve_product_entry",
        lambda: {"script": "/static/product/assets/main-test.js", "styles": []},
    )
    resp = await c.get("/dev")
    assert resp.status_code == 200
    assert 'id="chat-card"' in resp.text
    assert 'id="product-root"' not in resp.text
