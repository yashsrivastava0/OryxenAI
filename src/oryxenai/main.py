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
from starlette.types import ASGIApp

from oryxenai.agents.shared.model_runtime import close_model_runtime, get_model_runtime
from oryxenai.api.errors import (
    AppError,
    app_error_handler,
    request_validation_error_handler,
    unhandled_error_handler,
)
from oryxenai.api.routes import create_api_router, create_health_router
from oryxenai.auth.admin.provider import SupabaseAdminProvider
from oryxenai.auth.jwt import SupabaseJwtVerifier
from oryxenai.auth.provider import SupabaseAuthProvider
from oryxenai.auth.web import create_auth_web_router
from oryxenai.core.lifecycle import dispose_engine
from oryxenai.core.logging import configure_logging, get_logger, new_request_id
from oryxenai.core.settings import Settings, get_settings
from oryxenai.db.session import get_engine, get_sessionmaker
from oryxenai.storage.archive import create_archive_storage

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
        if request.url.path.startswith("/api/") or request.url.path in {"/app", "/"}:
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Minimal in-memory per-IP fixed-window limit for auth and API paths.

    Single Compose `app` container, single uvicorn process (no --workers),
    so in-memory state needs no cross-process coordination. Requires uvicorn
    to be started with --proxy-headers/--forwarded-allow-ips behind Caddy,
    otherwise every request would appear to come from Caddy's own IP.
    """

    _WINDOW_SECONDS = 60.0
    _LIMITS: tuple[tuple[str, int], ...] = (("/auth/", 30), ("/api/", 120))
    _MAX_TRACKED_KEYS = 10_000

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._buckets: dict[tuple[str, str], tuple[int, float]] = {}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        prefix: str | None = None
        limit: int = 0
        for path_prefix, path_limit in self._LIMITS:
            if request.url.path.startswith(path_prefix):
                prefix, limit = path_prefix, path_limit
                break
        if prefix is not None:
            client_ip = request.client.host if request.client else "unknown"
            now = time.monotonic()
            key = (client_ip, prefix)
            count, window_start = self._buckets.get(key, (0, now))
            if now - window_start >= self._WINDOW_SECONDS:
                count, window_start = 0, now
            count += 1
            if len(self._buckets) >= self._MAX_TRACKED_KEYS and key not in self._buckets:
                self._buckets = {
                    k: v for k, v in self._buckets.items() if now - v[1] < self._WINDOW_SECONDS
                }
            self._buckets[key] = (count, window_start)
            if count > limit:
                retry_after = max(1, int(self._WINDOW_SECONDS - (now - window_start)))
                request_id = getattr(request.state, "request_id", "")
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMITED",
                            "message": "Too many requests.",
                            "requestId": request_id,
                        }
                    },
                    headers={"Retry-After": str(retry_after)},
                )
        return await call_next(request)


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
        await app.state.auth_admin_provider.aclose()
        await close_model_runtime(settings.models)
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
    app.state.model_runtime = get_model_runtime(s.models, app.state.sessionmaker)
    app.state.auth_verifier = SupabaseJwtVerifier(
        supabase_url=s.supabase_url,
        config=s.auth,
    )
    app.state.auth_provider = SupabaseAuthProvider(
        supabase_url=s.supabase_url,
        publishable_key=s.supabase_publishable_key.get_secret_value(),
        timeout_seconds=s.auth.http_timeout_seconds,
    )
    app.state.auth_admin_provider = SupabaseAdminProvider(
        supabase_url=s.supabase_url,
        secret_key=s.supabase_secret_key.get_secret_value(),
        timeout_seconds=s.auth.http_timeout_seconds,
    )
    # Account cleanup can remove older stored outputs without exposing an
    # output-serving or output-writing runtime.
    app.state.archive_storage = create_archive_storage(s)

    # Middleware (order: outer to inner; last added runs first).
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AuthOriginMiddleware)
    app.add_middleware(RateLimitMiddleware)
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
