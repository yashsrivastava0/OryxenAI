"""No-context provider compatibility checks shared by Code Generator entrypoints."""

from __future__ import annotations

import hashlib
import json
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


def provider_contract_groups(settings: Any, profile_names: list[str]) -> list[tuple[str, str]]:
    """Collapse role aliases sharing a provider/model/schema contract.

    Per-role token budgets, timeouts, and reasoning effort are generation
    policy, not distinct credentials or structured-output contracts. The
    representative with the largest configured output budget is checked once;
    every supplied role is still independently validated by the caller.
    """

    grouped: dict[str, list[str]] = {}
    for profile_name in dict.fromkeys(profile_names):
        profile = settings.models.get_profile(profile_name)
        capabilities = getattr(profile, "capabilities", None)
        identity_payload = {
            "provider": str(getattr(profile, "provider", "") or ""),
            "model": str(getattr(profile, "model", "") or ""),
            "base_url": str(getattr(profile, "base_url", "") or ""),
            "base_url_env": str(getattr(profile, "base_url_env", "") or ""),
            "api_key_env": str(getattr(profile, "api_key_env", "") or ""),
            "request_params": getattr(profile, "request_params", {}) or {},
            "capabilities": (
                capabilities.model_dump(mode="json") if capabilities is not None else {}
            ),
            "store": bool(getattr(profile, "store", False)),
            "prompt_cache_ttl": str(getattr(profile, "prompt_cache_ttl", "") or ""),
        }
        identity = hashlib.sha256(
            json.dumps(
                identity_payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        grouped.setdefault(identity, []).append(profile_name)

    result: list[tuple[str, str]] = []
    effort_rank = {"none": 0, "low": 1, "medium": 2, "high": 3, "xhigh": 4}
    for identity, members in grouped.items():
        representative = max(
            members,
            key=lambda name: (
                int(getattr(settings.models.get_profile(name), "max_output_tokens", 0) or 0),
                effort_rank.get(
                    str(getattr(settings.models.get_profile(name), "reasoning_effort", "")), 0
                ),
            ),
        )
        result.append((identity, representative))
    return result


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

    representatives = [
        profile_name for _identity, profile_name in provider_contract_groups(settings, profile_ids)
    ]
    checked: list[str] = []
    if provider_preflight is not None:
        for profile_name in representatives:
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
            receipt = await get_model_runtime(settings.models).preflight(representatives)
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
        "covered_profiles": profile_ids,
        "checked_at": datetime.now(UTC).isoformat(),
        "private_context_sent": False,
        "protocol": _PREFLIGHT_PROTOCOL,
        "checked_identity_count": len(representatives),
    }


def provider_preflight_status(settings: Any, profile_names: list[str]) -> dict[str, Any]:
    """Read the shared preflight cache without contacting the provider.

    The development readiness endpoint is called repeatedly by the browser;
    using this helper keeps those polls free of model/API spend while still
    expiring the status with the runtime's normal preflight TTL.
    """

    try:
        representatives = [
            profile_name
            for _identity, profile_name in provider_contract_groups(settings, profile_names)
        ]
        return get_model_runtime(settings.models).preflight_status(representatives)
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
