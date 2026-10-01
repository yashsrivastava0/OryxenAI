"""Provider adapters and errors, exported lazily to avoid import cycles."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MODULES = {
    "AnthropicAdapter": "anthropic",
    "BaseProviderAdapter": "base",
    "OpenAICompatibleAdapter": "opencode_go",
    "OpenCodeGoAdapter": "opencode_go",
    "ProviderAuthError": "errors",
    "ProviderBadResponseError": "errors",
    "ProviderConfigError": "errors",
    "ProviderConnectionError": "errors",
    "ProviderContentFilterError": "errors",
    "ProviderCreditError": "errors",
    "ProviderError": "errors",
    "ProviderInvalidRequestError": "errors",
    "ProviderRateLimitError": "errors",
    "ProviderServerError": "errors",
    "ProviderTimeoutError": "errors",
    "SchemaCompatibilityError": "schema_compatibility",
    "build_adapter": "factory",
    "can_build": "factory",
    "ensure_schema_compatible": "schema_compatibility",
    "schema_compatibility_issues": "schema_compatibility",
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    module = _EXPORT_MODULES.get(name)
    if module is None:
        raise AttributeError(name)
    return getattr(import_module(f"{__name__}.{module}"), name)
