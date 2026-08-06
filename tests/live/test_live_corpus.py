"""Live full-corpus evaluation (Section 27 / 26.5).

Runs the complete golden corpus with all model-dependent assertions against
the real OpenCode Go provider. Opt-in: -m live + RUN_LIVE_DISCOVERY=1.
"""

from __future__ import annotations

import os

import pytest

from oryxenai.agents.discovery.schemas import DiscoveryAnalysisResult
from oryxenai.agents.shared.providers.opencode_go import OpenCodeGoAdapter
from oryxenai.core.settings import get_settings
from tests.eval.test_discovery_eval import SCENARIOS, AssertionRunner


def _live_enabled() -> bool:
    if os.environ.get("RUN_LIVE_DISCOVERY") != "1":
        return False
    # get_settings() exports .env secrets into os.environ (documented
    # contract), so the adapter can resolve the key.
    get_settings()
    return bool(os.environ.get("OPENCODE_GO_API_KEY"))


pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not _live_enabled(),
        reason="Live corpus evaluation requires RUN_LIVE_DISCOVERY=1 and a provider key",
    ),
]


async def _run_live(adapter: OpenCodeGoAdapter, intake: dict) -> dict:
    from oryxenai.agents.discovery.prompt_builder import build_instructions

    source_packet = {
        "main_prompt": intake.get("main_prompt", ""),
        "resume_text": intake.get("resume_text", ""),
        "links": intake.get("links", []),
    }
    system, task, _version, _manifest = build_instructions(
        "prepare_questions",
        source_packet,
        config={"max_questions": 8, "max_featured_projects": 5},
        output_language=intake.get("output_language", "en"),
    )
    result = await adapter.generate_structured(
        operation="prepare_questions",
        instructions=f"{system}\n\n{task}",
        input_payload={"synthetic": True},
        output_model=DiscoveryAnalysisResult,
    )
    return result.parsed_output


@pytest.mark.parametrize(
    "scenario",
    [pytest.param(s, id=s["name"]) for s in SCENARIOS],
)
async def test_live_corpus_full_assertions(scenario: dict) -> None:
    """Full assertion set (incl. model-dependent) against the real provider."""
    settings = get_settings()
    profile = settings.models.get_profile("discovery")
    assert profile is not None
    adapter = OpenCodeGoAdapter(profile)
    try:
        output = await _run_live(adapter, scenario["input"])
    finally:
        if adapter._client is not None:
            await adapter._client.close()

    runner = AssertionRunner(scenario, live=True)
    failures = runner.check(output)
    assert not failures, failures
