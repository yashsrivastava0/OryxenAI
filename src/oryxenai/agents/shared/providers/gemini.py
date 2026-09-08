"""Native Gemini ``generateContent`` adapter.

The adapter deliberately owns Gemini's wire format, usage normalization, and
error redaction.  The rest of the application only sees ``ModelClient`` and
``StructuredModelResult``.  Google Free Tier credentials are never included
in logs or durable metadata.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel

from oryxenai.agents.shared.model_cache import estimate_model_cost
from oryxenai.agents.shared.providers.base import BaseProviderAdapter
from oryxenai.agents.shared.providers.capabilities import ModelCapabilities
from oryxenai.agents.shared.providers.errors import (
    ModelEmptyOutputError,
    ModelJsonInvalidError,
    ModelOutputTruncatedError,
    ProviderBadResponseError,
    ProviderConfigError,
    ProviderConnectionError,
    ProviderError,
    ProviderTimeoutError,
    map_http_error,
)

if TYPE_CHECKING:
    from oryxenai.core.settings import ModelProfile

_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def _schema_for_gemini(output_model: type[BaseModel]) -> dict[str, Any]:
    """Return the conservative JSON-schema subset accepted by Gemini.

    The initial free-tier profiles use JSON MIME mode and do not send this
    schema by default.  This helper is retained for explicitly qualified
    native-schema profiles and strips Pydantic-only metadata.
    """

    raw = json.loads(json.dumps(output_model.model_json_schema()))

    def clean(node: Any) -> Any:
        if isinstance(node, dict):
            result: dict[str, Any] = {}
            for key in ("type", "format", "description", "enum", "items", "properties", "required"):
                if key in node:
                    result[key] = clean(node[key])
            if result.get("type") == "object" and "properties" in result:
                result.setdefault("required", list(result["properties"].keys()))
            return result
        if isinstance(node, list):
            return [clean(item) for item in node]
        return node

    return cast(dict[str, Any], clean(raw))


class GeminiAdapter(BaseProviderAdapter):
    """Direct async HTTP adapter for the Gemini REST API."""

    def __init__(self, profile: ModelProfile) -> None:
        super().__init__(profile)
        self._client: httpx.AsyncClient | None = None
        self._capabilities = profile.capabilities or ModelCapabilities(
            json_object_mode=True,
            json_schema_mode=False,
            thinking_mode=False,
            reasoning_content=False,
            temperature_control=True,
            usage_metadata=True,
            response_id=False,
            context_cache_metadata=False,
            supports_store_parameter=False,
            uses_max_completion_tokens=False,
            structured_output_mode="json_object",
            thinking_strategy="disabled",
            effort_parameter="none",
        )

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def complete(
        self,
        system_prompt: str,
        task_prompt: str,
        request_params: dict[str, Any] | None = None,
    ) -> str:
        result = await self._request(
            operation="complete",
            system_prompt=system_prompt,
            task_prompt=task_prompt,
            output_model=None,
            strict_schema=False,
            request_params=request_params,
        )
        return result[0]

    async def _generate_structured_impl(
        self,
        *,
        operation: str,
        instructions: str,
        input_payload: Mapping[str, object],
        output_model: type[BaseModel],
        request_id: str,
        system_prompt: str | None = None,
        strict_schema: bool = False,
        request_context: Any = None,
    ) -> Any:
        del request_id
        raw, response, usage, latency_ms = await self._request(
            operation=operation,
            system_prompt=system_prompt or "",
            task_prompt=instructions + "\n\n" + self._serialize_input(operation, input_payload),
            output_model=output_model,
            strict_schema=strict_schema,
            request_params=request_context if isinstance(request_context, Mapping) else None,
        )
        if not raw.strip():
            error: ProviderError = ModelEmptyOutputError("Gemini returned empty content")
            _annotate_gemini_error(error, usage, response)
            raise error
        finish_reason = self._finish_reason(response)
        if finish_reason in {"MAX_TOKENS", "LENGTH"}:
            error = ModelOutputTruncatedError("Gemini output was truncated by the provider")
            _annotate_gemini_error(error, usage, response)
            raise error
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            error = ModelJsonInvalidError("Gemini returned invalid JSON")
            _annotate_gemini_error(error, usage, response)
            raise error from exc
        if not isinstance(parsed, dict):
            error = ProviderBadResponseError("Gemini returned non-object JSON")
            _annotate_gemini_error(error, usage, response)
            raise error

        from oryxenai.agents.discovery.schemas import StructuredModelResult

        estimated_cost = estimate_model_cost(usage, getattr(self._profile, "pricing", None))
        telemetry: dict[str, Any] = {
            "provider_request_id": str(
                response.get("_provider_request_id") or response.get("responseId", "") or ""
            ),
            "input_characters": len((system_prompt or "") + instructions),
            "output_characters": len(raw),
        }
        if estimated_cost is not None:
            telemetry["estimated_cost"] = estimated_cost
            telemetry["cost_unit"] = str(
                getattr(getattr(self._profile, "pricing", None), "unit", "") or ""
            )
        return StructuredModelResult(
            parsed_output=parsed,
            response_id=str(response.get("responseId", "") or "") or None,
            model=str(response.get("modelVersion", "") or self._profile.model),
            usage=usage,
            finish_reason=finish_reason,
            latency_ms=latency_ms,
            telemetry=telemetry,
        )

    async def _request(
        self,
        *,
        operation: str,
        system_prompt: str,
        task_prompt: str,
        output_model: type[BaseModel] | None,
        strict_schema: bool,
        request_params: Mapping[str, Any] | None,
    ) -> tuple[str, dict[str, Any], dict[str, Any], float]:
        self._ensure_initialized()
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._profile.timeout_seconds)
        base_url = self._base_url()
        endpoint = urljoin(
            base_url.rstrip("/") + "/", f"models/{self._profile.model}:generateContent"
        )
        contents = [{"role": "user", "parts": [{"text": task_prompt}]}]
        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "responseMimeType": "application/json"
                if output_model is not None
                else "text/plain",
                "maxOutputTokens": int(self._profile.max_output_tokens),
            },
        }
        if system_prompt:
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        if output_model is not None and strict_schema and self._capabilities.json_schema_mode:
            body["generationConfig"]["responseSchema"] = _schema_for_gemini(output_model)
        # Only provider-neutral generation parameters explicitly declared in
        # profile.request_params are forwarded.  Routing metadata is never a
        # wire parameter.
        for key, value in (self._profile.request_params or {}).items():
            if key not in {"responseMimeType", "responseSchema", "temperature", "topP", "topK"}:
                continue
            body["generationConfig"][key] = value
        raw_params = request_params if isinstance(request_params, Mapping) else {}
        token_limit, timeout_seconds = self._request_limits(raw_params)
        body["generationConfig"]["maxOutputTokens"] = token_limit
        for key in ("temperature", "topP", "topK"):
            if key in raw_params and isinstance(raw_params[key], (int, float)):
                body["generationConfig"][key] = raw_params[key]
        # Gemini thinking is opt-in and provider-specific. Never forward the
        # OpenAI ``reasoning_effort`` field as a Gemini wire parameter.
        thinking_config = raw_params.get("thinkingConfig")
        if self._capabilities.thinking_mode and isinstance(thinking_config, Mapping):
            body["generationConfig"]["thinkingConfig"] = dict(thinking_config)

        started = time.monotonic()
        try:
            response = await self._client.post(
                endpoint,
                headers={"x-goog-api-key": self._api_key or "", "content-type": "application/json"},
                json=body,
                timeout=timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Gemini request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderConnectionError("Could not connect to Gemini") from exc
        latency_ms = (time.monotonic() - started) * 1000.0
        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = None
            error = map_http_error(
                response.status_code, payload if isinstance(payload, dict) else None
            )
            if isinstance(getattr(error, "details", None), dict):
                request_id = response.headers.get("x-request-id") or response.headers.get(
                    "x-goog-request-id"
                )
                if request_id:
                    error.details["provider_request_id"] = request_id
            raise error
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderBadResponseError("Gemini returned a non-JSON response") from exc
        if not isinstance(payload, dict):
            raise ProviderBadResponseError("Gemini returned an invalid response envelope")
        provider_request_id = response.headers.get("x-request-id") or response.headers.get(
            "x-goog-request-id"
        )
        if provider_request_id:
            payload["_provider_request_id"] = provider_request_id
        text_parts: list[str] = []
        for candidate in payload.get("candidates", []) or []:
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content")
            if not isinstance(content, dict):
                continue
            for part in content.get("parts", []) or []:
                if (
                    isinstance(part, dict)
                    and isinstance(part.get("text"), str)
                    and not part.get("thought")
                ):
                    text_parts.append(part["text"])
        raw = "".join(text_parts)
        usage_metadata = payload.get("usageMetadata", {})
        usage = self._normalize_usage(usage_metadata if isinstance(usage_metadata, dict) else {})
        return raw, payload, usage, latency_ms

    def _base_url(self) -> str:
        value = self._resolve_value_from_env(
            str(getattr(self._profile, "base_url_env", "") or ""),
            str(self._profile.base_url or _DEFAULT_BASE_URL),
        )
        return value.rstrip("/")

    def _request_limits(self, request_context: Mapping[str, Any]) -> tuple[int, float]:
        raw_tokens = request_context.get("max_output_tokens")
        try:
            requested_tokens = (
                int(raw_tokens) if raw_tokens is not None else self._profile.max_output_tokens
            )
        except (TypeError, ValueError):
            requested_tokens = self._profile.max_output_tokens
        token_limit = max(1, min(int(self._profile.max_output_tokens), requested_tokens))
        raw_timeout = request_context.get("timeout_seconds")
        try:
            timeout_seconds = (
                float(raw_timeout) if raw_timeout is not None else self._profile.timeout_seconds
            )
        except (TypeError, ValueError):
            timeout_seconds = self._profile.timeout_seconds
        return token_limit, max(1.0, timeout_seconds)

    def _resolve_api_key(self) -> str:
        env_var = self._profile.api_key_env
        if not env_var:
            raise ProviderConfigError("Gemini profile has no api_key_env configured")
        return self._require_key(self._resolve_key_from_env(env_var), env_var, self.provider_name)

    def _validate_profile(self) -> None:
        if not self._profile.model:
            raise ProviderConfigError("Gemini profile has no model configured")
        if not self._profile.api_key_env:
            raise ProviderConfigError("Gemini profile has no api_key_env configured")

    @staticmethod
    def _serialize_input(operation: str, input_payload: Mapping[str, object]) -> str:
        serialized = json.dumps(
            dict(input_payload), ensure_ascii=False, sort_keys=True, default=str
        )
        return f'<untrusted_input operation="{operation}">\n{serialized}\n</untrusted_input>'

    @staticmethod
    def _normalize_usage(raw: Mapping[str, Any]) -> dict[str, Any]:
        prompt = raw.get("promptTokenCount")
        output = raw.get("candidatesTokenCount")
        total = raw.get("totalTokenCount")
        thoughts = raw.get("thoughtsTokenCount")
        cached = raw.get("cachedContentTokenCount")
        result: dict[str, Any] = {}
        for key, value in (
            ("prompt_tokens", prompt),
            ("completion_tokens", output),
            ("total_tokens", total),
            ("reasoning_tokens", thoughts),
            ("cached_prompt_tokens", cached),
        ):
            if isinstance(value, int):
                result[key] = value
        if "prompt_tokens" in result:
            result["input_tokens"] = result["prompt_tokens"]
        if "completion_tokens" in result:
            result["output_tokens"] = result["completion_tokens"]
        return result

    @staticmethod
    def _finish_reason(response: Mapping[str, Any]) -> str:
        candidates = response.get("candidates", [])
        if candidates and isinstance(candidates[0], Mapping):
            return str(candidates[0].get("finishReason", "STOP") or "STOP")
        return "STOP"


def _annotate_gemini_error(
    error: ProviderError,
    usage: Mapping[str, Any],
    response: Mapping[str, Any],
) -> None:
    """Keep post-response usage/request identity on parse and validation errors."""

    if usage:
        error.details["usage"] = dict(usage)
    provider_request_id = str(
        response.get("_provider_request_id") or response.get("responseId") or ""
    )
    if provider_request_id:
        error.details["provider_request_id"] = provider_request_id
