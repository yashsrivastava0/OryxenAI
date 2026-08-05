"""Tests for deterministic Discovery application helpers."""

from __future__ import annotations

import json
from pathlib import Path

from oryxenai.agents.discovery.schemas import (
    DiscoveryAnalysisResult,
    DiscoveryBrief,
    DiscoveryState,
    DiscoveryStatus,
)
from oryxenai.agents.discovery.service import assign_stable_analysis_ids
from oryxenai.agents.discovery.state import apply_approval, apply_brief_review

_SAMPLES = (
    Path(__file__).resolve().parents[4] / "src" / "oryxenai" / "agents" / "discovery" / "samples"
)


def test_analysis_ids_are_application_assigned_and_repeatable() -> None:
    raw = json.loads((_SAMPLES / "call_a_normal_output.json").read_text(encoding="utf-8"))
    first = assign_stable_analysis_ids(DiscoveryAnalysisResult.model_validate(raw))
    second = assign_stable_analysis_ids(DiscoveryAnalysisResult.model_validate(raw))

    assert first.model_dump() == second.model_dump()
    assert all(fact.local_key.startswith("fact-") for fact in first.fact_candidates)
    assert all(question.local_key.startswith("q-") for question in first.questions)


def test_approval_keeps_an_immutable_brief_snapshot() -> None:
    state = DiscoveryState(status=DiscoveryStatus.BRIEF_RUNNING, source_revision=2)
    brief = DiscoveryBrief.model_validate(
        {
            "schema_version": 1,
            "target_role": {"title": "Backend Engineer", "fact_ids": []},
            "output_language": "en",
        }
    )
    reviewed = apply_brief_review(state, brief, "run-1")
    reviewed.brief.generated_from_source_revision = 2
    reviewed.brief.generated_from_answer_revision = 0
    approved = apply_approval(reviewed, {"session_identity": "test"})

    assert approved.brief.approved is not None
    assert approved.brief.approved_brief is not None
    assert approved.brief.approved_brief.target_role.title == "Backend Engineer"
    approved.brief.draft.target_role.title = "Changed draft"
    assert approved.brief.approved_brief.target_role.title == "Backend Engineer"
