"""No-context provider compatibility checks shared by Code Generator entrypoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import (
    CreativeDirectionSetV3,
    ExperienceBlueprintV4,
    IntegrationReviewV1,
    QualityReviewDraftV1,
    SourceGenerationEnvelopeV2,
)
from oryxenai.agents.code_generator.core.resource_scout import ScoutSelection
from oryxenai.agents.code_generator.session_schemas import ProviderPreflightEnvelope
from oryxenai.agents.shared.model_client import resolve_api_key
from oryxenai.agents.shared.model_runtime import (
    clear_model_preflight_caches,
    get_model_runtime,
)
from oryxenai.agents.shared.providers.schema_compatibility import schema_compatibility_issues
from oryxenai.core.logging import redact_sensitive_text

_PREFLIGHT_PROTOCOL = "code-generator-preflight-v1"
_WIRE_MODELS = (
    CreativeDirectionSetV3,
    ExperienceBlueprintV4,
    ScoutSelection,
    SourceGenerationEnvelopeV2,
    QualityReviewDraftV1,
    IntegrationReviewV1,
    ProviderPreflightEnvelope,
)


def code_generator_wire_schema_issues() -> dict[str, list[str]]:
    """Return compatibility diagnostics for every structured wire DTO."""

    return {model.__name__: schema_compatibility_issues(model) for model in _WIRE_MODELS}


class ProviderPreflightError(RuntimeError):
    """A safe, actionable failure from the provider compatibility check."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


PreflightCallable = Callable[[str], Awaitable[dict[str, Any]]]


async def run_provider_preflight(
    settings: Any,
    profile_names: list[str],
    *,
    provider_preflight: PreflightCallable | None = None,
) -> dict[str, Any]:
    """Check each distinct configured provider contract with no portfolio data."""

    wire_schema_issues = code_generator_wire_schema_issues()
    incompatible = {name: issues for name, issues in wire_schema_issues.items() if issues}
    if incompatible:
        raise ProviderPreflightError(
            "CODE_GENERATOR_WIRE_SCHEMA_UNSUPPORTED",
            "A Code Generator structured-output schema is not provider-compatible.",
            details={
                "schemas": "; ".join(
                    f"{name}:{','.join(issues)}" for name, issues in incompatible.items()
                )[:1000]
            },
        )

    profile_ids: list[str] = []
    for profile_name in dict.fromkeys(profile_names):
        profile = settings.models.get_profile(profile_name)
        if profile is None or not profile.provider or not profile.model:
            raise ProviderPreflightError(
                "CODE_GENERATOR_PROFILE_UNAVAILABLE",
                "A required Code Generator model profile is unavailable.",
                details={"profile": profile_name},
            )
        if (
            profile.capabilities is None
            or not profile.capabilities.json_schema_mode
            or profile.capabilities.structured_output_mode != "native_json_schema"
        ):
            raise ProviderPreflightError(
                "CODE_GENERATOR_STRICT_SCHEMA_UNSUPPORTED",
                "A required Code Generator profile does not declare native JSON Schema support.",
                details={"profile": profile_name},
            )
        if not resolve_api_key(profile):
            raise ProviderPreflightError(
                "CODE_GENERATOR_PROVIDER_CREDENTIAL_MISSING",
                "A required Code Generator provider credential is not configured.",
                details={"profile": profile_name},
            )
        profile_ids.append(profile_name)

    checked: list[str] = []
    if provider_preflight is not None:
        for profile_name in profile_ids:
            try:
                await provider_preflight(profile_name)
            except ProviderPreflightError:
                raise
            except Exception as exc:
                raise ProviderPreflightError(
                    str(getattr(exc, "code", "PROVIDER_PREFLIGHT_FAILED")),
                    _safe_message(exc),
                    details={"profile": profile_name},
                ) from exc
            checked.append(profile_name)
    else:
        try:
            receipt = await get_model_runtime(settings.models).preflight(profile_ids)
        except ProviderPreflightError:
            raise
        except Exception as exc:
            raw_details = getattr(exc, "details", {})
            details: dict[str, str | int | float | bool] = {}
            if isinstance(raw_details, dict):
                details.update(
                    {
                        str(key): value
                        for key, value in raw_details.items()
                        if isinstance(key, str) and isinstance(value, (str, int, float, bool))
                    }
                )
            raise ProviderPreflightError(
                str(getattr(exc, "code", "PROVIDER_PREFLIGHT_FAILED")),
                _safe_message(exc),
                details=details,
            ) from exc
        checked = [
            str(item.get("profile_id", ""))
            for item in receipt.get("profiles", [])
            if isinstance(item, dict)
        ]

    return {
        "status": "ready",
        "checked_profiles": checked,
        "checked_at": datetime.now(UTC).isoformat(),
        "private_context_sent": False,
        "protocol": _PREFLIGHT_PROTOCOL,
        "checked_identity_count": len(checked),
    }


def provider_preflight_status(settings: Any, profile_names: list[str]) -> dict[str, Any]:
    """Read the shared preflight cache without contacting the provider.

    The development readiness endpoint is called repeatedly by the browser;
    using this helper keeps those polls free of model/API spend while still
    expiring the status with the runtime's normal preflight TTL.
    """

    try:
        return get_model_runtime(settings.models).preflight_status(profile_names)
    except Exception:
        # Readiness already reports missing profile/credential/schema blockers.
        # A cache lookup must never turn a diagnostics endpoint into a 500.
        return {
            "status": "required",
            "checked": False,
            "checked_profiles": [],
            "private_context_sent": False,
        }


def clear_provider_preflight_cache() -> None:
    """Clear cached receipts for deterministic tests and configuration reloads."""

    clear_model_preflight_caches()


def _safe_message(exc: Exception) -> str:
    message = redact_sensitive_text(str(exc).strip())
    if not message:
        return "The configured Code Generator provider failed its no-context preflight."
    return message[:500]
