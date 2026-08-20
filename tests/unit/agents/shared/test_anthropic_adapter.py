import httpx
import pytest
from pydantic import BaseModel

from oryxenai.agents.shared.providers.anthropic import AnthropicAdapter
from oryxenai.agents.shared.providers.errors import ProviderConfigError
from oryxenai.agents.shared.providers.factory import build_adapter, can_build
from oryxenai.core.settings import ModelProfile


class _Output(BaseModel):
    answer: str


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
    body = requests[0].content.decode("utf-8")
    assert '"model":"claude-sonnet-5"' in body
    assert "JSON Schema" in body
    assert "<untrusted_input" in body


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
