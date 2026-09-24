"""Product shell and static assets."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from oryxenai.auth.web import auth_csp

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_AUTH_STATIC_DIR = Path(__file__).resolve().parents[1] / "auth" / "static"
_SHELL_ASSETS = frozenset(
    {"app-auth-bootstrap.mjs", "auth-bootstrap.css", "pipeline-bootstrap.mjs"}
)

templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


def _asset_version(filename: str) -> str:
    try:
        return str((_STATIC_DIR / filename).stat().st_mtime_ns)
    except OSError:
        return "0"


def _auth_asset_version(filename: str) -> str:
    try:
        return str((_AUTH_STATIC_DIR / filename).stat().st_mtime_ns)
    except OSError:
        return "0"


def _resolve_product_entry() -> dict[str, Any] | None:
    """Resolve the built Preact bundle's hashed entry script and CSS."""
    manifest_path = _STATIC_DIR / "product" / ".vite" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    entry = manifest.get("src/main.tsx")
    if not isinstance(entry, dict) or "file" not in entry:
        return None
    return {
        "script": f"/static/product/{entry['file']}",
        "styles": [f"/static/product/{css}" for css in entry.get("css", [])],
    }


def _resolve_shell_asset(requested: str) -> Path | None:
    parts = Path(requested).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return None
    if parts[0] == "product":
        relative = Path(*parts)
    elif len(parts) == 1 and parts[0] in _SHELL_ASSETS:
        relative = Path(parts[0])
    else:
        return None
    path = (_STATIC_DIR / relative).resolve()
    if not path.is_relative_to(_STATIC_DIR.resolve()) or not path.is_file():
        return None
    return path


def _shell_context(settings: Any) -> dict[str, object]:
    # The public shell contains no model profiles, identity, session state, or
    # provider credentials. Safe account-scoped metadata is fetched after auth.
    return {
        "app_name": settings.app.name,
        "model_profiles": [],
        "auth_config": settings.auth_public_config,
        "pipeline_mode": settings.auth.pipeline_mode,
        "tokens_css_version": _auth_asset_version("tokens.css"),
        "motion_css_version": _auth_asset_version("motion.css"),
        "living_draft_mark_css_version": _auth_asset_version("living-draft-mark.css"),
        "auth_css_version": _auth_asset_version("auth.css"),
        "auth_client_version": _auth_asset_version("auth-client.js"),
        "auth_bootstrap_css_version": _asset_version("auth-bootstrap.css"),
        "auth_runtime_version": _asset_version("auth-runtime.mjs"),
        "app_auth_bootstrap_version": _asset_version("app-auth-bootstrap.mjs"),
        "pipeline_bootstrap_version": _asset_version("pipeline-bootstrap.mjs"),
    }


def _set_shell_headers(response: Response, settings: Any) -> Response:
    response.headers["Content-Security-Policy"] = auth_csp(settings.supabase_url)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


def create_web_router(settings_override: Any | None = None) -> APIRouter:
    """Return the authenticated product shell and static assets."""
    router = APIRouter()

    @router.get("/app", response_class=HTMLResponse)
    async def product_app(request: Request) -> Any:
        settings = request.app.state.settings
        if not settings.is_product_preact_shell_enabled:
            response = Response(
                "The product frontend is disabled.",
                status_code=503,
                media_type="text/plain",
            )
        else:
            product_entry = _resolve_product_entry()
            if product_entry is None:
                response = Response(
                    "The product frontend bundle is unavailable. Build the frontend before starting the app.",
                    status_code=503,
                    media_type="text/plain",
                )
            else:
                response = templates.TemplateResponse(
                    request=request,
                    name="product_shell.html",
                    context={**_shell_context(settings), "product_entry": product_entry},
                )
        return _set_shell_headers(response, settings)

    @router.get("/static/{requested:path}")
    async def shell_asset(requested: str) -> Any:
        path = _resolve_shell_asset(requested)
        if path is None:
            return Response("Not found", status_code=404, media_type="text/plain")
        return FileResponse(
            path,
            media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            headers={"Cache-Control": "public, max-age=300"},
        )

    return router
