"""Central failure classification for durable Code Generator stages.

The worker decides whether a job is retried, repaired, or made visible as a
terminal issue from this module.  Call sites may attach provider-specific
details, but they do not get to silently redefine the retry boundary.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import Diagnostic, SafeIssue


class FailureClass(StrEnum):
    RETRYABLE_INFRASTRUCTURE = "retryable_infrastructure"
    PERMANENT_INPUT_POLICY = "permanent_input_policy"
    REPAIRABLE_GENERATED_SOURCE = "repairable_generated_source"
    TERMINAL = "terminal"


@dataclass(frozen=True, slots=True)
class FailureClassification:
    category: FailureClass
    code: str
    message: str
    retryable: bool
    repairable: bool
    safe_details: dict[str, str | int | float | bool]


_RETRYABLE_CODES = {
    "JOB_TIMEOUT",
    "PROVIDER_CONNECTION_ERROR",
    "PROVIDER_TIMEOUT_ERROR",
    "PROVIDER_RATE_LIMIT_ERROR",
    "PROVIDER_SERVER_ERROR",
    "ARTIFACT_UPLOAD_FAILED",
    "ARTIFACT_READ_FAILED",
    "ARTIFACT_HEAD_FAILED",
    "ARTIFACT_NOT_FOUND",
    "BROWSER_LAUNCH_FAILED",
    "FILESYSTEM_LOCK_TRANSIENT",
    "R2_TRANSPORT_ERROR",
}
_PERMANENT_CODES = {
    "PROVIDER_AUTH_ERROR",
    "PROVIDER_CREDENTIALS_MISSING",
    "ARTIFACT_HASH_MISMATCH",
    "ARTIFACT_LOCAL_HASH_MISMATCH",
    "ARTIFACT_EXPIRY_INVALID",
    "ARTIFACT_IMMUTABLE_CONFLICT",
    "ARTIFACT_STORAGE_CREDENTIALS_MISSING",
    "ARTIFACT_STORAGE_NOT_CONFIGURED",
    "INPUT_HASH_MISMATCH",
    "PACK_EXPIRED",
    "PACK_SCHEMA_INVALID",
    "PACK_NOT_ELIGIBLE",
    "PACK_PROVENANCE_INVALID",
    "CREDENTIALS_INVALID",
    "FORBIDDEN_RESOURCE",
    "AUTHORITY_MISSING",
}
_REPAIRABLE_PREFIXES = (
    "SOURCE_",
    "TYPECHECK_",
    "BUILD_",
    "DOM_",
    "INTERACTION_",
    "ACCESSIBILITY_",
    "GEOMETRY_",
    "RUNTIME_",
)


def _safe_details(value: Any) -> dict[str, str | int | float | bool]:
    if not isinstance(value, dict):
        return {}
    allowed = (str, int, float, bool)
    return {
        str(key): item
        for key, item in value.items()
        if isinstance(key, str)
        and isinstance(item, allowed)
        and key.casefold() not in {"api_key", "token", "secret", "authorization", "content"}
    }


def classify_failure(error: Any) -> FailureClassification:
    """Classify an exception, safe issue, or diagnostic without leaking data."""

    code = str(getattr(error, "code", "") or "UNKNOWN_FAILURE").upper()
    message = str(
        getattr(error, "message", "")
        or getattr(error, "normalized_message", "")
        or "The Code Generator stage failed safely."
    )
    details = _safe_details(getattr(error, "details", None))
    if code in _RETRYABLE_CODES or any(
        marker in code for marker in ("_CONNECTION", "_TIMEOUT", "_RATE_LIMIT", "_5XX")
    ):
        return FailureClassification(
            FailureClass.RETRYABLE_INFRASTRUCTURE, code, message, True, False, details
        )
    if code in _PERMANENT_CODES or any(
        marker in code for marker in ("_HASH_MISMATCH", "_SCHEMA_INVALID", "_PROVENANCE")
    ):
        return FailureClassification(
            FailureClass.PERMANENT_INPUT_POLICY, code, message, False, False, details
        )
    if code.startswith(_REPAIRABLE_PREFIXES):
        return FailureClassification(
            FailureClass.REPAIRABLE_GENERATED_SOURCE, code, message, False, True, details
        )
    if bool(getattr(error, "retryable", False)):
        return FailureClassification(
            FailureClass.RETRYABLE_INFRASTRUCTURE, code, message, True, False, details
        )
    return FailureClassification(FailureClass.TERMINAL, code, message, False, False, details)


def classify_diagnostics(diagnostics: Iterable[Diagnostic]) -> FailureClassification:
    values = list(diagnostics)
    if not values:
        return FailureClassification(
            FailureClass.TERMINAL,
            "NO_DIAGNOSTICS",
            "No diagnostics were provided for classification.",
            False,
            False,
            {},
        )
    classifications = [classify_failure(item) for item in values]
    if any(item.category is FailureClass.RETRYABLE_INFRASTRUCTURE for item in classifications):
        return next(
            item
            for item in classifications
            if item.category is FailureClass.RETRYABLE_INFRASTRUCTURE
        )
    if all(item.repairable for item in classifications):
        first = classifications[0]
        return FailureClassification(
            FailureClass.REPAIRABLE_GENERATED_SOURCE,
            first.code,
            first.message,
            False,
            True,
            first.safe_details,
        )
    return classifications[0]


def safe_issue_for(error: Any, *, next_action: str = "") -> SafeIssue:
    result = classify_failure(error)
    action = (
        next_action
        or {
            FailureClass.RETRYABLE_INFRASTRUCTURE: "Retry the stage after the dependency recovers.",
            FailureClass.PERMANENT_INPUT_POLICY: "Correct the admitted input or configuration and start a new attempt.",
            FailureClass.REPAIRABLE_GENERATED_SOURCE: "Run the bounded owner-scoped repair and rerun the affected checks.",
            FailureClass.TERMINAL: "Review the safe diagnostic and start a corrected attempt.",
        }[result.category]
    )
    return SafeIssue(
        code=result.code, message=result.message, next_action=action, details=result.safe_details
    )
