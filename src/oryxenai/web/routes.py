"""Direct product and explicitly development-only web shells."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from oryxenai.auth.web import auth_csp

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_AUTH_STATIC_DIR = Path(__file__).resolve().parents[1] / "auth" / "static"

templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


def _asset_version(filename: str) -> str:
    """Return a cheap dev-friendly cache key for a checked-in static asset."""
    try:
        return str((_STATIC_DIR / filename).stat().st_mtime_ns)
    except OSError:
        return "0"


def _auth_asset_version(filename: str) -> str:
    try:
        return str((_AUTH_STATIC_DIR / filename).stat().st_mtime_ns)
    except OSError:
        return "0"


def _shell_context(settings: Any) -> dict[str, object]:
    # No model profiles, identity, session state, or provider credentials are
    # rendered into a public HTML shell.  The authenticated bootstrap may
    # request safe profile metadata only after an administrator check.
    return {
        "app_name": settings.app.name,
        "dev_ui": settings.is_dev_ui_enabled,
        "model_profiles": [],
        "auth_config": settings.auth_public_config,
        "app_js_version": _asset_version("app.js"),
        "auth_css_version": _auth_asset_version("auth.css"),
        "auth_client_version": _auth_asset_version("auth-client.js"),
        "app_css_version": _asset_version("app.css"),
        "auth_runtime_version": _asset_version("auth-runtime.mjs"),
        "app_auth_bootstrap_version": _asset_version("app-auth-bootstrap.mjs"),
        "dev_auth_bootstrap_version": _asset_version("dev-auth-bootstrap.mjs"),
    }


def _set_shell_headers(response: HTMLResponse, settings: Any) -> HTMLResponse:
    response.headers["Content-Security-Policy"] = auth_csp(settings.supabase_url)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    return response


def create_web_router(settings_override: Any | None = None) -> APIRouter:
    """Return the always-mounted product shell plus optional dev routes."""
    router = APIRouter()
    dev_enabled = bool(getattr(settings_override, "is_dev_ui_enabled", False))
    fixture_enabled = bool(
        getattr(getattr(settings_override, "build_preparation", None), "fixture_enabled", False)
    )
    code_generator_dev_enabled = bool(
        getattr(getattr(settings_override, "code_generator_development", None), "enabled", False)
    )

    @router.get("/app", response_class=HTMLResponse)
    async def product_app(request: Request) -> Any:
        settings = request.app.state.settings
        response = templates.TemplateResponse(
            request=request,
            # Phase 3 uses the existing authenticated Discovery workspace as
            # the single product frontend.  The bootstrap hides developer
            # controls for normal users and supplies the server-bound
            # entitlement projection before this module is initialized.
            name="index.html",
            context=_shell_context(settings),
        )
        return _set_shell_headers(response, settings)

    if dev_enabled:

        @router.get("/dev", response_class=HTMLResponse)
        async def developer_index(request: Request) -> Any:
            settings = request.app.state.settings
            response = templates.TemplateResponse(
                request=request,
                name="index.html",
                context=_shell_context(settings),
            )
            return _set_shell_headers(response, settings)

    if dev_enabled and fixture_enabled:

        @router.get("/dev/build-preparation-fixture", response_class=HTMLResponse)
        @router.get("/build-preparation-fixture", response_class=HTMLResponse)
        async def build_preparation_fixture(request: Request) -> Any:
            settings = request.app.state.settings
            response = templates.TemplateResponse(
                request=request,
                name="build_preparation_fixture.html",
                context={
                    "app_name": settings.app.name,
                    "auth_config": settings.auth_public_config,
                    "dev_auth_bootstrap_version": _asset_version("dev-auth-bootstrap.mjs"),
                    "fixture_enabled": True,
                },
            )
            return _set_shell_headers(response, settings)

        @router.get("/dev/build-preparation-fixture/progress", response_class=HTMLResponse)
        @router.get("/build-preparation-fixture/progress", response_class=HTMLResponse)
        async def build_preparation_fixture_progress(request: Request) -> Any:
            settings = request.app.state.settings
            response = templates.TemplateResponse(
                request=request,
                name="build_preparation_progress.html",
                context={
                    "app_name": settings.app.name,
                    "auth_config": settings.auth_public_config,
                    "dev_auth_bootstrap_version": _asset_version("dev-auth-bootstrap.mjs"),
                    "fixture_enabled": True,
                },
            )
            return _set_shell_headers(response, settings)

    if dev_enabled and code_generator_dev_enabled:

        @router.get("/dev/code-generator-development", response_class=HTMLResponse)
        @router.get("/code-generator-development", response_class=HTMLResponse)
        async def code_generator_development(request: Request) -> Any:
            settings = request.app.state.settings
            response = templates.TemplateResponse(
                request=request,
                name="code_generator_development.html",
                context={
                    "app_name": settings.app.name,
                    "auth_config": settings.auth_public_config,
                    "dev_auth_bootstrap_version": _asset_version("dev-auth-bootstrap.mjs"),
                    "css_version": _asset_version("code-generator-development.css"),
                    "js_version": _asset_version("code-generator-development.js"),
                },
            )
            return _set_shell_headers(response, settings)

    router.mount("/static", app=StaticFiles(directory=str(_STATIC_DIR)), name="static")
    return router
