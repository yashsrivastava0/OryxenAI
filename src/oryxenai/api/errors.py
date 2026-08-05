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
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from oryxenai.core.logging import get_request_id


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
    body: dict[str, Any] = {"code": code, "message": message, "requestId": rid}
    if details:
        body["details"] = details
    return {"error": body}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    details = dict(exc.details)
    if exc.retryable:
        details["retryable"] = True
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_envelope(exc.code, exc.message, details),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    from oryxenai.core.logging import get_logger

    logger = get_logger("oryxenai.api.errors")
    logger.error("unhandled error: %s: %s", type(exc).__name__, exc)
    return JSONResponse(
        status_code=500,
        content=_build_envelope(
            "INTERNAL_ERROR",
            "An unexpected error occurred.",
        ),
    )
