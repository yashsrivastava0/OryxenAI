"""Provider-agnostic error types for model client adapters.

Every provider adapter raises only these types (or their subclasses).
Callers never need to know which provider generated the error.
"""

from __future__ import annotations

import hashlib
from typing import Any

MODEL_PROVIDER_CREDIT_EXHAUSTED = "MODEL_PROVIDER_CREDIT_EXHAUSTED"
MODEL_PROVIDER_CREDIT_MESSAGE = (
    "The configured model provider has no available credit. Retry this same run later."
)
_CREDIT_MARKERS = (
    "insufficient_quota",
    "credit_balance_exhausted",
    "quota_exceeded",
    "insufficient_credit",
    "insufficient_credits",
    "billing_hard_limit",
    "billing_not_active",
    "payment_required",
    # Anthropic's actual wording for this condition doesn't use a distinct
    # error code — it's a plain "invalid_request_error" whose message reads
    # "Your credit balance is too low to access the Anthropic API. Please go
    # to Plans & Billing to upgrade or purchase credits." Without these
    # markers this fell through to the generic PROVIDER_INVALID_REQUEST_ERROR
    # bucket instead of the dedicated, correctly-retried credit-error path.
    "credit balance is too low",
    "plans & billing",
    "purchase credits",
)
_SAFE_FAILURE_MESSAGES = {
    "PROVIDER_AUTH_ERROR": "The configured model provider rejected its credentials.",
    "PROVIDER_CONNECTION_ERROR": "The configured model provider could not be reached.",
    "PROVIDER_TIMEOUT_ERROR": "The configured model provider timed out.",
    "PROVIDER_RATE_LIMIT_ERROR": "The configured model provider rate-limited the request.",
    "PROVIDER_SERVER_ERROR": "The configured model provider returned a temporary server error.",
    "PROVIDER_INVALID_REQUEST_ERROR": "The configured model provider rejected the request.",
    "PROVIDER_BAD_RESPONSE_ERROR": "The configured model provider returned an invalid response.",
    "PROVIDER_CONFIG_ERROR": "The configured model provider is unavailable.",
    "PROVIDER_CONTENT_FILTER_ERROR": "The model provider refused the request safely.",
    "PROVIDER_HTTP_ERROR": "The configured model provider returned an unexpected response.",
    "MODEL_OUTPUT_INVALID": "The model returned output that did not satisfy the required structure.",
    "MODEL_CACHE_WAIT_TIMEOUT": "Another model operation is still producing this result; retry safely.",
    "MODEL_CAPACITY_UNAVAILABLE": "No eligible free model capacity is available for this operation.",
    "MODEL_INPUT_POLICY_BLOCKED": "This operation requires a provider approved for the supplied input.",
    "MODEL_INPUT_TOO_LARGE": "The approved input is too large for this operation's configured limit.",
    "MODEL_ROUTING_POLICY_CHANGED": "The saved routing policy changed before this operation ran; restart the stage safely.",
    "MODEL_USAGE_PERSISTENCE_UNAVAILABLE": "Model usage accounting is temporarily unavailable; no provider request was sent.",
    "NETWORK_RETRY_EXHAUSTED": "The model provider network retry budget was exhausted.",
    "CODE_GENERATOR_PROVIDER_CREDENTIAL_MISSING": "The configured model provider credentials are missing.",
    "CODE_GENERATOR_PROVIDER_UNAVAILABLE": "The configured model provider is unavailable.",
}


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
        self.message = message
        self.code = code
        self.retryable = retryable
        self.details = details or {}


class ProviderAuthError(ProviderError):
    """Authentication failed — key invalid, expired, or revoked."""

    def __init__(self, message: str = "Provider authentication failed") -> None:
        super().__init__(message, code="PROVIDER_AUTH_ERROR", retryable=False)


