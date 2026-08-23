"""Direct HTML shells for the Phase 1 auth controller."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

_ROOT = Path(__file__).resolve().parent
_TEMPLATE_DIR = _ROOT / "templates"
_STATIC_DIR = _ROOT / "static"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


def _asset_version(filename: str) -> str:
    try:
        return str((_STATIC_DIR / filename).stat().st_mtime_ns)
    except OSError:
        return "0"


def _auth_csp(supabase_url: str) -> str:
    parsed = urlsplit(supabase_url.rstrip("/"))
    sources = ["'self'"]
    if parsed.scheme in {"http", "https"} and parsed.hostname:
        origin = f"{parsed.scheme}://{parsed.netloc}"
        sources.extend([origin, f"wss://{parsed.netloc}"])
    return "; ".join(
        [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self'",
            "img-src 'self'",
            "font-src 'self'",
            f"connect-src {' '.join(sources)}",
            "object-src 'none'",
            "base-uri 'none'",
            "form-action 'self' https://accounts.google.com",
            "frame-ancestors 'none'",
        ]
    )


def create_auth_web_router() -> APIRouter:
    router = APIRouter()

    async def render_shell(request: Request, page: str) -> HTMLResponse:
        settings = request.app.state.settings
        response = templates.TemplateResponse(
            request=request,
            name="auth_shell.html",
            context={
                "app_name": settings.app.name,
                "page": page,
                "auth_config": settings.auth_public_config,
                "auth_css_version": _asset_version("auth.css"),
                "auth_client_version": _asset_version("auth-client.js"),
                "auth_controller_version": _asset_version("auth-controller.mjs"),
            },
        )
        response.headers["Content-Security-Policy"] = _auth_csp(settings.supabase_url)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @router.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> Any:
        return await render_shell(request, "controller")

    @router.get("/sign-in", response_class=HTMLResponse)
    async def sign_in(request: Request) -> Any:
        return await render_shell(request, "sign-in")

    @router.get("/auth/callback", response_class=HTMLResponse)
    async def callback(request: Request) -> Any:
        return await render_shell(request, "callback")

    @router.get("/access-not-approved", response_class=HTMLResponse)
    async def access_not_approved(request: Request) -> Any:
        return await render_shell(request, "access-not-approved")

    @router.get("/account-unavailable", response_class=HTMLResponse)
    async def account_unavailable(request: Request) -> Any:
        return await render_shell(request, "account-unavailable")

    @router.get("/onboarding", response_class=HTMLResponse)
    async def onboarding(request: Request) -> Any:
        return await render_shell(request, "onboarding")

    @router.get("/app", response_class=HTMLResponse)
    async def app_page(request: Request) -> Any:
        return await render_shell(request, "app")

    @router.get("/admin", response_class=HTMLResponse)
    async def admin(request: Request) -> Any:
        return await render_shell(request, "admin")

    router.mount("/auth-static", app=StaticFiles(directory=str(_STATIC_DIR)), name="auth-static")
    return router
