"""Configuration-driven model/profile routing.

The router is deliberately independent from agent business logic. Agents and
handlers identify a logical engine (or an existing operation profile), while
``config/models.toml`` decides which provider/model profile is used. This
keeps a future provider or per-engine model change out of the agent modules.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oryxenai.core.settings import ModelConfig, ModelProfile, OperationRouteConfig


@dataclass(frozen=True)
class ModelProfileOption:
    """Safe, non-secret profile metadata suitable for an API or UI."""

    id: str
    label: str
    provider: str
    model: str
    is_default: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "provider": self.provider,
            "model": self.model,
            "is_default": self.is_default,
        }


class ModelRouter:
    """Resolve logical engines to configured provider-neutral profiles."""

    def __init__(self, model_config: ModelConfig) -> None:
        self._config = model_config

    @property
    def config(self) -> ModelConfig:
        return self._config

    def fallback_profile_name(self) -> str:
        configured = str(self._config.routing.fallback_profile or "").strip()
        return configured or "default"

    def selectable_profile_names(self) -> tuple[str, ...]:
        names: list[str] = []
        for name in self._config.routing.selectable_profiles:
            value = str(name).strip()
            if value and value in self._config.profiles and value not in names:
                names.append(value)
        return tuple(names)

    def is_selectable(self, profile_name: str) -> bool:
        return profile_name in self.selectable_profile_names()

    def routed_profile_name(self, engine: str) -> str:
        logical_name = str(engine or "").strip()
        routed = str(self._config.routing.engine_profiles.get(logical_name, "")).strip()
        if routed:
            return routed
        if logical_name in self._config.profiles:
            return logical_name
        return self.fallback_profile_name()

    def resolve_profile_name(self, engine: str, override_profile_name: str = "") -> str:
        override = str(override_profile_name or "").strip()
        if override and self.is_selectable(override):
            return override
        return self.routed_profile_name(engine)

    def resolve_profile(self, engine: str, override_profile_name: str = "") -> ModelProfile | None:
        return self._config.get_profile(self.resolve_profile_name(engine, override_profile_name))

    def operation_route(self, engine: str, operation: str) -> OperationRouteConfig | None:
        """Return the configured route policy for one logical operation."""

        return self._config.routing.operation_route(engine, operation)

    def operation_profile_names(
        self,
        engine: str,
        operation: str,
        *,
        input_classification: str = "unknown",
        override_profile_name: str = "",
    ) -> tuple[str, ...]:
        """Resolve primary and bounded fallback profiles for an operation.

        Gemini profiles are only considered when the packet is explicitly
        marked ``sanitized`` or ``synthetic`` and the operation policy opts in.
        Unknown packets therefore remain on the configured Luna primary.
        """

        override = str(override_profile_name or "").strip()
        route = self.operation_route(engine, operation)
        if route is None:
            name = self.resolve_profile_name(engine, override)
            return (name,) if name else ()
        names: list[str] = []
        classification = str(input_classification or "unknown").strip().casefold()
        if override and self.is_selectable(override):
            names.append(override)
        elif (
            route.allow_gemini
            and classification in {"sanitized", "synthetic"}
            and route.sanitized_primary_profile
        ):
            names.append(route.sanitized_primary_profile)
        elif route.primary_profile:
            names.append(route.primary_profile)
        if route.fallback_profiles:
            names.extend(route.fallback_profiles)
        # A route with a sanitized primary still needs the quality primary as a
        # bounded fallback when it is not explicitly listed.
        if (
            classification in {"sanitized", "synthetic"}
            and route.sanitized_primary_profile
            and route.primary_profile
        ):
            names.append(route.primary_profile)
        result: list[str] = []
        for name in names:
            value = str(name).strip()
            profile = self._config.profiles.get(value)
            if not value or profile is None or value in result:
                continue
            provider = str(profile.provider or "").strip().casefold()
            if provider == "gemini" and (
                not route.allow_gemini or classification not in {"sanitized", "synthetic"}
            ):
                continue
            result.append(value)
        return tuple(result)

    def resolve_operation_profile_name(
        self,
        engine: str,
        operation: str,
        *,
        input_classification: str = "unknown",
        override_profile_name: str = "",
    ) -> str:
        names = self.operation_profile_names(
            engine,
            operation,
            input_classification=input_classification,
            override_profile_name=override_profile_name,
        )
        if not names:
            raise ValueError(f"No configured model route for {engine}.{operation}.")
        return names[0]

    def policy_snapshot(self) -> dict[str, Any]:
        """Return a stable, secret-free snapshot for session persistence."""

        raw = self._config.routing.model_dump(mode="json")
        profile_fingerprints = {
            name: hashlib.sha256(
                json.dumps(
                    {"profile_id": name, **profile.model_dump(mode="json")},
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            for name, profile in sorted(self._config.profiles.items())
            if name in self.selectable_profile_names()
            or any(
                name
                in {
                    route.primary_profile,
                    route.sanitized_primary_profile,
                    *route.fallback_profiles,
                }
                for routes in self._config.routing.operation_profiles.values()
                for route in routes.values()
            )
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                {"routing": raw, "profile_fingerprints": profile_fingerprints},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return {
            "version": self._config.routing.policy.version,
            "fingerprint": fingerprint,
            "routing": raw,
            "profile_fingerprints": profile_fingerprints,
        }

    def public_options(self, default_engine: str = "discovery") -> list[ModelProfileOption]:
        """Return safe default plus configured selectable options."""
        default_id = self.routed_profile_name(default_engine)
        default_profile = self._config.get_profile(default_id)
        options: list[ModelProfileOption] = []
        if default_profile is not None:
            options.append(self._option(default_id, default_profile, is_default=True))
        for profile_name in self.selectable_profile_names():
            if profile_name == default_id:
                continue
            profile = self._config.get_profile(profile_name)
            if profile is not None:
                options.append(self._option(profile_name, profile))
        return options

    @staticmethod
    def _option(
        profile_name: str,
        profile: ModelProfile,
        *,
        is_default: bool = False,
    ) -> ModelProfileOption:
        label = str(profile.display_name or "").strip()
        if not label:
            provider = str(profile.provider or "configured provider").strip()
            model = str(profile.model or "configured model").strip()
            label = f"{provider} — {model}"
        if is_default:
            label = f"{label} (default)"
        return ModelProfileOption(
            id="" if is_default else profile_name,
            label=label,
            provider=str(profile.provider),
            model=str(profile.model),
            is_default=is_default,
        )
