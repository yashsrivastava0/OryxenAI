"""Provider adapter factory — selects the right adapter from a profile."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from oryxenai.agents.shared.contracts import ModelClient

if TYPE_CHECKING:
    from oryxenai.core.settings import ModelProfile

AdapterBuilder = Callable[["ModelProfile"], ModelClient]


def _openai_compatible(profile: ModelProfile) -> ModelClient:
    from oryxenai.agents.shared.providers.opencode_go import OpenAICompatibleAdapter

    return OpenAICompatibleAdapter(profile)


def _anthropic(profile: ModelProfile) -> ModelClient:
    from oryxenai.agents.shared.providers.anthropic import AnthropicAdapter

    return AnthropicAdapter(profile)


_ADAPTER_BUILDERS: dict[str, AdapterBuilder] = {
    "opencode_go": _openai_compatible,
    "openai": _openai_compatible,
    "openai_compatible": _openai_compatible,
    "anthropic": _anthropic,
}


def register_adapter(provider: str, builder: AdapterBuilder) -> None:
    normalized = str(provider or "").strip().casefold()
    if not normalized:
        raise ValueError("provider must not be empty")
    _ADAPTER_BUILDERS[normalized] = builder


def supported_providers() -> tuple[str, ...]:
    return tuple(sorted(_ADAPTER_BUILDERS))


def build_adapter(profile: ModelProfile) -> ModelClient:
    """Build the correct provider adapter for the given profile.

    Provider selection is based on `profile.provider`. Adding a new
    provider means adding an entry to the registry below.
    """
    provider = profile.provider.strip().casefold()
    builder = _ADAPTER_BUILDERS.get(provider)
    if builder is not None:
        return builder(profile)
    if provider == "openai_responses":
        raise ValueError(
            "Provider 'openai_responses' is not implemented. Configure an "
            "OpenAI Chat Completions profile or add a native Responses adapter."
        )

    raise ValueError(
        f"Unknown provider '{profile.provider}'. "
        f"Supported providers: {', '.join(supported_providers())}"
    )


def can_build(profile: ModelProfile) -> bool:
    """Check whether an adapter can be built without actually building it."""
    return profile.provider.strip().casefold() in _ADAPTER_BUILDERS
