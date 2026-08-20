from types import SimpleNamespace

import pytest

from oryxenai.agents.code_generator.core import provider_preflight
from oryxenai.core.settings import Settings


@pytest.mark.asyncio
async def test_provider_preflight_uses_fixed_input_and_closes_client(monkeypatch):
    settings = Settings()
    calls: list[dict[str, object]] = []

    class FakeClient:
        async def generate_structured(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                parsed_output={"ok": True, "protocol": "code-generator-preflight-v1"}
            )

        async def aclose(self):
            calls.append({"closed": True})

    provider_preflight.clear_provider_preflight_cache()
    monkeypatch.setattr(provider_preflight, "resolve_api_key", lambda _profile: "configured")
    monkeypatch.setattr(provider_preflight, "build_provider_client", lambda *_args: FakeClient())

    result = await provider_preflight.run_provider_preflight(
        settings,
        [settings.code_generator_development.planner_profile],
    )

    request = calls[0]
    assert request["operation"] == "code_generator.provider_preflight"
    assert request["input_payload"] == {"protocol": "code-generator-preflight-v1"}
    assert "portfolio data" in str(request["instructions"])
    assert "portfolio" not in str(request["input_payload"])
    assert calls[-1] == {"closed": True}
    assert result["private_context_sent"] is False
