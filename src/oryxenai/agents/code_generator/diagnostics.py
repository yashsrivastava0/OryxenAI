"""Turn every kind of failure into one exact what / where / why envelope.

This is the substitute for graceful degradation in this phase: the pipeline
never retries or repairs on its own, so the failure it reports must say what
failed (``code``, ``stage``), where (``where``), why (``cause``), and what the
user can do next (``action``).
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any

from oryxenai.agents.code_generator.schemas import (
    FailureEnvelope,
    FailureLocation,
    FailureOwner,
    FailureStage,
)
from oryxenai.agents.code_generator.validate import ValidationReport
from oryxenai.agents.shared.providers.errors import stable_provider_failure
from oryxenai.themes.issues import Issue, bounded

_MAX_LOCATIONS = 8
_MAX_ISSUES_IN_ENVELOPE = 20

_COPY_CODES = frozenset(
    {
        "COPY_MISMATCH",
        "COPY_MISSING",
        "COPY_COUNT_MISMATCH",
        "COPY_UNEXPECTED",
        "TEXT_NOT_APPROVED",
        "TEXT_OUTSIDE_STRUCTURE",
    }
)
_MARKUP_CODES = frozenset(
    {
        "TAG_NOT_ALLOWED",
        "ATTRIBUTE_FORBIDDEN",
        "URL_NOT_ALLOWED",
        "CLASS_NOT_IN_THEME",
        "LINK_NEW_TAB_REQUIRED",
        "ASSET_MISMATCH",
    }
)
_OUTPUT_CODES = frozenset({"OUTPUT_NOT_HTML", "BODY_HAS_DOCUMENT_TAGS", "SIZE_LIMIT"})

# provider code -> (summary, cause, owner, action)
_PROVIDER_COPY: dict[str, tuple[str, str, FailureOwner, str]] = {
    "MODEL_OUTPUT_TRUNCATED": (
        "The model stopped before it finished writing the page.",
        "The page was longer than the configured output limit, so the reply was cut off.",
        "model_output",
        "Try again. If it keeps happening, shorten the longest sections of your content.",
    ),
    "MODEL_JSON_INVALID": (
        "The model's reply could not be read.",
        "The reply was not valid JSON, usually a stray quote or line break inside the page markup.",
        "model_output",
        "Try again.",
    ),
    "MODEL_EMPTY_OUTPUT": (
        "The model returned an empty reply.",
        "The model produced no content for this request.",
        "model_output",
        "Try again.",
    ),
    "MODEL_OUTPUT_INVALID": (
        "The model's reply did not have the expected shape.",
        "The reply was readable but did not contain the page markup the builder needs.",
        "model_output",
        "Try again.",
    ),
    "PROVIDER_TIMEOUT_ERROR": (
        "The model took too long to answer.",
        "The configured model did not finish within its time limit.",
        "infrastructure",
        "Try again in a moment.",
    ),
    "PROVIDER_RATE_LIMIT_ERROR": (
        "The model is busy right now.",
        "The model provider is rate limiting requests.",
        "infrastructure",
        "Wait a minute and try again.",
    ),
    "MODEL_CAPACITY_UNAVAILABLE": (
        "The model has no free capacity right now.",
        "The configured model capacity is fully used at the moment.",
        "infrastructure",
        "Wait a few minutes and try again.",
    ),
    "PROVIDER_CONNECTION_ERROR": (
        "The model could not be reached.",
        "The connection to the model provider failed.",
        "infrastructure",
        "Try again in a moment.",
    ),
    "PROVIDER_SERVER_ERROR": (
        "The model provider had an internal error.",
        "The provider returned a server error.",
        "infrastructure",
        "Try again in a moment.",
    ),
    "PROVIDER_AUTH_ERROR": (
        "The model credentials were rejected.",
        "The configured API key is missing, invalid or expired.",
        "configuration",
        "This needs the site operator: the model credentials must be fixed.",
    ),
    "MODEL_PROVIDER_CREDIT_EXHAUSTED": (
        "The model account is out of credit.",
        "The provider reports that no usage credit is left.",
        "configuration",
        "This needs the site operator: the model account must be topped up.",
    ),
    "PROVIDER_INVALID_REQUEST_ERROR": (
        "The model rejected the request.",
        "The provider refused the request as malformed, which points to a configuration problem.",
        "configuration",
        "This needs the site operator.",
    ),
    "PROVIDER_BAD_RESPONSE_ERROR": (
        "The model's reply was not usable.",
        "The provider returned a response this builder could not read.",
        "infrastructure",
        "Try again.",
    ),
    "PROVIDER_CONTENT_FILTER_ERROR": (
        "The model declined to write this page.",
        "The provider's safety filter blocked the request.",
        "model_output",
        "Try again. If it repeats, review your content for sensitive wording.",
    ),
    "PROVIDER_HTTP_ERROR": (
        "The model provider returned an unexpected response.",
        "The provider answered with a status this builder does not recognize.",
        "infrastructure",
        "Try again in a moment.",
    ),
    "NETWORK_RETRY_EXHAUSTED": (
        "The model could not be reached after several attempts.",
        "The connection to the model provider kept failing.",
        "infrastructure",
        "Try again in a moment.",
    ),
    "MODEL_INPUT_POLICY_BLOCKED": (
        "This content cannot be sent to the configured model.",
        "The routing policy does not approve the configured provider for this kind of content.",
        "configuration",
        "This needs the site operator.",
    ),
    "MODEL_INPUT_TOO_LARGE": (
        "Your content is too large for the page builder.",
        "The approved content is longer than the model's configured input limit.",
        "content",
        "Shorten the longest sections of your content plan, then generate again.",
    ),
    "MODEL_CAPABILITY_UNSUPPORTED": (
        "The configured model cannot do this job.",
        "The model route does not support a capability the page builder requires.",
        "configuration",
        "This needs the site operator.",
    ),
    "MODEL_USAGE_PERSISTENCE_UNAVAILABLE": (
        "Usage accounting is unavailable right now.",
        "The builder could not record model usage, so no request was sent.",
        "infrastructure",
        "Try again in a moment.",
    ),
    "MODEL_USAGE_SETTLEMENT_UNAVAILABLE": (
        "Usage accounting could not record the model's reply.",
        "The model answered, but its usage could not be saved, so the reply was discarded.",
        "infrastructure",
        "Try again in a moment.",
    ),
    "PROVIDER_CONFIG_ERROR": (
        "The model is not configured correctly.",
        "The model configuration is incomplete or invalid.",
        "configuration",
        "This needs the site operator.",
    ),
    "MODEL_CALL_ALLOWANCE_EXHAUSTED": (
        "This build already used its model-call allowance.",
        "A single build may only make a fixed number of model calls and that limit was reached.",
        "infrastructure",
        "Start a new build with Retry.",
    ),
    "MODEL_ROUTING_POLICY_CHANGED": (
        "The model settings changed while this build was queued.",
        "The routing configuration was updated after the build was created.",
        "configuration",
        "Start a new build with Retry.",
    ),
}


def reference_for(*parts: object) -> str:
    material = "|".join(str(part) for part in parts)
    return "cg-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:10]


def _locations(issues: Sequence[Issue]) -> list[FailureLocation]:
    locations: list[FailureLocation] = []
    for issue in issues:
        if len(locations) >= _MAX_LOCATIONS:
            break
        if issue.origin and issue.origin.partition(":")[0] in {"viewport", "request", "file"}:
            kind, _, ref = issue.origin.partition(":")
            locations.append(
                FailureLocation(kind=kind, ref=ref, detail=issue.message)  # type: ignore[arg-type]
            )
        elif issue.path:
            locations.append(FailureLocation(kind="field", ref=issue.path, detail=issue.message))
        elif issue.selector:
            locations.append(
                FailureLocation(kind="selector", ref=issue.selector, detail=issue.message)
            )
        elif issue.line is not None:
            locations.append(
                FailureLocation(
                    kind="source",
                    ref=f"line {issue.line}, column {issue.column or 1}",
                    detail=issue.message,
                )
            )
    return locations


def failure_from_issues(
    issues: Sequence[Issue],
    *,
    stage: FailureStage,
    code: str,
    summary: str,
    cause: str,
    owner: FailureOwner,
    action: str,
    retryable: bool = True,
    reference: str = "",
) -> FailureEnvelope:
    errors = [issue for issue in issues if issue.is_error] or list(issues)
    # Findings that name a content field (with expected/found) explain the failure best.
    errors = sorted(errors, key=lambda issue: (issue.path is None, issue.selector is None))
    first = errors[0] if errors else None
    return FailureEnvelope(
        code=code,
        stage=stage,
        summary=summary,
        cause=cause,
        where=_locations(errors),
        expected=bounded(first.expected) if first else None,
        found=bounded(first.found) if first else None,
        owner=owner,
        retryable=retryable,
        action=action,
        issue_count=len(errors),
        reference=reference,
        issues=[issue.to_dict() for issue in errors[:_MAX_ISSUES_IN_ENVELOPE]],
    )


def failure_from_validation(report: ValidationReport, *, reference: str = "") -> FailureEnvelope:
    """The page the model wrote failed the host's checks."""
    errors = sorted(report.errors, key=lambda issue: (issue.path is None, issue.selector is None))
    codes = {issue.code for issue in errors}
    count = len(errors)
    first = errors[0]
    noun = "check" if count == 1 else "checks"
    if any(code.startswith("HTML_") or code == "HTML_UNCLOSED_ELEMENT" for code in codes):
        code, cause = (
            "HTML_NOT_WELL_FORMED",
            "The markup has tags that are not properly opened and closed, so its structure cannot be trusted.",
        )
    elif codes & _OUTPUT_CODES:
        code, cause = (
            "PAGE_OUTPUT_INVALID",
            "The model's output was not a page body (extra wrapping, commentary or a size problem).",
        )
    elif codes & _COPY_CODES:
        code, cause = (
            "PAGE_COPY_MISMATCH",
            "The model changed, dropped, added or misplaced approved wording. Approved copy must appear exactly, in its own place.",
        )
    elif codes & _MARKUP_CODES:
        code, cause = (
            "PAGE_MARKUP_NOT_ALLOWED",
            "The page uses markup, classes or links the pinned theme does not allow.",
        )
    else:
        code, cause = (
            "PAGE_STRUCTURE_INVALID",
            "The page structure does not match the theme's required layout.",
        )
    return failure_from_issues(
        errors,
        stage="validate",
        code=code,
        summary=f"The generated page failed {count} {noun}; first: {first.message}",
        cause=cause,
        owner="validation" if code == "PAGE_MARKUP_NOT_ALLOWED" else "model_output",
        action="Nothing was published and your last verified page is unchanged. Try again; if it repeats, copy the diagnostics for support.",
        reference=reference,
    )


