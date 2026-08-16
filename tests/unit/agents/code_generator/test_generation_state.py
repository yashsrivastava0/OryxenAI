from __future__ import annotations

import pytest

from oryxenai.agents.code_generator.state import GenerationStateError, can_transition, transition


def test_generation_state_allows_source_pipeline() -> None:
    assert can_transition("acquired", "queued")
    assert transition("queued", "generating_foundation") == "generating_foundation"
    assert transition("generating_foundation", "generating_routes") == "generating_routes"
    assert transition("generating_routes", "integrating") == "integrating"
    assert transition("integrating", "source_ready") == "source_ready"


def test_generation_state_rejects_preview_phase_transition() -> None:
    with pytest.raises(GenerationStateError, match="Invalid"):
        transition("source_ready", "ready")
