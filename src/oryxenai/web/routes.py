"""Web routes — serve the developer testing harness at /."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from oryxenai.agents.shared.model_router import ModelRouter

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_STATIC_DIR = Path(__file__).resolve().parent / "static"

templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


def _asset_version(filename: str) -> str:
    """Return a cheap dev-friendly cache key for a checked-in static asset."""
    try:
        return str((_STATIC_DIR / filename).stat().st_mtime_ns)
    except OSError:
        return "0"


def create_web_router(settings_override: Any | None = None) -> APIRouter:
    """Return a router serving the developer testing harness and static assets."""
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> Any:
        settings = request.app.state.settings
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "app_name": settings.app.name,
                "dev_ui": settings.is_dev_ui_enabled,
                "model_profiles": [
                    option.as_dict() for option in ModelRouter(settings.models).public_options()
                ],
                "app_js_version": _asset_version("app.js"),
                "app_css_version": _asset_version("app.css"),
            },
        )

    @router.get("/build-preparation-fixture", response_class=HTMLResponse)
    async def build_preparation_fixture(request: Request) -> Any:
        settings = request.app.state.settings
        return templates.TemplateResponse(
            request=request,
            name="build_preparation_fixture.html",
            context={
                "app_name": settings.app.name,
                "fixture_enabled": settings.build_preparation.fixture_enabled,
            },
        )

    @router.get("/build-preparation-fixture/progress", response_class=HTMLResponse)
    async def build_preparation_fixture_progress(request: Request) -> Any:
        settings = request.app.state.settings
        return templates.TemplateResponse(
            request=request,
            name="build_preparation_progress.html",
            context={
                "app_name": settings.app.name,
                "fixture_enabled": settings.build_preparation.fixture_enabled,
            },
        )

    if bool(
        getattr(getattr(settings_override, "code_generator_development", None), "enabled", False)
    ):

        @router.get("/code-generator-development", response_class=HTMLResponse)
        async def code_generator_development(request: Request) -> Any:
            settings = request.app.state.settings
            return templates.TemplateResponse(
                request=request,
                name="code_generator_development.html",
                context={
                    "app_name": settings.app.name,
                    "css_version": _asset_version("code-generator-development.css"),
                    "js_version": _asset_version("code-generator-development.js"),
                },
            )

    router.mount("/static", app=StaticFiles(directory=str(_STATIC_DIR)), name="static")
    return router
