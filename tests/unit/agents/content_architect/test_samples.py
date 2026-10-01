"""The checked-in sample pairs must satisfy the live validators and readiness gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oryxenai.agents.content_architect.agent import _approval_readiness_errors
from oryxenai.agents.content_architect.schemas import ContentArchitectOutput
from oryxenai.agents.content_architect.validators import validate_stage_output
from oryxenai.agents.discovery.schemas import DiscoveryDossier

_SAMPLES = Path(__file__).resolve().parents[4] / "src/oryxenai/agents/content_architect/samples"
_NAMES = ["01_strong_profile", "02_sparse_no_metrics", "03_nda_confidential"]


def _load(name: str, kind: str) -> dict:
    return json.loads((_SAMPLES / f"{name}_{kind}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", _NAMES)
def test_sample_input_carries_a_valid_dossier(name):
    sample = _load(name, "input")
    dossier = DiscoveryDossier.model_validate(sample["intake"]["dossier"])
    assert dossier.facts


@pytest.mark.parametrize("name", _NAMES)
def test_sample_output_passes_validation_and_readiness(name):
    output = _load(name, "output")
    dossier = _load(name, "input")["intake"]["dossier"]

    assert validate_stage_output(output, "plan_content").is_valid
    ContentArchitectOutput.model_validate(output)
    assert (
        _approval_readiness_errors(
            page_content=output["page_content"],
            claim_grounding=output["claim_grounding"],
            coverage_ledger=output["coverage_ledger"],
            dossier=dossier,
        )
        == []
    )
    assert len(output["page_content"]["systems_practice"]["pillars"]) == 4


def test_nda_sample_withholds_the_restricted_claim():
    output = _load("03_nda_confidential", "output")
    blocked = [c for c in output["claim_grounding"] if c["publication_status"] == "blocked"]
    assert blocked
    assert all(c["field_paths"] == [] for c in blocked)
    assert "18%" not in json.dumps(output["page_content"])
