"""Consistent structured error responses.

All API errors return:
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message.",
    "requestId": "correlation-id"
  }
}

Never returns raw stack traces to HTTP clients.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import DBAPIError

from oryxenai.core.logging import get_request_id, redact_sensitive_text


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str = ""


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class AppError(Exception):
    """Base application error with a code, message, and HTTP status."""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details or {}
        self.retryable = retryable
        super().__init__(message)


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404


class SessionNotFoundError(NotFoundError):
    code = "SESSION_NOT_FOUND"

    def __init__(self, session_id: str) -> None:
        super().__init__(
            "Portfolio session was not found.",
            details={"session_id": session_id},
        )


class AgentNotFoundError(AppError):
    code = "AGENT_NOT_FOUND"
    status_code = 400

    def __init__(self, key: str) -> None:
        super().__init__(
            f"Agent '{key}' is not registered.",
            details={"key": key},
        )


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 400


class ConflictError(AppError):
    code = "CONFLICT"
    status_code = 409


class PipelineRestartCleanupError(AppError):
    code = "PIPELINE_RESTART_CLEANUP_FAILED"
    status_code = 503

    def __init__(self) -> None:
        super().__init__(
            "The pipeline could not be fully cleared. Retry restart to finish cleanup.",
            retryable=True,
        )


class PayloadTooLargeError(AppError):
    code = "PAYLOAD_TOO_LARGE"
    status_code = 413


class DiscoveryError(AppError):
    """Safe API error for the Discovery workflow."""

    status_code = 409

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 409,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(
            message,
            code=code,
            status_code=status_code,
            details=details,
            retryable=retryable,
        )


def _build_envelope(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rid = get_request_id() or ""
    body: dict[str, Any] = {
        "code": code,
        "message": redact_sensitive_text(message),
        "requestId": rid,
    }
    if details:
        body["details"] = _redact_detail_value(details)
    return {"error": body}


def _redact_detail_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, dict):
        return {str(key): _redact_detail_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_detail_value(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_detail_value(item) for item in value]
    return value


def _exception_nodes(exc: BaseException) -> list[BaseException]:
    nodes: list[BaseException] = []
    pending = [exc]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        marker = id(current)
        if marker in seen:
            continue
        seen.add(marker)
        nodes.append(current)
        if isinstance(current, BaseExceptionGroup):
            pending.extend(current.exceptions)
        if current.__cause__ is not None:
            pending.append(current.__cause__)
        if current.__context__ is not None:
            pending.append(current.__context__)
    return nodes


def _database_failure(exc: BaseException) -> tuple[str, str] | None:
    """Return a safe user-facing classification for database failures."""

    nodes = _exception_nodes(exc)
    for node in nodes:
        name = type(node).__name__.casefold()
        message = str(node).casefold()
        if name == "invalidpassworderror" or "password authentication failed" in message:
            return (
                "DATABASE_CREDENTIALS_INVALID",
                "The local PostgreSQL role/password was rejected. Align the role with "
                "POSTGRES_PASSWORD, then restart the API and worker.",
            )
    if any(isinstance(node, DBAPIError) for node in nodes) or any(
        type(node).__module__.casefold().startswith("asyncpg") for node in nodes
    ):
        return (
            "DATABASE_UNAVAILABLE",
            "The local PostgreSQL database is unavailable. Check the native database "
            "configuration, then restart the API and worker.",
        )
    return None


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    details = dict(exc.details)
    if exc.retryable:
        details["retryable"] = True
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_envelope(exc.code, exc.message, details),
    )


async def request_validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Keep framework validation failures in the same redacted envelope."""
    fields: list[dict[str, Any]] = []
    for error in exc.errors():
        location = error.get("loc", ())
        fields.append(
            {
                "location": [str(part) for part in location],
                "message": str(error.get("msg", "Invalid request.")),
                "type": str(error.get("type", "validation_error")),
            }
        )
    return JSONResponse(
        status_code=422,
        content=_build_envelope(
            "VALIDATION_ERROR",
            "The request could not be validated.",
            {"fields": fields},
        ),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    from oryxenai.core.logging import get_logger

    logger = get_logger("oryxenai.api.errors")
    logger.error("unhandled error: %s: %s", type(exc).__name__, redact_sensitive_text(str(exc)))
    database_failure = _database_failure(exc)
    if database_failure is not None:
        code, message = database_failure
        return JSONResponse(
            status_code=503,
            content=_build_envelope(code, message),
        )
    return JSONResponse(
        status_code=500,
        content=_build_envelope(
            "INTERNAL_ERROR",
            "An unexpected error occurred.",
        ),
    )
