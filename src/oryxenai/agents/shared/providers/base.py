"""Base provider adapter — shared logic for all model provider integrations.

New providers extend BaseProviderAdapter and implement the ModelClient
protocol. Provider-specific code (SDK imports, request formatting, error
mapping) lives in the subclass. Agent code depends only on the ModelClient
protocol, never on any provider name or implementation.
"""

from __future__ import annotations

import hashlib
import os
import time
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from oryxenai.agents.shared.contracts import ModelClient
from oryxenai.agents.shared.providers.errors import ProviderConfigError
from oryxenai.core.logging import get_logger
from oryxenai.core.settings import ModelProfile

logger = get_logger("oryxenai.agents.providers")


class BaseProviderAdapter(ModelClient, ABC):
    """Abstract base for all provider adapters.

    Subclasses implement the transport layer and structured-output parsing.
    This base handles key resolution, tracing IDs, and timing.
    """

    def __init__(self, profile: ModelProfile) -> None:
        self._profile = profile
        self._api_key: str | None = None
        self._initialized = False

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def profile(self) -> ModelProfile:
        return self._profile

    @property
    def provider_name(self) -> str:
        return self._profile.provider

    # ── Public API ──────────────────────────────────────────────────────

    async def complete(
        self,
        system_prompt: str,
        task_prompt: str,
        request_params: dict[str, Any] | None = None,
    ) -> str:
        """Plain text completion. Default throws NotImplementedError."""
        raise NotImplementedError(f"{self.provider_name} does not support plain completion")

    async def generate_structured(
        self,
        *,
        operation: str,
        instructions: str,
        input_payload: Mapping[str, object],
        output_model: type[BaseModel],
        model_profile: Any = None,
        request_context: Any = None,
    ) -> Any:
        """Structured output via the provider's native mechanism."""
        self._ensure_initialized()
        request_id = self._make_trace_id(operation)
        start_ms = time.monotonic() * 1000

        try:
            result = await self._generate_structured_impl(
                operation=operation,
                instructions=instructions,
                input_payload=input_payload,
                output_model=output_model,
                request_id=request_id,
            )
            elapsed_ms = (time.monotonic() * 1000) - start_ms
            logger.info(
                "provider=%s model=%s operation=%s trace=%s elapsed_ms=%.0f",
                self.provider_name,
                self._profile.model,
                operation,
                request_id,
                elapsed_ms,
            )
            return result
        except Exception:
            elapsed_ms = (time.monotonic() * 1000) - start_ms
            logger.warning(
                "provider=%s model=%s operation=%s trace=%s elapsed_ms=%.0f FAILED",
                self.provider_name,
                self._profile.model,
                operation,
                request_id,
                elapsed_ms,
            )
            raise

    # ── Subclass contract ───────────────────────────────────────────────

    @abstractmethod
    async def _generate_structured_impl(
        self,
        *,
        operation: str,
        instructions: str,
        input_payload: Mapping[str, object],
        output_model: type[BaseModel],
        request_id: str,
    ) -> Any:
        """Provider-specific structured generation. Must be implemented."""
        ...

    @abstractmethod
    def _resolve_api_key(self) -> str:
        """Resolve and validate the API key. Raises ProviderConfigError."""
        ...

    @abstractmethod
    def _validate_profile(self) -> None:
        """Validate profile configuration. Raises ProviderConfigError."""
        ...

    # ── Helpers ─────────────────────────────────────────────────────────

    def _ensure_initialized(self) -> None:
        """Lazy-initialize: resolve key and validate on first call."""
        if self._initialized:
            return
        self._validate_profile()
        self._api_key = self._resolve_api_key()
        self._initialized = True
        logger.debug("provider=%s model=%s initialized", self.provider_name, self._profile.model)

    def _make_trace_id(self, operation: str) -> str:
        """Deterministic trace ID that does not expose the API key."""
        seed = f"{self.provider_name}:{self._profile.model}:{operation}:{time.monotonic()}"
        return hashlib.sha256(seed.encode()).hexdigest()[:12]

    @staticmethod
    def _resolve_key_from_env(env_var: str) -> str:
        """Resolve an API key from an environment variable.

        Returns empty string if unset. Never logs the value.
        """
        if not env_var:
            return ""
        return os.environ.get(env_var, "")

    @staticmethod
    def _require_key(key: str, env_var: str, provider: str) -> str:
        """Validate that a key is non-empty. Raises ProviderConfigError if missing."""
        if not key:
            raise ProviderConfigError(
                f"API key environment variable '{env_var}' is not set or is empty. "
                f"Provider '{provider}' cannot authenticate."
            )
        return key