def failure_from_verification(issues: Sequence[Issue], *, reference: str = "") -> FailureEnvelope:
    """A real browser loaded the page and found a defect."""
    errors = [issue for issue in issues if issue.is_error] or list(issues)
    count = len(errors)
    first = errors[0]
    return failure_from_issues(
        errors,
        stage="verify",
        code="PAGE_BROWSER_CHECK_FAILED",
        summary=f"The page failed {count} browser check{'s' if count != 1 else ''}; first: {first.message}",
        cause="A real browser loaded the page and found a problem such as a console error, a blocked or failed request, a missing font or a broken image.",
        owner="browser",
        action="Nothing was published and your last verified page is unchanged. Try again; if it repeats, copy the diagnostics for support.",
        reference=reference,
    )


def failure_from_admission(issues: Sequence[Issue], *, reference: str = "") -> FailureEnvelope:
    count = len(issues)
    first = issues[0]
    return failure_from_issues(
        issues,
        stage="start",
        code="CONTENT_NOT_BUILDABLE",
        summary=f"Your content cannot be built into a page yet ({count} problem{'s' if count != 1 else ''}); first: {first.message}",
        cause="The approved content does not fit the pinned page template, so no model call was made.",
        owner="content",
        action="Revise your content plan to fix the listed fields, then generate again.",
        retryable=False,
        reference=reference,
    )


