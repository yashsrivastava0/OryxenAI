"""Generic OpenAI-protocol provider adapter.

Despite the module name (kept for import stability), this adapter serves
every provider registered under "opencode_go", "openai", "openai_compatible",
and "openai_responses" in providers/factory.py — any endpoint that speaks
the OpenAI chat/completions protocol with structured JSON output. Provider
differences (base URL, whether temperature is configurable, whether the
endpoint wants max_tokens or max_completion_tokens, ...) are expressed as
per-profile ModelCapabilities in config/models.toml, not as branches on
provider name here.

The adapter never imports OpenAI-specific types in its public API.
All responses are normalized to StructuredModelResult.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from oryxenai.agents.shared.providers.base import BaseProviderAdapter
from oryxenai.agents.shared.providers.capabilities import DEFAULT_OPENCODE_GO, ModelCapabilities
from oryxenai.agents.shared.providers.errors import (
    ModelEmptyOutputError,
    ModelJsonInvalidError,
    ModelOutputTruncatedError,
    ProviderBadResponseError,
    ProviderConfigError,
    map_http_error,
)
from oryxenai.core.logging import get_logger

if TYPE_CHECKING:
    from oryxenai.core.settings import ModelProfile

logger = get_logger("oryxenai.agents.providers.opencode_go")

_OPENCODE_GO_BASE_URL = "https://opencode.ai/zen/go/v1"


class OpenCodeGoAdapter(BaseProviderAdapter):
    """Model client adapter for any OpenAI-protocol endpoint.

    Talks to an OpenAI-compatible chat/completions endpoint using the
    standard `openai` SDK (AsyncOpenAI). `base_url` and capabilities come
    from the profile, so the same class serves OpenCode Go, real OpenAI,
    and any other OpenAI-compatible provider.
    """

    def __init__(self, profile: ModelProfile) -> None:
        super().__init__(profile)
        self._client: Any = None
        self._capabilities: ModelCapabilities = profile.capabilities or DEFAULT_OPENCODE_GO

    # ── BaseProviderAdapter implementation ──────────────────────────────

    async def complete(
        self,
        system_prompt: str,
        task_prompt: str,
        request_params: dict[str, Any] | None = None,
    ) -> str:
        self._ensure_initialized()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": task_prompt})

        token_kwarg = (
            "max_completion_tokens"
            if self._capabilities.uses_max_completion_tokens
            else "max_tokens"
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._profile.model,
                messages=messages,
                timeout=self._profile.timeout_seconds,
                **{token_kwarg: self._profile.max_output_tokens},
                **self._build_extra_params(request_params),
            )
        except Exception as exc:
            raise self._map_sdk_error(exc) from exc

        return response.choices[0].message.content or ""

    async def _generate_structured_impl(
        self,
        *,
        operation: str,
        instructions: str,
        input_payload: Mapping[str, object],
        output_model: type[BaseModel],
        request_id: str,
        system_prompt: str | None = None,
    ) -> Any:
        from oryxenai.agents.discovery.schemas import StructuredModelResult

        self._ensure_initialized()

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": instructions})

        extra = self._build_extra_params({})
        if self._capabilities.temperature_control:
            extra.setdefault("temperature", 0.0)

        token_kwarg = (
            "max_completion_tokens"
            if self._capabilities.uses_max_completion_tokens
            else "max_tokens"
        )

        call_start = time.monotonic()

        try:
            response = await self._client.chat.completions.create(
                model=self._profile.model,
                messages=messages,
                response_format={"type": "json_object"},
                timeout=self._profile.timeout_seconds,
                **{token_kwarg: self._profile.max_output_tokens},
                **self._structured_call_kwargs(),
                **extra,
            )
        except Exception as exc:
            raise self._map_sdk_error(exc) from exc

        latency_ms = (time.monotonic() - call_start) * 1000.0

        message = response.choices[0].message
        # reasoning_content must never be captured, persisted, or logged.
        # Only the final content is read; the reasoning channel is discarded.
        raw = message.content or ""
        finish_reason = response.choices[0].finish_reason or "unknown"

        if not raw.strip():
            raise ModelEmptyOutputError(
                f"Model returned {'empty' if not raw else 'whitespace-only'} content"
            )
        if finish_reason == "length":
            raise ModelOutputTruncatedError(
                "Model output was truncated by the provider (finish_reason=length)"
            )

        try:
            parsed_output: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ModelJsonInvalidError(f"Model returned invalid JSON: {exc!s}") from exc

        if not isinstance(parsed_output, dict):
            raise ProviderBadResponseError(
                f"Model returned non-object JSON: {type(parsed_output).__name__}"
            )

        usage_dict: dict[str, Any] = {}
        if response.usage:
            usage_dict = {
                "prompt_tokens": response.usage.prompt_tokens or 0,
                "completion_tokens": response.usage.completion_tokens or 0,
                "total_tokens": response.usage.total_tokens or 0,
            }

        return StructuredModelResult(
            parsed_output=parsed_output,
            response_id=response.id or "",
            model=response.model or self._profile.model,
            usage=usage_dict,
            finish_reason=finish_reason,
            latency_ms=latency_ms,
        )

    def _resolve_api_key(self) -> str:
        env_var = self._profile.api_key_env
        if not env_var:
            raise ProviderConfigError(
                f"Provider '{self.provider_name}' has no api_key_env configured. "
                "Set api_key_env in config/models.toml to the environment variable "
                "that holds the API key."
            )
        key = self._resolve_key_from_env(env_var)
        return self._require_key(key, env_var, self.provider_name)

    def _validate_profile(self) -> None:
        if not self._profile.model:
            raise ProviderConfigError(
                f"Provider '{self.provider_name}' has no model configured. "
                "Set the 'model' field in config/models.toml."
            )
        if not self._profile.api_key_env:
            raise ProviderConfigError(
                f"Provider '{self.provider_name}' has no api_key_env configured."
            )

    # ── Client factory ──────────────────────────────────────────────────

    def _ensure_initialized(self) -> None:
        super()._ensure_initialized()
        if self._client is None:
            self._client = self._build_client()

    def _build_client(self) -> Any:
        import openai

        base_url = self._profile.base_url
        if not base_url and self._profile.provider == "opencode_go":
            base_url = _OPENCODE_GO_BASE_URL
        return openai.AsyncOpenAI(
            api_key=self._api_key,
            base_url=base_url or None,
            max_retries=self._profile.max_retries,
            timeout=self._profile.timeout_seconds,
        )

    # ── Helpers ─────────────────────────────────────────────────────────

    def _build_extra_params(self, request_params: dict[str, Any] | None) -> dict[str, Any]:
        merged = dict(self._profile.request_params)
        if request_params:
            merged.update(request_params)
        if self._profile.reasoning_effort and self._capabilities.thinking_mode:
            # A flat top-level param on Chat Completions for reasoning-family
            # models (confirmed live: none/low/medium/high/xhigh) — NOT the
            # nested {"reasoning": {"effort": ...}} shape, which the SDK
            # rejects outright as an unexpected keyword argument.
            merged.setdefault("reasoning_effort", self._profile.reasoning_effort)
        return merged

    def _structured_call_kwargs(self) -> dict[str, Any]:
        """Extra kwargs for the structured chat/completions call."""
        kwargs: dict[str, Any] = {}
        if not self._profile.store and self._capabilities.supports_store_parameter:
            kwargs["store"] = False
        return kwargs

    def _map_sdk_error(self, exc: Exception) -> Exception:
        import openai

        # The SDK rejected a parameter (e.g. unsupported 'reasoning' key).
        # This is a capability mismatch, not a transient network failure.
        if isinstance(exc, TypeError) and "unexpected keyword argument" in str(exc):
            from oryxenai.agents.shared.providers.errors import ModelCapabilityUnsupportedError

            return ModelCapabilityUnsupportedError(str(exc))

        if isinstance(exc, openai.AuthenticationError):
            status = getattr(exc, "status_code", 401)
            return map_http_error(status, _safe_body(exc))
        if isinstance(exc, openai.RateLimitError):
            return map_http_error(429, _safe_body(exc))
        if isinstance(exc, openai.APITimeoutError):
            from oryxenai.agents.shared.providers.errors import ProviderTimeoutError

            return ProviderTimeoutError(str(exc))
        if isinstance(exc, openai.APIConnectionError):
            from oryxenai.agents.shared.providers.errors import ProviderConnectionError

            return ProviderConnectionError(str(exc))
        if isinstance(exc, openai.APIStatusError):
            return map_http_error(exc.status_code, _safe_body(exc))
        if isinstance(exc, openai.BadRequestError):
            return map_http_error(400, _safe_body(exc))
        if isinstance(exc, openai.APIError):
            return map_http_error(500, _safe_body(exc))

        from oryxenai.agents.shared.providers.errors import ProviderError

        return ProviderError(
            f"OpenCode Go adapter error: {exc!s}",
            code="PROVIDER_UNKNOWN_ERROR",
            retryable=True,
        )


def _safe_body(exc: Any) -> dict[str, Any] | None:
    try:
        body = getattr(exc, "body", None)
        if body is None:
            return None
        if isinstance(body, dict):
            return dict(body)
        if isinstance(body, (str, bytes)):
            parsed = json.loads(body if isinstance(body, str) else body.decode())
            if isinstance(parsed, dict):
                return dict(parsed)
        return None
    except Exception:
        return None
