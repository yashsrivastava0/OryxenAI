"""FastAPI application factory and entry point."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from oryxenai.agents.build_preparation.fixture_runs import FixtureRunManager
from oryxenai.api.errors import (
    AppError,
    app_error_handler,
    request_validation_error_handler,
    unhandled_error_handler,
)
from oryxenai.api.routes import create_api_router, create_health_router
from oryxenai.auth.jwt import SupabaseJwtVerifier
from oryxenai.auth.provider import SupabaseAuthProvider
from oryxenai.auth.web import create_auth_web_router
from oryxenai.core.lifecycle import dispose_engine
from oryxenai.core.logging import configure_logging, get_logger, new_request_id
from oryxenai.core.settings import Settings, get_settings
from oryxenai.db.session import get_engine, get_sessionmaker

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = get_logger("oryxenai.main")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign a correlation/request ID to every request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = request.headers.get("X-Request-ID") or new_request_id()
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration = (time.perf_counter() - start) * 1000
            logger.error(
                "%s %s -> 500 (%.1fms)",
                request.method,
                request.url.path,
                duration,
            )
            raise
        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add same-origin security headers to the developer harness without
    breaking the API or docs pages."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response


class AuthOriginMiddleware(BaseHTTPMiddleware):
    """Reject unexpected unsafe-method browser origins when an Origin exists."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if origin:
                allowed = request.app.state.settings.auth.allowed_origins
                if origin.lower() not in allowed:
                    request_id = getattr(request.state, "request_id", "")
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": {
                                "code": "ORIGIN_NOT_ALLOWED",
                                "message": "The request origin is not allowed.",
                                "requestId": request_id,
                            }
                        },
                    )
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown lifecycle."""
    settings: Settings = app.state.settings
    configure_logging(settings)
    logger.info(
        "starting %s (env=%s, host=%s, port=%d, dev_ui=%s)",
        settings.app.name,
        settings.app.env,
        settings.app.host,
        settings.app.port,
        settings.is_dev_ui_enabled,
    )
    logger.info("database engine initialised")
    try:
        yield
    finally:
        logger.info("shutting down %s", settings.app.name)
        await app.state.auth_verifier.aclose()
        await app.state.auth_provider.aclose()
        await app.state.fixture_run_manager.close()
        await dispose_engine(app.state.engine)
        logger.info("shutdown complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and return the FastAPI application."""
    s = settings or get_settings()
    s.validate_auth_configuration()
    configure_logging(s)

    app = FastAPI(
        title=s.app.name,
        version="0.1.0",
        docs_url="/docs" if s.is_dev_ui_enabled else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if s.is_dev_ui_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = s
    app.state.engine = get_engine(s)
    app.state.sessionmaker = get_sessionmaker(s)
    app.state.fixture_run_manager = FixtureRunManager(s)
    app.state.auth_verifier = SupabaseJwtVerifier(
        supabase_url=s.supabase_url,
        config=s.auth,
    )
    app.state.auth_provider = SupabaseAuthProvider(
        supabase_url=s.supabase_url,
        publishable_key=s.supabase_publishable_key.get_secret_value(),
        timeout_seconds=s.auth.http_timeout_seconds,
    )

    # Middleware (order: outer to inner; last added runs first).
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AuthOriginMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    # Exception handlers.
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(
        RequestValidationError,
        request_validation_error_handler,  # type: ignore[arg-type]
    )
    app.add_exception_handler(Exception, unhandled_error_handler)

    # Routers.
    app.include_router(create_health_router())
    app.include_router(create_api_router(s))
    app.include_router(create_auth_web_router())

    # The authenticated product shell is always directly reachable.  The
    # explicit developer harness is conditionally registered inside this
    # router and is absent when the dev feature is disabled.
    from oryxenai.web.routes import create_web_router

    app.include_router(create_web_router(s))

    return app


# Module-level app for uvicorn (ORYXENAI_APP=oryxenai.main:app)
app = create_app()
