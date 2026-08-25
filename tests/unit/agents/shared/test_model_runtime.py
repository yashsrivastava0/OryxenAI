from __future__ import annotations

from types import SimpleNamespace

import pytest

from oryxenai.agents.shared.model_client import MockModelClient
from oryxenai.agents.shared.model_runtime import ModelRuntime
from oryxenai.agents.shared.providers.capabilities import ModelCapabilities
from oryxenai.agents.shared.providers.errors import ProviderConfigError
from oryxenai.core.settings import ModelConfig, ModelProfile, ModelRoutingConfig


def _capabilities(**updates) -> ModelCapabilities:
    values = {
        "json_object_mode": True,
        "json_schema_mode": False,
        "thinking_mode": False,
        "reasoning_content": False,
        "temperature_control": True,
        "usage_metadata": True,
        "response_id": True,
        "context_cache_metadata": False,
        "supports_store_parameter": False,
        "uses_max_completion_tokens": False,
        "structured_output_mode": "json_object",
        "thinking_strategy": "disabled",
        "effort_parameter": "none",
    }
    values.update(updates)
    return ModelCapabilities.model_validate(values)


def _config(*, provider: str = "openai_compatible") -> ModelConfig:
    return ModelConfig(
        profiles={
            "primary": ModelProfile(
                provider=provider,
                model="configured-model",
                api_key_env="TEST_MODEL_KEY",
                capabilities=_capabilities(),
            ),
            "alternate": ModelProfile(
                provider="anthropic",
                model="configured-alternate",
                api_key_env="TEST_ALT_KEY",
                capabilities=_capabilities(),
            ),
        },
        routing=ModelRoutingConfig(
            fallback_profile="primary",
            selectable_profiles=["alternate"],
            engine_profiles={"discovery": "primary", "content_architect": "primary"},
        ),
    )


def test_runtime_rejects_unknown_override_and_unimplemented_responses_transport() -> None:
    runtime = ModelRuntime(_config())
    with pytest.raises(ProviderConfigError, match="not selectable"):
        runtime.resolve_profile_name("discovery", "unknown")

    with pytest.raises(ProviderConfigError, match="Responses transport"):
        ModelRuntime(_config(provider="openai_responses"))


def test_runtime_rejects_capability_contradictions() -> None:
    config = _config()
    config.profiles["primary"].capabilities = _capabilities(
        json_object_mode=False,
        structured_output_mode="json_object",
    )

    with pytest.raises(ProviderConfigError, match="JSON-object mode"):
        ModelRuntime(config)


@pytest.mark.asyncio
async def test_runtime_reuses_clients_caches_preflight_and_closes_once(monkeypatch) -> None:
    built: list[str] = []
    calls: list[dict[str, object]] = []
    closed: list[str] = []

    class FakeClient:
        def __init__(self, model: str) -> None:
            self.model = model

        async def generate_structured(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                parsed_output={
                    "ok": True,
                    "protocol": "pipeline-model-preflight-v1",
                },
                latency_ms=12.5,
                finish_reason="stop",
                usage={"input_tokens": 3, "output_tokens": 2},
            )

        async def aclose(self) -> None:
            closed.append(self.model)

    def build(profile):
        built.append(profile.model)
        return FakeClient(profile.model)

    monkeypatch.setattr("oryxenai.agents.shared.model_runtime.build_adapter", build)
    runtime = ModelRuntime(_config())

    assert runtime.resolve("discovery") is runtime.resolve("content_architect")
    first = await runtime.preflight(["discovery", "content_architect"])
    second = await runtime.preflight(["discovery"])

    assert built == ["configured-model"]
    assert len(calls) == 1
    assert calls[0]["input_payload"] == {"protocol": "pipeline-model-preflight-v1"}
    assert first["private_context_sent"] is False
    assert second["profiles"] == first["profiles"]

    await runtime.aclose()
    assert closed == ["configured-model"]


def test_runtime_rejects_mock_from_live_factory(monkeypatch) -> None:
    monkeypatch.setattr(
        "oryxenai.agents.shared.model_runtime.build_adapter",
        lambda _profile: MockModelClient(),
    )
    runtime = ModelRuntime(_config())

    with pytest.raises(ProviderConfigError, match="cannot use MockModelClient"):
        runtime.resolve("discovery")
