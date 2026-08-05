"""API routes package."""

from fastapi import APIRouter

from oryxenai.api.routes import agents, discovery, health, runs, sessions, system


def create_api_router() -> APIRouter:
    """Build the /api/v1 router with all sub-routers."""
    router = APIRouter(prefix="/api/v1")
    router.include_router(agents.router)
    router.include_router(sessions.router)
    router.include_router(runs.router)
    router.include_router(system.router)
    router.include_router(discovery.router)
    return router


def create_health_router() -> APIRouter:
    """Build the /health router (no /api/v1 prefix)."""
    router = APIRouter(prefix="/health")
    router.include_router(health.router)
    return router
