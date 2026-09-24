"""API routes package."""

from fastapi import APIRouter

from oryxenai.api.routes import (
    agents,
    client_diagnostics,
    content_architect,
    discovery,
    health,
    model_profiles,
    model_usage,
    runs,
    sessions,
    system,
)
from oryxenai.auth import api as auth_api
from oryxenai.auth.admin import api as admin_api


def create_api_router(settings: object | None = None) -> APIRouter:
    """Build the /api/v1 router with explicit environment route policy."""
    router = APIRouter(prefix="/api/v1")
    dev_ui_enabled = bool(getattr(settings, "is_dev_ui_enabled", False))
    router.include_router(auth_api.router)
    router.include_router(admin_api.router)
    router.include_router(agents.router)
    router.include_router(sessions.router)
    router.include_router(runs.router)
    # Mock execution is an explicit development-only administrator harness.
    if dev_ui_enabled:
        router.include_router(runs.mock_router)
    router.include_router(system.router)
    router.include_router(model_profiles.router)
    router.include_router(model_profiles.pipeline_router)
    router.include_router(model_usage.router)
    router.include_router(discovery.router)
    router.include_router(content_architect.router)
    # Client diagnostics are a separate local-only switch. Keep the route
    # available when the developer UI is not mounted so API-backed local
    # product shells can still export a trace; deployment overlays disable it
    # explicitly through [client_diagnostics].
    if bool(getattr(getattr(settings, "client_diagnostics", None), "enabled", False)):
        router.include_router(client_diagnostics.router)
    return router


def create_health_router() -> APIRouter:
    """Build the /health router (no /api/v1 prefix)."""
    router = APIRouter(prefix="/health")
    router.include_router(health.router)
    return router
