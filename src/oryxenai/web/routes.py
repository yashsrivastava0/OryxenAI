"""Web routes — serve the developer testing harness at /."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_STATIC_DIR = Path(__file__).resolve().parent / "static"

templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


def create_web_router() -> APIRouter:
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
            },
        )

    router.mount("/static", app=StaticFiles(directory=str(_STATIC_DIR)), name="static")
    return router
