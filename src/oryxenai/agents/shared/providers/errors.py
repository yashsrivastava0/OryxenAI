"""Provider-agnostic error types for model client adapters.

Every provider adapter raises only these types (or their subclasses).
Callers never need to know which provider generated the error.
"""

from __future__ import annotations

from typing import Any


class ProviderError(Exception):
    """Base error for all provider-level failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "PROVIDER_ERROR",
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.details = details or {}


class ProviderAuthError(ProviderError):
    """Authentication failed — key invalid, expired, or revoked."""

    def __init__(self, message: str = "Provider authentication failed") -> None:
        super().__init__(message, code="PROVIDER_AUTH_ERROR", retryable=False)


class ProviderRateLimitError(ProviderError):
    """Rate limited — caller should back off and retry."""

    def __init__(
        self,
        message: str = "Provider rate limit exceeded",
        retry_after_seconds: float | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if retry_after_seconds is not None:
            details["retry_after_seconds"] = retry_after_seconds
        super().__init__(
            message,
            code="PROVIDER_RATE_LIMIT_ERROR",
            retryable=True,
            details=details,
        )


class ProviderTimeoutError(ProviderError):
    """Request timed out."""

    def __init__(self, message: str = "Provider request timed out") -> None:
        super().__init__(message, code="PROVIDER_TIMEOUT_ERROR", retryable=True)


class ProviderConnectionError(ProviderError):
    """Network-level connection failure."""

    def __init__(self, message: str = "Provider connection failed") -> None:
        super().__init__(message, code="PROVIDER_CONNECTION_ERROR", retryable=True)


class ProviderServerError(ProviderError):
    """Provider returned a 5xx error."""

    def __init__(
        self,
        message: str = "Provider server error",
        status_code: int = 500,
    ) -> None:
        super().__init__(
            message,
            code="PROVIDER_SERVER_ERROR",
            retryable=True,
            details={"status_code": status_code},
        )


class ProviderContentFilterError(ProviderError):
    """Content was refused by the provider's safety filter."""

    def __init__(self, message: str = "Content refused by provider safety filter") -> None:
        super().__init__(message, code="PROVIDER_CONTENT_FILTER_ERROR", retryable=False)


class ProviderInvalidRequestError(ProviderError):
    """Request was rejected by the provider (4xx non-auth non-rate)."""

    def __init__(
        self,
        message: str = "Provider rejected the request",
        status_code: int = 400,
    ) -> None:
        super().__init__(
            message,
            code="PROVIDER_INVALID_REQUEST_ERROR",
            retryable=False,
            details={"status_code": status_code},
        )


class ProviderBadResponseError(ProviderError):
    """Provider returned a response that could not be parsed."""

    def __init__(self, message: str = "Provider returned an unparseable response") -> None:
        super().__init__(message, code="PROVIDER_BAD_RESPONSE_ERROR", retryable=True)


class ProviderConfigError(ProviderError):
    """Provider misconfigured — missing key, wrong profile, etc."""

    def __init__(self, message: str = "Provider configuration error") -> None:
        super().__init__(message, code="PROVIDER_CONFIG_ERROR", retryable=False)


class ModelEmptyOutputError(ProviderError):
    """Model returned empty or whitespace-only content."""

    def __init__(self, message: str = "Model returned empty content") -> None:
        super().__init__(message, code="MODEL_EMPTY_OUTPUT", retryable=True)


class ModelOutputTruncatedError(ProviderError):
    """Model output was truncated by the provider (finish_reason=length)."""

    def __init__(self, message: str = "Model output was truncated") -> None:
        super().__init__(message, code="MODEL_OUTPUT_TRUNCATED", retryable=True)


class ModelJsonInvalidError(ProviderError):
    """Model returned content that is not valid JSON."""

    def __init__(self, message: str = "Model returned invalid JSON") -> None:
        super().__init__(message, code="MODEL_JSON_INVALID", retryable=True)


class ModelSemanticallyInvalidError(ProviderError):
    """Model output failed deterministic semantic validation after repair."""

    def __init__(self, message: str = "Model output failed semantic validation") -> None:
        super().__init__(message, code="MODEL_SEMANTICALLY_INVALID", retryable=False)


class ModelCapabilityUnsupportedError(ProviderError):
    """The endpoint does not support a required capability."""

    def __init__(self, message: str = "Model capability is not supported") -> None:
        super().__init__(message, code="MODEL_CAPABILITY_UNSUPPORTED", retryable=False)


class NetworkRetryExhaustedError(ProviderError):
    """Transport retries were exhausted for a retryable network failure."""

    def __init__(self, message: str = "Network retries exhausted") -> None:
        super().__init__(message, code="NETWORK_RETRY_EXHAUSTED", retryable=False)


# ── HTTP status to error mapping ──────────────────────────────────────────


def map_http_error(status_code: int, body: dict[str, Any] | None = None) -> ProviderError:
    """Map an HTTP status code to the appropriate ProviderError subclass.

    Never logs the raw body — only the error type/code.
    """
    message = _extract_message(body)

    if status_code == 401:
        return ProviderAuthError(message or "Invalid or missing API key")
    if status_code == 402:
        return ProviderAuthError(message or "Insufficient quota or payment required")
    if status_code == 403:
        return ProviderAuthError(message or "Access denied")
    if status_code == 429:
        retry_after = _extract_retry_after(body)
        return ProviderRateLimitError(message or "Rate limited", retry_after_seconds=retry_after)
    if status_code == 408:
        return ProviderTimeoutError(message or "Request timed out")
    if 500 <= status_code < 600:
        return ProviderServerError(message or "Provider server error", status_code=status_code)
    if 400 <= status_code < 500 and status_code not in {401, 402, 403, 408, 429}:
        if _is_content_filter(body):
            return ProviderContentFilterError(message or "Content refused")
        return ProviderInvalidRequestError(message or "Invalid request", status_code=status_code)

    return ProviderError(
        message or f"Unexpected HTTP {status_code}",
        code="PROVIDER_HTTP_ERROR",
        retryable=status_code >= 500,
        details={"status_code": status_code},
    )


def _extract_message(body: dict[str, Any] | None) -> str | None:
    if not body:
        return None
    error = body.get("error", {})
    if isinstance(error, dict):
        return error.get("message")
    if isinstance(error, str):
        return error
    return str(body.get("message", "") or "")


def _extract_retry_after(body: dict[str, Any] | None) -> float | None:
    if not body:
        return None
    try:
        return float(body.get("retry_after", body.get("retry_after_seconds", "")))
    except (ValueError, TypeError):
        return None


def _is_content_filter(body: dict[str, Any] | None) -> bool:
    if not body:
        return False
    error = body.get("error", {})
    if isinstance(error, dict):
        code = str(error.get("code", "") or error.get("type", ""))
        return "content_filter" in code or "safety" in code or "moderation" in code
    return False