def failure_from_provider_error(
    error: BaseException, *, stage: FailureStage, reference: str = ""
) -> FailureEnvelope:
    """A model call failed (timeout, rate limit, truncation, unreadable reply...)."""
    code, _safe_message = stable_provider_failure(error)
    known = _PROVIDER_COPY.get(code)
    if known is None:
        summary = "The model request failed."
        cause = "The model provider returned an error this builder does not recognize."
        owner: FailureOwner = "infrastructure"
        action = "Try again. If it repeats, copy the diagnostics for support."
    else:
        summary, cause, owner, action = known
    retryable = bool(getattr(error, "retryable", True))
    if owner == "configuration":
        retryable = False
    return FailureEnvelope(
        code=code,
        stage=stage,
        summary=summary,
        cause=cause,
        owner=owner,
        retryable=retryable,
        action=action,
        reference=reference,
    )


def failure_unexpected(
    error: BaseException, *, stage: FailureStage, reference: str = ""
) -> FailureEnvelope:
    """An unexpected host error: report its type only, never its message."""
    return FailureEnvelope(
        code="CODE_GENERATOR_INTERNAL_ERROR",
        stage=stage,
        summary="Something went wrong inside the page builder.",
        cause=f"An unexpected {type(error).__name__} occurred while running the '{stage}' step.",
        owner="infrastructure",
        retryable=True,
        action="Try again. If it repeats, copy the diagnostics for support.",
        reference=reference,
    )


def failure_worker_lost(
    *, stage: FailureStage = "generate", reference: str = ""
) -> FailureEnvelope:
    return FailureEnvelope(
        code="WORKER_LOST",
        stage=stage,
        summary="The build was interrupted before it finished.",
        cause="The background worker stopped, restarted or timed out while this build was running.",
        owner="infrastructure",
        retryable=True,
        action="Your last verified page is unchanged. Start the build again.",
        reference=reference,
    )


def failure_cancelled(*, reference: str = "") -> FailureEnvelope:
    return FailureEnvelope(
        code="JOB_CANCELLED",
        stage="generate",
        summary="The build was stopped.",
        cause="You stopped this build.",
        owner="user_input",
        retryable=True,
        action="Your last verified page is unchanged. Start a new build when you are ready.",
        reference=reference,
    )


def envelope_payload(envelope: FailureEnvelope) -> dict[str, Any]:
    return envelope.to_payload()
