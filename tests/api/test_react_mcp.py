"""Exercise the official Streamable HTTP transport and capability errors."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from oryxenai.core.settings import get_settings
from oryxenai.delivery.contracts import VIEWER_URI, DeliveryError
from oryxenai.delivery.mcp import create_mcp


@pytest.mark.asyncio
async def test_transport_tools_app_resource_and_structured_expiry():
    settings = get_settings().model_copy(deep=True)
    settings.auth.primary_origin = "http://test"
    settings.auth.allowed_origins = ["http://test"]
    manifest = {"handoff_id": "fixture", "expires_at": "2030-01-01T00:00:00Z", "files": []}
    runtime = SimpleNamespace(
        settings=settings,
        project=AsyncMock(return_value=manifest),
        read_file=AsyncMock(return_value={"data": "", "next_cursor": None}),
    )
    app, server = create_mcp(runtime)
    headers = {
        "accept": "application/json, text/event-stream",
        "mcp-protocol-version": "2025-11-25",
    }
    async with (
        server.session_manager.run(),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test", headers=headers
        ) as client,
    ):

        async def rpc(method, params=None):
            response = await client.post(
                "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
            )
            assert response.status_code == 200, response.text
            result = response.json()
            assert "error" not in result, result
            return result["result"]

        listing = await rpc("tools/list")
        tools = {tool["name"]: tool for tool in listing["tools"]}
        assert set(tools) == {
            "get_react_project",
            "read_react_project_file",
            "show_react_portfolio",
            "read_preview_asset",
        }
        assert tools["read_preview_asset"]["_meta"]["ui"]["visibility"] == ["app"]
        assert tools["show_react_portfolio"]["_meta"]["ui"]["resourceUri"] == VIEWER_URI
        assert tools["get_react_project"]["annotations"]["readOnlyHint"]
        result = await rpc(
            "tools/call",
            {"name": "get_react_project", "arguments": {"share_link": "test-capability"}},
        )
        assert result["structuredContent"] == manifest
        shown = await rpc(
            "tools/call",
            {"name": "show_react_portfolio", "arguments": {"share_link": "test-capability"}},
        )
        assert shown["structuredContent"]["preview"] == "host_support_unconfirmed"
        assert shown["_meta"]["share_link"] == "test-capability"
        resource = await rpc("resources/read", {"uri": VIEWER_URI})
        assert resource["contents"][0]["mimeType"] == "text/html;profile=mcp-app"
        assert "<!doctype html>" in resource["contents"][0]["text"]
        runtime.project.side_effect = DeliveryError(
            "EXPIRED", "Ask the owner for a new link.", status_code=410
        )
        result = await rpc(
            "tools/call",
            {"name": "get_react_project", "arguments": {"share_link": "test-capability"}},
        )
        assert result["isError"] and result["structuredContent"]["error"]["code"] == "EXPIRED"
        denied = await client.post("/mcp", json={}, headers={"origin": "https://untrusted.example"})
        assert denied.status_code == 403


def test_feature_is_disabled_by_default():
    from oryxenai.main import create_app

    app = create_app(get_settings())
    assert app.state.delivery is None
    assert all(getattr(route, "path", "") != "/mcp" for route in app.routes)
