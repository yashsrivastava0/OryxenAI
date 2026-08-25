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
from oryxenai.auth import api as auth_api
from oryxenai.auth.admin import api as admin_api


def create_api_router(settings: object | None = None) -> APIRouter:
    """Build the /api/v1 router with explicit environment route policy."""
    router = APIRouter(prefix="/api/v1")
    dev_ui_enabled = bool(getattr(settings, "is_dev_ui_enabled", False))
    fixture_enabled = bool(
        getattr(getattr(settings, "build_preparation", None), "fixture_enabled", False)
    )
    code_generator_dev_enabled = bool(
        getattr(getattr(settings, "code_generator_development", None), "enabled", False)
    )

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
    router.include_router(discovery.router)
    router.include_router(content_architect.router)
    router.include_router(visual_design_director.router)
    router.include_router(build_preparation.router)
    if dev_ui_enabled and fixture_enabled:
        fixture_router = (
            build_preparation.detached_fixture_router
            if getattr(getattr(settings, "auth", None), "pipeline_mode", "attached") == "detached"
            else build_preparation.fixture_router
        )
        router.include_router(fixture_router)
    router.include_router(code_generator.router)
    if dev_ui_enabled and code_generator_dev_enabled:
        router.include_router(code_generator_development.router)
    return router


def create_health_router() -> APIRouter:
    """Build the /health router (no /api/v1 prefix)."""
    router = APIRouter(prefix="/health")
    router.include_router(health.router)
    return router
