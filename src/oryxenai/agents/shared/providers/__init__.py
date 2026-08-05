"""Provider adapters for model clients.

Each provider adapter implements the ModelClient protocol. Use
`build_adapter()` to create the correct adapter from a ModelProfile.

Adding a new provider:
  1. Create a new module in this package (e.g. `anthropic.py`).
  2. Extend `BaseProviderAdapter` and implement the abstract methods.
  3. Add the provider name to `_ADAPTER_REGISTRY` in `factory.py`.
  4. Add the new profile section to `config/models.toml`.
"""

from oryxenai.agents.shared.providers.base import BaseProviderAdapter
from oryxenai.agents.shared.providers.errors import (
    ProviderAuthError,
    ProviderBadResponseError,
    ProviderConfigError,
    ProviderConnectionError,
    ProviderContentFilterError,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
    ProviderServerError,
    ProviderTimeoutError,
)
from oryxenai.agents.shared.providers.factory import build_adapter, can_build
from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

__all__ = [
    "BaseProviderAdapter",
    "OpenCodeGoAdapter",
    "ProviderAuthError",
    "ProviderBadResponseError",
    "ProviderConfigError",
    "ProviderConnectionError",
    "ProviderContentFilterError",
    "ProviderError",
    "ProviderInvalidRequestError",
    "ProviderRateLimitError",
    "ProviderServerError",
    "ProviderTimeoutError",
    "build_adapter",
    "can_build",
]
