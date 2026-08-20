"""No-context provider compatibility checks shared by Code Generator entrypoints."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from oryxenai.agents.code_generator.session_schemas import ProviderPreflightEnvelope
from oryxenai.agents.shared.model_client import build_provider_client, resolve_api_key

_PREFLIGHT_TTL_SECONDS = 300.0
_PREFLIGHT_CACHE: dict[str, float] = {}
_PREFLIGHT_PROTOCOL = "code-generator-preflight-v1"


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


class _PreflightInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol: str = _PREFLIGHT_PROTOCOL


PreflightCallable = Callable[[str], Awaitable[dict[str, Any]]]


async def run_provider_preflight(
    settings: Any,
    profile_names: list[str],
    *,
    provider_preflight: PreflightCallable | None = None,
) -> dict[str, Any]:
    """Check each distinct configured provider contract with no portfolio data."""

    identities: dict[str, str] = {}
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
        identity = hashlib.sha256(profile.model_dump_json().encode("utf-8")).hexdigest()
        identities.setdefault(identity, profile_name)

    checked: list[str] = []
    for identity, profile_name in identities.items():
        if time.monotonic() - _PREFLIGHT_CACHE.get(identity, 0.0) <= _PREFLIGHT_TTL_SECONDS:
            checked.append(profile_name)
            continue
        try:
            if provider_preflight is not None:
                await provider_preflight(profile_name)
            else:
                client = build_provider_client(profile_name, settings.models)
                if client is None:
                    raise ProviderPreflightError(
                        "CODE_GENERATOR_PROVIDER_UNAVAILABLE",
                        "The configured Code Generator provider client is unavailable.",
                        details={"profile": profile_name},
                    )
                try:
                    result = await client.generate_structured(
                        operation="code_generator.provider_preflight",
                        instructions=(
                            "Return ok=true and protocol=code-generator-preflight-v1. "
                            "This fixed request contains no user or portfolio data."
                        ),
                        input_payload=_PreflightInput().model_dump(),
                        output_model=ProviderPreflightEnvelope,
                        system_prompt="You are a transport preflight. Return only the required schema.",
                        model_profile=profile_name,
                        strict_schema=True,
                    )
                finally:
                    close = getattr(client, "aclose", None)
                    if close is not None:
                        await close()
                envelope = ProviderPreflightEnvelope.model_validate(
                    getattr(result, "parsed_output", result)
                )
                if not envelope.ok or envelope.protocol != _PREFLIGHT_PROTOCOL:
                    raise ProviderPreflightError(
                        "PROVIDER_PREFLIGHT_INVALID_RESPONSE",
                        "The provider returned an invalid no-context preflight response.",
                        details={"profile": profile_name},
                    )
        except ProviderPreflightError:
            raise
        except Exception as exc:
            raw_details = getattr(exc, "details", {})
            details: dict[str, str | int | float | bool] = {"profile": profile_name}
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
        _PREFLIGHT_CACHE[identity] = time.monotonic()
        checked.append(profile_name)

    return {
        "status": "ready",
        "checked_profiles": checked,
        "checked_at": datetime.now(UTC).isoformat(),
        "private_context_sent": False,
        "protocol": _PREFLIGHT_PROTOCOL,
    }


def clear_provider_preflight_cache() -> None:
    """Clear cached receipts for deterministic tests and configuration reloads."""

    _PREFLIGHT_CACHE.clear()


def _safe_message(exc: Exception) -> str:
    message = str(exc).strip()
    if not message:
        return "The configured Code Generator provider failed its no-context preflight."
    return message[:500]
