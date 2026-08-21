"""Configuration-driven model/profile routing.

The router is deliberately independent from agent business logic. Agents and
handlers identify a logical engine (or an existing operation profile), while
``config/models.toml`` decides which provider/model profile is used. This
keeps a future provider or per-engine model change out of the agent modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oryxenai.core.settings import ModelConfig, ModelProfile


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
