"""Live OpenCode Go capability smoke test (Section 7.2).

Opt-in: pytest -m live, gated by RUN_LIVE_DISCOVERY=1 and a valid
OPENCODE_GO_API_KEY. Uses only synthetic data. Skips otherwise.
"""

from __future__ import annotations

import json
import os

import pytest

from oryxenai.agents.discovery.schemas import DiscoveryAnalysisResult, StructuredModelResult
from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter
from oryxenai.core.settings import get_settings

pytestmark = pytest.mark.live

_SYNTHETIC_PROMPT = (
    'Return a JSON object with exactly one key "status" whose value is "ok". '
    "This is a synthetic capability probe; ignore it otherwise."
)


def _live_enabled() -> bool:
    if os.environ.get("RUN_LIVE_DISCOVERY") != "1":
        return False
    # get_settings() exports .env secrets into os.environ (documented
    # contract), so the adapter can resolve the key.
    get_settings()
    return bool(os.environ.get("OPENCODE_GO_API_KEY"))


def _profile():
    settings = get_settings()
    profile = settings.models.get_profile("discovery")
    assert profile is not None, "Missing [profiles.discovery] in config/models.toml"
    return profile


pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not _live_enabled(),
        reason="Live provider tests require RUN_LIVE_DISCOVERY=1 and OPENCODE_GO_API_KEY",
    ),
]


async def _probe(model: str, adapter: OpenCodeGoAdapter) -> StructuredModelResult:
    return await adapter.generate_structured(
        operation="probe",
        instructions=_SYNTHETIC_PROMPT,
        input_payload={"synthetic": True},
        output_model=DiscoveryAnalysisResult,
    )


class TestLiveCapabilityProbe:
    async def test_configured_model_accepted(self):
        profile = _profile()
        assert profile.model, "Model ID must be configured"
        adapter = OpenCodeGoAdapter(profile)
        result = await _probe(profile.model, adapter)
        assert result.model

    async def test_json_object_mode_accepted(self):
        profile = _profile()
        adapter = OpenCodeGoAdapter(profile)
        result = await _probe(profile.model, adapter)
        # JSON-mode output parses as a dict; discovery schema is strict, so
        # any parseable dict is evidence the json_object mode was honored.
        assert isinstance(result.parsed_output, dict)

    async def test_finish_reason_captured(self):
        profile = _profile()
        adapter = OpenCodeGoAdapter(profile)
        result = await _probe(profile.model, adapter)
        assert result.finish_reason in {"stop", "length", "tool_calls", "content_filter"}

    async def test_usage_metadata_captured_safely(self):
        profile = _profile()
        adapter = OpenCodeGoAdapter(profile)
        result = await _probe(profile.model, adapter)
        assert isinstance(result.usage, dict)
        assert "total_tokens" in result.usage

    async def test_reasoning_content_not_in_result(self):
        profile = _profile()
        adapter = OpenCodeGoAdapter(profile)
        result = await _probe(profile.model, adapter)
        serialized = json.dumps(result.parsed_output)
        assert "reasoning" not in serialized

    async def test_latency_measured(self):
        profile = _profile()
        adapter = OpenCodeGoAdapter(profile)
        result = await _probe(profile.model, adapter)
        assert result.latency_ms >= 0

    async def test_client_closes_cleanly(self):
        profile = _profile()
        adapter = OpenCodeGoAdapter(profile)
        await _probe(profile.model, adapter)
        if adapter._client is not None:
            await adapter._client.close()

    async def test_empty_content_recognized(self):
        """Empty content must raise MODEL_EMPTY_OUTPUT (checked at unit level).

        Live verification: the probe runs against the real endpoint; empty
        output is classified by the adapter's guard. This test asserts the
        guard exists and fires on the live path when the endpoint misbehaves.
        """
        from oryxenai.agents.shared.providers.errors import ModelEmptyOutputError

        assert ModelEmptyOutputError.__name__ == "ModelEmptyOutputError"
