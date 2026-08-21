import json

import httpx
import pytest
from pydantic import BaseModel

from oryxenai.agents.shared.providers.anthropic import AnthropicAdapter
from oryxenai.agents.shared.providers.capabilities import ModelCapabilities
from oryxenai.agents.shared.providers.errors import ProviderConfigError
from oryxenai.agents.shared.providers.factory import build_adapter, can_build
from oryxenai.core.settings import ModelProfile


class _Output(BaseModel):
    answer: str


class _MapOutput(BaseModel):
    values: dict[str, str]


class _NullableOutput(BaseModel):
    value: str | None = None


def _profile(**overrides: object) -> ModelProfile:
    values: dict[str, object] = {
        "provider": "anthropic",
        "model": "claude-sonnet-5",
        "base_url": "https://api.anthropic.com/v1",
        "api_key_env": "TEST_ANTHROPIC_API_KEY",
        "timeout_seconds": 10,
        "max_retries": 0,
        "max_output_tokens": 4096,
        "reasoning_effort": "medium",
        "capabilities": ModelCapabilities(
            json_object_mode=True,
            json_schema_mode=True,
            thinking_mode=True,
            reasoning_content=False,
            temperature_control=False,
            usage_metadata=True,
            response_id=True,
            context_cache_metadata=False,
            supports_store_parameter=True,
            uses_max_completion_tokens=True,
            structured_output_mode="native_json_schema",
            thinking_strategy="default",
            effort_parameter="output_config_effort",
        ),
    }
    values.update(overrides)
    return ModelProfile(**values)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_anthropic_messages_adapter_sends_schema_and_parses_text(monkeypatch):
    monkeypatch.setenv("TEST_ANTHROPIC_API_KEY", "sk-ant-test")
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = request.read()
        assert body
        return httpx.Response(
            200,
            json={
                "id": "msg_test",
                "model": "claude-sonnet-5",
                "content": [
                    {"type": "thinking", "thinking": "internal"},
                    {"type": "text", "text": '{"answer":"grounded"}'},
                ],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 12, "output_tokens": 8},
            },
            request=request,
        )

    adapter = AnthropicAdapter(_profile())
    adapter._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.anthropic.com/v1",
        headers={"x-api-key": "sk-ant-test", "anthropic-version": "2023-06-01"},
    )
    result = await adapter.generate_structured(
        operation="code_generator.planner",
        instructions="Create the plan.",
        input_payload={"untrusted": "portfolio data"},
        output_model=_Output,
        system_prompt="You are the planner.",
        strict_schema=True,
    )
    await adapter.aclose()

    assert result.parsed_output == {"answer": "grounded"}
    assert result.response_id == "msg_test"
    assert result.usage["total_tokens"] == 20
    assert len(requests) == 1
    body = httpx.Request(
        "POST", "https://api.anthropic.com/v1/messages", content=requests[0].content
    ).read()
    payload = json.loads(body)
    assert payload["model"] == "claude-sonnet-5"
    assert "thinking" not in payload
    assert payload["output_config"]["effort"] == "medium"
    assert payload["output_config"]["format"]["type"] == "json_schema"
    assert "JSON Schema" not in payload["system"]
    assert "<untrusted_input" in json.dumps(payload["messages"])


@pytest.mark.asyncio
async def test_anthropic_adapter_falls_back_for_typed_mapping_schema(monkeypatch):
    monkeypatch.setenv("TEST_ANTHROPIC_API_KEY", "sk-ant-test")
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "msg_map",
                "model": "claude-sonnet-5",
                "content": [{"type": "text", "text": '{"values":{"accent":"#fff"}}'}],
                "stop_reason": "end_turn",
            },
            request=request,
        )

    adapter = AnthropicAdapter(_profile())
    adapter._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.anthropic.com/v1",
        headers={"x-api-key": "sk-ant-test", "anthropic-version": "2023-06-01"},
    )
    result = await adapter.generate_structured(
        operation="code_generator.planner",
        instructions="Create the plan.",
        input_payload={"untrusted": "portfolio data"},
        output_model=_MapOutput,
        system_prompt="You are the planner.",
        strict_schema=True,
    )
    await adapter.aclose()

    assert result.parsed_output == {"values": {"accent": "#fff"}}
    payload = json.loads(requests[0].content)
    assert "format" not in payload["output_config"]
    assert "JSON Schema" in payload["system"]


@pytest.mark.asyncio
async def test_anthropic_adapter_falls_back_for_composed_schema(monkeypatch):
    monkeypatch.setenv("TEST_ANTHROPIC_API_KEY", "sk-ant-test")
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "msg_nullable",
                "model": "claude-sonnet-5",
                "content": [{"type": "text", "text": '{"value":"grounded"}'}],
                "stop_reason": "end_turn",
            },
            request=request,
        )

    adapter = AnthropicAdapter(_profile())
    adapter._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.anthropic.com/v1",
        headers={"x-api-key": "sk-ant-test", "anthropic-version": "2023-06-01"},
    )
    result = await adapter.generate_structured(
        operation="code_generator.generation",
        instructions="Generate the result.",
        input_payload={"untrusted": "portfolio data"},
        output_model=_NullableOutput,
        system_prompt="You are the generator.",
        strict_schema=True,
    )
    await adapter.aclose()

    assert result.parsed_output == {"value": "grounded"}
    payload = json.loads(requests[0].content)
    assert "format" not in payload["output_config"]
    assert "JSON Schema" in payload["system"]


def test_anthropic_manual_thinking_is_only_sent_when_declared() -> None:
    profile = _profile(
        capabilities=ModelCapabilities(
            json_object_mode=True,
            json_schema_mode=True,
            thinking_mode=True,
            reasoning_content=False,
            temperature_control=False,
            usage_metadata=True,
            response_id=True,
            context_cache_metadata=False,
            supports_store_parameter=True,
            uses_max_completion_tokens=True,
            structured_output_mode="native_json_schema",
            thinking_strategy="manual_budget",
            effort_parameter="none",
        )
    )
    body = AnthropicAdapter(profile)._request_body(
        system_prompt="",
        messages=[{"role": "user", "content": "test"}],
        request_params=None,
    )

    assert body["thinking"] == {"type": "enabled", "budget_tokens": 3072}


def test_provider_invalid_request_keeps_safe_provider_details() -> None:
    from oryxenai.agents.shared.providers.errors import map_http_error

    error = map_http_error(
        400,
        {
            "error": {
                "type": "invalid_request_error",
                "param": "thinking",
                "message": "thinking.type.enabled is not supported",
            },
            "request_id": "req_test",
        },
    )

    assert error.code == "PROVIDER_INVALID_REQUEST_ERROR"
    assert error.details["provider_error_type"] == "invalid_request_error"
    assert error.details["provider_parameter"] == "thinking"
    assert error.details["provider_request_id"] == "req_test"


@pytest.mark.asyncio
async def test_anthropic_adapter_requires_key(monkeypatch):
    monkeypatch.delenv("MISSING_ANTHROPIC_KEY", raising=False)
    adapter = AnthropicAdapter(_profile(api_key_env="MISSING_ANTHROPIC_KEY"))

    with pytest.raises(ProviderConfigError, match="MISSING_ANTHROPIC_KEY"):
        await adapter.generate_structured(
            operation="test",
            instructions="test",
            input_payload={},
            output_model=_Output,
        )


def test_factory_supports_anthropic_without_initializing_credentials():
    profile = _profile()

    assert can_build(profile)
    assert isinstance(build_adapter(profile), AnthropicAdapter)
