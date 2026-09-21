from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from oryxenai.agents.discovery.schemas import QuestionSetOutput
from oryxenai.agents.shared.providers.errors import (
    ModelJsonInvalidError,
    ProviderRateLimitError,
    map_http_error,
)
from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter
from oryxenai.core.settings import ModelProfile


def _profile() -> ModelProfile:
    return ModelProfile(
        provider="opencode_go",
        model="configured-model",
        base_url="https://example.invalid/v1",
        api_key_env="TEST_PROVIDER_KEY",
    )


def test_gemini_style_retry_info_is_normalized_without_raw_body() -> None:
    error = map_http_error(
        429,
        {
            "error": {
                "status": "RESOURCE_EXHAUSTED",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.RetryInfo",
                        "retryDelay": "12s",
                    },
                    {
                        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                        "violations": [{"quotaMetric": "generativelanguage.googleapis.com/foo"}],
                    },
                ],
            }
        },
    )

    assert isinstance(error, ProviderRateLimitError)
    assert error.details["retry_after_seconds"] == 12.0
    assert error.details["quota_metric"].endswith("/foo")
    assert "RetryInfo" not in str(error.details)


@pytest.mark.asyncio
async def test_openai_compatible_parse_failure_retains_provider_usage() -> None:
    choice = MagicMock()
    choice.message.content = "not-json"
    choice.finish_reason = "stop"
    usage = MagicMock()
    usage.prompt_tokens = 11
    usage.completion_tokens = 7
    usage.total_tokens = 18
    response = MagicMock()
    response.id = "provider-response-1"
    response.model = "configured-model"
    response.choices = [choice]
    response.usage = usage

    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=response)
    adapter = OpenCodeGoAdapter(_profile())

    with (
        patch.dict("os.environ", {"TEST_PROVIDER_KEY": "test-key"}),
        patch.object(adapter, "_build_client", return_value=client),
        pytest.raises(ModelJsonInvalidError) as caught,
    ):
        await adapter.generate_structured(
            operation="test.operation",
            instructions="Return JSON.",
            input_payload={},
            output_model=QuestionSetOutput,
        )

    assert caught.value.details["usage"]["input_tokens"] == 11
    assert caught.value.details["usage"]["output_tokens"] == 7
    assert caught.value.details["provider_request_id"] == "provider-response-1"
