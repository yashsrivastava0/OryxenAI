"""Unit tests for the OpenCode Go provider adapter."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from oryxenai.agents.discovery.schemas import QuestionSetOutput
from oryxenai.agents.shared.providers.errors import (
    ModelJsonInvalidError,
    ProviderAuthError,
    ProviderBadResponseError,
    ProviderConfigError,
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from oryxenai.core.settings import ModelProfile


def _make_profile(**overrides: object) -> ModelProfile:
    kwargs: dict[str, object] = {
        "provider": "opencode_go",
        "model": "deepseek-v4-pro",
        "base_url": "https://opencode.ai/zen/go/v1",
        "api_key_env": "TEST_API_KEY",
        "timeout_seconds": 30,
        "max_retries": 0,
        "max_output_tokens": 4096,
    }
    kwargs.update(overrides)
    return ModelProfile(**kwargs)  # type: ignore[arg-type]


def _mock_chat_response(content: str, model: str = "deepseek-v4-pro") -> MagicMock:
    choice = MagicMock()
    choice.message.content = content
    choice.finish_reason = "stop"

    usage = MagicMock()
    usage.prompt_tokens = 100
    usage.completion_tokens = 200
    usage.total_tokens = 300

    response = MagicMock()
    response.id = "resp-123"
    response.model = model
    response.choices = [choice]
    response.usage = usage
    return response


def _make_mock_openai_client(chat_response: MagicMock | Exception) -> MagicMock:
    client = MagicMock()
    create = AsyncMock()
    if isinstance(chat_response, Exception):
        create.side_effect = chat_response
    else:
        create.return_value = chat_response
    client.chat.completions.create = create
    return client


class TestOpenCodeGoAdapterInit:
    def test_lazy_initialization_succeeds_with_valid_profile(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())
        assert adapter.provider_name == "opencode_go"

    def test_raises_config_error_when_api_key_env_not_set(self):
        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile(api_key_env=""))

        async def _run():
            await adapter.generate_structured(
                operation="test",
                instructions="test",
                input_payload={},
                output_model=QuestionSetOutput,
            )

        import asyncio

        with pytest.raises(ProviderConfigError, match="no api_key_env"):
            asyncio.run(_run())

    def test_raises_config_error_when_key_missing(self):
        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile(api_key_env="MISSING_KEY"))

        async def _run():
            await adapter.generate_structured(
                operation="test",
                instructions="test",
                input_payload={},
                output_model=QuestionSetOutput,
            )

        import asyncio

        with pytest.raises(ProviderConfigError, match="is not set or is empty"):
            asyncio.run(_run())

    def test_raises_config_error_when_model_not_set(self):
        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile(model=""))

        async def _run():
            await adapter.generate_structured(
                operation="test",
                instructions="test",
                input_payload={},
                output_model=QuestionSetOutput,
            )

        import asyncio

        with pytest.raises(ProviderConfigError, match="no model configured"):
            asyncio.run(_run())


class TestOpenCodeGoAdapterStructured:
    def test_returns_structured_result_on_success(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")

        valid_json = json.dumps(
            {
                "overall_assessment": "Test assessment",
                "normalized_profile": {},
                "fact_candidates": [],
                "conflicts": [],
                "questions": [],
                "auto_decisions": [],
                "omission_candidates": [],
                "warnings": [],
            }
        )

        mock_response = _mock_chat_response(valid_json)
        mock_client = _make_mock_openai_client(mock_response)

        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            result = asyncio.run(
                adapter.generate_structured(
                    operation="prepare_questions",
                    instructions="Test system\n\nTest task",
                    input_payload={"main_prompt": "test"},
                    output_model=QuestionSetOutput,
                )
            )

        from oryxenai.agents.discovery.schemas import StructuredModelResult

        assert isinstance(result, StructuredModelResult)
        assert result.model == "deepseek-v4-pro"
        assert result.response_id == "resp-123"
        assert result.finish_reason == "stop"
        assert result.parsed_output["overall_assessment"] == "Test assessment"
        assert result.latency_ms >= 0

    def test_uses_json_object_response_format(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")

        valid_json = json.dumps(
            {"overall_assessment": "ok", "fact_candidates": [], "questions": []}
        )
        mock_response = _mock_chat_response(valid_json)
        mock_client = _make_mock_openai_client(mock_response)

        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            asyncio.run(
                adapter.generate_structured(
                    operation="test",
                    instructions="Instructions",
                    input_payload={},
                    output_model=QuestionSetOutput,
                )
            )

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["response_format"] == {"type": "json_object"}
        assert call_kwargs["model"] == "deepseek-v4-pro"

    def test_generate_structured_includes_system_message_when_provided(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")

        mock_response = _mock_chat_response(json.dumps({"questions": []}))
        mock_client = _make_mock_openai_client(mock_response)

        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            asyncio.run(
                adapter.generate_structured(
                    operation="test",
                    system_prompt="You are trusted system instructions",
                    instructions="Untrusted task and user data",
                    input_payload={},
                    output_model=QuestionSetOutput,
                )
            )

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are trusted system instructions"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Untrusted task and user data"

    def test_generate_structured_omits_system_message_when_absent(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")

        mock_response = _mock_chat_response(json.dumps({"questions": []}))
        mock_client = _make_mock_openai_client(mock_response)

        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            asyncio.run(
                adapter.generate_structured(
                    operation="test",
                    instructions="Just the task",
                    input_payload={},
                    output_model=QuestionSetOutput,
                )
            )

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Just the task"

    def test_raises_on_invalid_json_response(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")

        mock_response = _mock_chat_response("not valid json {{{")
        mock_client = _make_mock_openai_client(mock_response)

        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            with pytest.raises(ModelJsonInvalidError, match="invalid JSON"):
                asyncio.run(
                    adapter.generate_structured(
                        operation="test",
                        instructions="test",
                        input_payload={},
                        output_model=QuestionSetOutput,
                    )
                )

    def test_raises_on_non_object_json_response(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")

        mock_response = _mock_chat_response("[1, 2, 3]")
        mock_client = _make_mock_openai_client(mock_response)

        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            with pytest.raises(ProviderBadResponseError, match="non-object JSON"):
                asyncio.run(
                    adapter.generate_structured(
                        operation="test",
                        instructions="test",
                        input_payload={},
                        output_model=QuestionSetOutput,
                    )
                )


class TestOpenCodeGoAdapterErrors:
    def test_maps_auth_error(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")

        import openai

        auth_error = openai.AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401),
            body={"error": {"message": "Invalid API key"}},
        )
        mock_client = _make_mock_openai_client(auth_error)

        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            with pytest.raises(ProviderAuthError):
                asyncio.run(
                    adapter.generate_structured(
                        operation="test",
                        instructions="test",
                        input_payload={},
                        output_model=QuestionSetOutput,
                    )
                )

    def test_maps_rate_limit_error(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")

        import openai

        rate_error = openai.RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429),
            body={"error": {"message": "Rate limited"}},
        )
        mock_client = _make_mock_openai_client(rate_error)

        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            with pytest.raises(ProviderRateLimitError):
                asyncio.run(
                    adapter.generate_structured(
                        operation="test",
                        instructions="test",
                        input_payload={},
                        output_model=QuestionSetOutput,
                    )
                )

    def test_maps_timeout_error(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")

        import openai

        timeout_error = openai.APITimeoutError(request=None)
        mock_client = _make_mock_openai_client(timeout_error)

        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            with pytest.raises(ProviderTimeoutError):
                asyncio.run(
                    adapter.generate_structured(
                        operation="test",
                        instructions="test",
                        input_payload={},
                        output_model=QuestionSetOutput,
                    )
                )

    def test_maps_connection_error(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")

        import openai

        conn_error = openai.APIConnectionError(message="Connection refused", request=None)
        mock_client = _make_mock_openai_client(conn_error)

        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            with pytest.raises(ProviderConnectionError):
                asyncio.run(
                    adapter.generate_structured(
                        operation="test",
                        instructions="test",
                        input_payload={},
                        output_model=QuestionSetOutput,
                    )
                )


class TestOpenCodeGoAdapterComplete:
    def test_complete_returns_text_response(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")

        mock_response = _mock_chat_response("Hello, world!")
        mock_client = _make_mock_openai_client(mock_response)

        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            result = asyncio.run(adapter.complete("System", "Task"))
            assert result == "Hello, world!"

    def test_complete_includes_system_message(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")

        mock_response = _mock_chat_response("ok")
        mock_client = _make_mock_openai_client(mock_response)

        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            asyncio.run(adapter.complete("You are helpful", "Answer"))

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are helpful"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Answer"


class TestProviderErrors:
    def test_provider_error_retryable_flags(self):
        from oryxenai.agents.shared.providers.errors import (
            ProviderServerError,
            map_http_error,
        )

        assert map_http_error(401).retryable is False
        assert map_http_error(429).retryable is True
        assert map_http_error(500).retryable is True
        assert map_http_error(400).retryable is False
        assert isinstance(map_http_error(500), ProviderServerError)

    def test_provider_auth_errors(self):
        from oryxenai.agents.shared.providers.errors import map_http_error

        err_401 = map_http_error(401)
        err_402 = map_http_error(402)
        assert isinstance(err_401, ProviderAuthError)
        assert isinstance(err_402, ProviderAuthError)
        assert not err_401.retryable
        assert not err_402.retryable


class TestAdapterFactory:
    def test_build_adapter_opencode_go(self):
        from oryxenai.agents.shared.providers.factory import build_adapter

        profile = _make_profile()
        with patch.dict("os.environ", {"TEST_API_KEY": "sk-test-key"}):
            adapter = build_adapter(profile)
            assert adapter.profile.provider == "opencode_go"

    def test_can_build(self):
        from oryxenai.agents.shared.providers.factory import can_build

        assert can_build(_make_profile()) is True
        assert can_build(_make_profile(provider="openai")) is True
        assert can_build(_make_profile(provider="openai_compatible")) is True
        assert can_build(_make_profile(provider="unknown_provider")) is False


class TestOpenCodeGoAdapterCapabilityHandling:
    def test_store_false_sent_when_capability_supported(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        response = _mock_chat_response('{"ok": true}')
        mock_client = _make_mock_openai_client(response)

        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile(store=False))

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            asyncio.run(
                adapter.generate_structured(
                    operation="test",
                    instructions="test",
                    input_payload={},
                    output_model=QuestionSetOutput,
                )
            )
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["store"] is False

    def test_store_omitted_when_capability_unsupported(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        response = _mock_chat_response('{"ok": true}')
        mock_client = _make_mock_openai_client(response)

        from oryxenai.agents.shared.providers.capabilities import ModelCapabilities
        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        caps = ModelCapabilities(
            json_object_mode=True,
            json_schema_mode=False,
            thinking_mode=True,
            reasoning_content=True,
            temperature_control=True,
            usage_metadata=True,
            response_id=True,
            context_cache_metadata=False,
            supports_store_parameter=False,
            uses_max_completion_tokens=False,
        )
        adapter = OpenCodeGoAdapter(_make_profile(store=False, capabilities=caps))

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            asyncio.run(
                adapter.generate_structured(
                    operation="test",
                    instructions="test",
                    input_payload={},
                    output_model=QuestionSetOutput,
                )
            )
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert "store" not in call_kwargs

    def test_thinking_param_sent_only_when_reasoning_effort_set(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        response = _mock_chat_response('{"ok": true}')
        mock_client = _make_mock_openai_client(response)

        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile(reasoning_effort="high"))

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            asyncio.run(
                adapter.generate_structured(
                    operation="test",
                    instructions="test",
                    input_payload={},
                    output_model=QuestionSetOutput,
                )
            )
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["reasoning_effort"] == "high"

        mock_client.chat.completions.create.reset_mock()
        adapter_no_thinking = OpenCodeGoAdapter(_make_profile(reasoning_effort=""))
        with patch.object(adapter_no_thinking, "_build_client", return_value=mock_client):
            import asyncio

            asyncio.run(
                adapter_no_thinking.generate_structured(
                    operation="test",
                    instructions="test",
                    input_payload={},
                    output_model=QuestionSetOutput,
                )
            )
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert "reasoning_effort" not in call_kwargs

    def test_empty_output_classified(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        response = _mock_chat_response("")
        mock_client = _make_mock_openai_client(response)

        from oryxenai.agents.shared.providers.errors import ModelEmptyOutputError
        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            with pytest.raises(ModelEmptyOutputError):
                asyncio.run(
                    adapter.generate_structured(
                        operation="test",
                        instructions="test",
                        input_payload={},
                        output_model=QuestionSetOutput,
                    )
                )

    def test_whitespace_only_output_classified(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        response = _mock_chat_response("   \n  \t  ")
        mock_client = _make_mock_openai_client(response)

        from oryxenai.agents.shared.providers.errors import ModelEmptyOutputError
        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            with pytest.raises(ModelEmptyOutputError):
                asyncio.run(
                    adapter.generate_structured(
                        operation="test",
                        instructions="test",
                        input_payload={},
                        output_model=QuestionSetOutput,
                    )
                )

    def test_truncated_output_classified(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        response = _mock_chat_response('{"parsed": true}')
        response.choices[0].finish_reason = "length"
        mock_client = _make_mock_openai_client(response)

        from oryxenai.agents.shared.providers.errors import ModelOutputTruncatedError
        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            with pytest.raises(ModelOutputTruncatedError):
                asyncio.run(
                    adapter.generate_structured(
                        operation="test",
                        instructions="test",
                        input_payload={},
                        output_model=QuestionSetOutput,
                    )
                )

    def test_reasoning_content_never_leaks_into_result(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        response = _mock_chat_response('{"parsed": true}')
        response.choices[0].message.reasoning_content = "SECRET REASONING"
        mock_client = _make_mock_openai_client(response)

        from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter

        adapter = OpenCodeGoAdapter(_make_profile())

        with patch.object(adapter, "_build_client", return_value=mock_client):
            import asyncio

            result = asyncio.run(
                adapter.generate_structured(
                    operation="test",
                    instructions="test",
                    input_payload={},
                    output_model=QuestionSetOutput,
                )
            )
        assert result.parsed_output == {"parsed": True}
        assert "reasoning" not in result.parsed_output
        serialized = result.model_dump_json()
        assert "SECRET REASONING" not in serialized