class ProviderCreditError(ProviderAuthError):
    """The credential is recognized, but billable capacity is unavailable."""

    def __init__(self, message: str = "Provider credit or quota is exhausted") -> None:
        ProviderError.__init__(self, message, code="PROVIDER_CREDIT_EXHAUSTED", retryable=False)


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

    def __init__(
        self,
        message: str = "Provider connection failed",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="PROVIDER_CONNECTION_ERROR",
            retryable=True,
            details=details,
        )


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
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged_details = {"status_code": status_code}
        if details:
            merged_details.update(details)
        super().__init__(
            message,
            code="PROVIDER_INVALID_REQUEST_ERROR",
            retryable=False,
            details=merged_details,
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


class ModelOutputInvalidError(ProviderError):
    """Parsed model output failed an agent's deterministic output contract."""

    def __init__(self, message: str = "Model output failed structural validation") -> None:
        super().__init__(message, code="MODEL_OUTPUT_INVALID", retryable=True)


class ModelSemanticallyInvalidError(ProviderError):
    """Model output failed deterministic semantic validation after repair."""

    def __init__(self, message: str = "Model output failed semantic validation") -> None:
        super().__init__(message, code="MODEL_SEMANTICALLY_INVALID", retryable=False)


class ModelCapabilityUnsupportedError(ProviderError):
    """The endpoint does not support a required capability."""

    def __init__(self, message: str = "Model capability is not supported") -> None:
        super().__init__(message, code="MODEL_CAPABILITY_UNSUPPORTED", retryable=False)


class ModelInputTooLargeError(ProviderError):
    """The application admission ceiling was exceeded before transmission."""

    def __init__(
        self, message: str = "The model input exceeds the configured operation limit"
    ) -> None:
        super().__init__(message, code="MODEL_INPUT_TOO_LARGE", retryable=False)


class ModelUsagePersistenceError(ProviderError):
    """The durable pre-send accounting transaction could not be committed."""

    def __init__(self, message: str = "Model usage accounting is unavailable") -> None:
        super().__init__(message, code="MODEL_USAGE_PERSISTENCE_UNAVAILABLE", retryable=True)


class ModelCapacityUnavailableError(ProviderError):
    """No observed free capacity remains for the selected source/window."""

    def __init__(self, message: str = "No eligible free model capacity is available") -> None:
        super().__init__(message, code="MODEL_CAPACITY_UNAVAILABLE", retryable=True)


class ModelRoutingPolicyChangedError(ProviderError):
    """The immutable operation snapshot no longer matches live config."""

    def __init__(self) -> None:
        super().__init__(
            "The saved model routing policy changed before this operation ran.",
            code="MODEL_ROUTING_POLICY_CHANGED",
            retryable=False,
        )


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
    error: ProviderError

    if status_code == 401:
        error = ProviderAuthError(message or "Invalid or missing API key")
        error.details.update(_safe_error_details(body))
        return error
    if _is_credit_exhausted(body) or status_code == 402:
        error = ProviderCreditError(message or "Provider credit or quota is exhausted")
        error.details.update(_safe_error_details(body))
        return error
    if status_code == 403:
        error = ProviderAuthError(message or "Access denied")
        error.details.update(_safe_error_details(body))
        return error
    if status_code == 429:
        retry_after = _extract_retry_after(body)
        error = ProviderRateLimitError(
            message or "Rate limited", retry_after_seconds=retry_after
        )
        error.details.update(_safe_error_details(body))
        return error
    if status_code == 408:
        error = ProviderTimeoutError(message or "Request timed out")
        error.details.update(_safe_error_details(body))
        return error
    if 500 <= status_code < 600:
        error = ProviderServerError(message or "Provider server error", status_code=status_code)
        error.details.update(_safe_error_details(body))
        return error
    if 400 <= status_code < 500 and status_code not in {401, 402, 403, 408, 429}:
        if _is_content_filter(body):
            return ProviderContentFilterError(message or "Content refused")
        return ProviderInvalidRequestError(
            message or "Invalid request",
            status_code=status_code,
            details=_safe_error_details(body),
        )

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


def _safe_error_details(body: dict[str, Any] | None) -> dict[str, Any]:
    """Extract small, non-secret provider diagnostics without the raw body."""

    if not body:
        return {}
    error = body.get("error", {})
    if not isinstance(error, dict):
        return {}
    details: dict[str, Any] = {}
    for source, target in (
        ("type", "provider_error_type"),
        ("code", "provider_error_code"),
        ("param", "provider_parameter"),
    ):
        value = error.get(source)
        if isinstance(value, (str, int, float, bool)) and str(value):
            details[target] = value
    request_id = body.get("request_id") or body.get("requestId")
    if isinstance(request_id, (str, int, float, bool)) and str(request_id):
        details["provider_request_id"] = request_id
    retry_after = _extract_retry_after(body)
    if retry_after is not None:
        details["retry_after_seconds"] = retry_after
    quota = _extract_quota_details(body)
    if quota:
        details.update(quota)
    return details


def _extract_retry_after(body: dict[str, Any] | None) -> float | None:
    """Extract a provider retry delay without retaining the raw error body.

    OpenAI-compatible gateways commonly put the delay at the top level,
    while Gemini returns ``google.rpc.RetryInfo`` in ``error.details`` as a
    duration such as ``"12s"``.  The parser is deliberately recursive and
    accepts only scalar duration fields; it never returns provider text.
    """

    if not body:
        return None

    keys = {
        "retry_after",
        "retry_after_seconds",
        "retryafter",
        "retry_after_ms",
        "retry_delay",
        "retrydelay",
    }

    def parse(value: Any, *, key: str = "") -> float | None:
        normalized = key.casefold().replace("-", "_")
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            number = float(value)
            if number < 0:
                return None
            return number / 1000.0 if normalized.endswith("_ms") else number
        if isinstance(value, str):
            raw = value.strip().casefold()
            if not raw:
                return None
            multiplier = 1.0
            if raw.endswith("ms"):
                multiplier = 0.001
                raw = raw[:-2].strip()
            elif raw.endswith("s"):
                raw = raw[:-1].strip()
            try:
                number = float(raw)
            except ValueError:
                return None
            return number * multiplier if number >= 0 else None
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                normalized_child = str(child_key).casefold().replace("-", "_")
                if normalized_child in keys or isinstance(child_value, (dict, list)):
                    found = parse(child_value, key=normalized_child)
                    if found is not None:
                        return found
        elif isinstance(value, list):
            for child in value:
                found = parse(child)
                if found is not None:
                    return found
        return None

    return parse(body)


def _extract_quota_details(body: dict[str, Any] | None) -> dict[str, Any]:
    """Return small, provider-neutral quota diagnostics from a safe body."""

    if not body:
        return {}
    result: dict[str, Any] = {}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            metric = value.get("quotaMetric") or value.get("quota_metric")
            limit = value.get("quotaLimit") or value.get("quota_limit")
            location = value.get("quotaLocation") or value.get("quota_location")
            if isinstance(metric, str) and metric:
                result.setdefault("quota_metric", metric[:200])
            if isinstance(limit, str) and limit:
                result.setdefault("quota_limit", limit[:200])
            if isinstance(location, str) and location:
                result.setdefault("quota_location", location[:200])
            for child in value.values():
                if isinstance(child, (dict, list)):
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    error = body.get("error") if isinstance(body, dict) else None
    visit(error if isinstance(error, (dict, list)) else body)
    return result


def _is_content_filter(body: dict[str, Any] | None) -> bool:
    if not body:
        return False
    error = body.get("error", {})
    if isinstance(error, dict):
        code = str(error.get("code", "") or error.get("type", ""))
        return "content_filter" in code or "safety" in code or "moderation" in code
    return False


def _is_credit_exhausted(body: dict[str, Any] | None) -> bool:
    if not body:
        return False
    error = body.get("error", {})
    if not isinstance(error, dict):
        return False
    values = (
        str(error.get("code", "")),
        str(error.get("type", "")),
        str(error.get("message", "")),
    )
    return any(marker in value.casefold() for value in values for marker in _CREDIT_MARKERS)


def is_provider_credit_error(error: Any) -> bool:
    """Recognize exhausted provider credit without exposing provider details."""

    if isinstance(error, dict):
        code_value = error.get("code", "")
        message_value = error.get("message", "")
        details = error.get("details")
    else:
        code_value = getattr(error, "code", "")
        message_value = getattr(error, "message", "")
        details = getattr(error, "details", None)
    code = str(code_value or "").casefold()
    if code in {"provider_credit_exhausted", MODEL_PROVIDER_CREDIT_EXHAUSTED.casefold()}:
        return True
    values = [code, str(message_value or "").casefold()]
    if isinstance(details, dict):
        values.extend(str(value).casefold() for value in details.values())
    return any(marker in value for value in values for marker in _CREDIT_MARKERS)


def stable_provider_failure(error: Any) -> tuple[str, str]:
    """Return a redacted public failure code/message for provider failures."""

    if is_provider_credit_error(error):
        return MODEL_PROVIDER_CREDIT_EXHAUSTED, MODEL_PROVIDER_CREDIT_MESSAGE
    if isinstance(error, dict):
        code = error.get("code", "MODEL_OPERATION_FAILED")
    else:
        code = getattr(error, "code", "MODEL_OPERATION_FAILED")
    safe_code = str(code or "MODEL_OPERATION_FAILED")
    if safe_code in _SAFE_FAILURE_MESSAGES:
        return safe_code, _SAFE_FAILURE_MESSAGES[safe_code]
    # This function is used at provider boundaries. Unknown provider codes and
    # messages are never safe to echo because they may contain response bodies,
    # request metadata, or billing details.
    return safe_code, "The model operation failed safely."


def safe_operation_failure(
    error: Any,
    *,
    operation: str = "",
    provider_label: str = "Configured model provider",
    support_seed: str = "",
) -> dict[str, Any]:
    """Build the public error envelope without provider internals or secrets."""

    code, message = stable_provider_failure(error)
    details = error.get("details") if isinstance(error, dict) else getattr(error, "details", {})
    if not isinstance(details, dict):
        details = {}
    retry_after = details.get("retry_after_seconds")
    support_material = "|".join(
        (str(code), str(operation), str(support_seed or details.get("provider_request_id", "")))
    )
    reference = hashlib.sha256(support_material.encode("utf-8")).hexdigest()[:12]
    payload: dict[str, Any] = {
        "code": code,
        "message": message,
        "provider_label": str(details.get("provider_label") or provider_label),
        "operation_label": str(operation or "model operation"),
        "support_reference": f"model-{reference}",
        "retryable": bool(
            error.get("retryable", False)
            if isinstance(error, dict)
            else getattr(error, "retryable", False)
        ),
    }
    if isinstance(retry_after, (int, float)) and retry_after >= 0:
        payload["retry_after_seconds"] = float(retry_after)
    return payload
