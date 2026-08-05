"""Provider adapter factory — selects the right adapter from a profile."""

from __future__ import annotations

from typing import TYPE_CHECKING

from oryxenai.agents.shared.contracts import ModelClient

if TYPE_CHECKING:
    from oryxenai.core.settings import ModelProfile


def build_adapter(profile: ModelProfile) -> ModelClient:
    """Build the correct provider adapter for the given profile.

    Provider selection is based on `profile.provider`. Adding a new
    provider means adding an entry to the registry below.
    """
    provider = profile.provider.lower()

    if provider == "opencode_go":
        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        return OpenCodeGoAdapter(profile)

    if provider in ("openai", "openai_compatible", "openai_responses"):
        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        # OpenAI and OpenAI-compatible endpoints use the same chat/completions
        # protocol. The OpenCodeGo adapter is generic enough for any
        # OpenAI-compatible provider — just set base_url and model.
        return OpenCodeGoAdapter(profile)

    raise ValueError(
        f"Unknown provider '{profile.provider}'. "
        f"Supported providers: opencode_go, openai, openai_compatible, openai_responses"
    )


def can_build(profile: ModelProfile) -> bool:
    """Check whether an adapter can be built without actually building it."""
    provider = profile.provider.lower()
    return provider in {
        "opencode_go",
        "openai",
        "openai_compatible",
        "openai_responses",
    }
