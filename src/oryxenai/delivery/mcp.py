"""Official MCP transport and MCP App; no independent source-download surface."""

from __future__ import annotations

import json
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent, ToolAnnotations

from oryxenai.delivery.contracts import VIEWER_URI, DeliveryError
from oryxenai.delivery.project import TEMPLATES, viewer_fingerprint
from oryxenai.delivery.service import DeliveryRuntime


def result(
    data: dict[str, Any], *, error: bool = False, meta: dict[str, Any] | None = None
) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(data))],
        structured_content=data,
        is_error=error,
        meta=meta,
    )


def create_mcp(runtime: DeliveryRuntime) -> tuple[Any, MCPServer[Any]]:
    from urllib.parse import urlsplit

    server: MCPServer[Any] = MCPServer(
        "OryxenAI React portfolios",
        version="1.0.0",
        instructions="Read an explicit OryxenAI share link. Import the complete React project, verify hashes, build it and preview it before enhancing it. No tool creates a portfolio or converts it using a model.",
    )
    annotations = ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
    )

    @server.tool(annotations=annotations, structured_output=False)
    async def get_react_project(share_link: str) -> CallToolResult:
        """Read the complete React project manifest for a temporary share link."""
        try:
            return result(await runtime.project(share_link))
        except DeliveryError as exc:
            return result({"error": exc.envelope()}, error=True)

    @server.tool(annotations=annotations, structured_output=False)
    async def read_react_project_file(
        share_link: str, path: str, cursor: int = 0
    ) -> CallToolResult:
        """Read a bounded binary-safe chunk; decode base64 outside model context."""
        try:
            return result(await runtime.read_file(share_link, path, cursor))
        except DeliveryError as exc:
            return result({"error": exc.envelope()}, error=True)

    @server.tool(
        annotations=annotations, structured_output=False, meta={"ui": {"resourceUri": VIEWER_URI}}
    )
    async def show_react_portfolio(share_link: str, ctx: Context[Any, Any]) -> CallToolResult:
        """Show the already-prepared React portfolio in an MCP Apps-capable host."""
        try:
            manifest = await runtime.project(share_link)
            if manifest.get("viewer_version") not in {None, viewer_fingerprint()}:
                raise DeliveryError(
                    "VIEWER_COMPATIBILITY_REQUIRED",
                    "This deployment cannot render the handoff's pinned viewer. The React project remains available for import.",
                    status_code=503,
                )
            # The UI is optional; never claim the host actually rendered it.
            capabilities = ctx.client_capabilities
            extensions = getattr(capabilities, "extensions", None) or {}
            ui_capability = extensions.get("io.modelcontextprotocol/ui", {})
            supported = "text/html;profile=mcp-app" in ui_capability.get("mimeTypes", [])
            return result(
                {
                    "handoff_id": manifest["handoff_id"],
                    "expires_at": manifest["expires_at"],
                    "preview": "available" if supported else "host_support_unconfirmed",
                    "message": "Open the attached React app if your host supports MCP Apps; otherwise import the project in a coding client.",
                },
                meta={"share_link": share_link, "manifest": manifest},
            )
        except DeliveryError as exc:
            return result({"error": exc.envelope()}, error=True)

    @server.tool(
        annotations=annotations, structured_output=False, meta={"ui": {"visibility": ["app"]}}
    )
    async def read_preview_asset(share_link: str, path: str, cursor: int = 0) -> CallToolResult:
        """App-only reader for public portfolio data and approved theme assets."""
        try:
            return result(await runtime.read_file(share_link, path, cursor, preview=True))
        except DeliveryError as exc:
            return result({"error": exc.envelope()}, error=True)

    @server.resource(
        VIEWER_URI,
        mime_type="text/html;profile=mcp-app",
        meta={
            "ui": {
                "prefersBorder": False,
                "csp": {"connectDomains": [], "resourceDomains": ["blob:", "data:"]},
            }
        },
    )
    def react_viewer() -> str:
        return (TEMPLATES / "viewer.html").read_text(encoding="utf-8")

    host = urlsplit(runtime.settings.auth.primary_origin).netloc
    transport = server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        max_request_body_size=65536,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[host, "localhost:*", "127.0.0.1:*"],
            allowed_origins=runtime.settings.auth.allowed_origins,
        ),
    )
    return transport, server
