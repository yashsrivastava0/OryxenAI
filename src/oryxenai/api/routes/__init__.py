"""API routes package."""

from fastapi import APIRouter

from oryxenai.api.routes import (
    agents,
    build_preparation,
    code_generator,
    code_generator_development,
    content_architect,
    discovery,
    health,
    model_profiles,
    runs,
    sessions,
    system,
    visual_design_director,
)


def create_api_router(settings: object | None = None) -> APIRouter:
    """Build the /api/v1 router with all sub-routers."""
    router = APIRouter(prefix="/api/v1")
    router.include_router(agents.router)
    router.include_router(sessions.router)
    router.include_router(runs.router)
    router.include_router(system.router)
    router.include_router(model_profiles.router)
    router.include_router(discovery.router)
    router.include_router(content_architect.router)
    router.include_router(visual_design_director.router)
    router.include_router(build_preparation.router)
    router.include_router(build_preparation.fixture_router)
    router.include_router(code_generator.router)
    if bool(getattr(getattr(settings, "code_generator_development", None), "enabled", False)):
        router.include_router(code_generator_development.router)
    return router


def create_health_router() -> APIRouter:
    """Build the /health router (no /api/v1 prefix)."""
    router = APIRouter(prefix="/health")
    router.include_router(health.router)
    return router
