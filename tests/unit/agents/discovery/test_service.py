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
    assert all(fact.local_key.startswith("fact-") for fact in first.facts)
    assert all(question.local_key.startswith("q-") for question in first.questions)

    # v2 reference fields are remapped deterministically too.
    for candidate in first.profile_overview.primary_role_candidates:
        assert all(fact_id.startswith("fact-") for fact_id in candidate.supporting_fact_ids)


def test_approval_keeps_an_immutable_brief_snapshot() -> None:
    state = DiscoveryState(status=DiscoveryStatus.BRIEF_RUNNING, source_revision=2)
    brief = DiscoveryBrief.model_validate(
        {
            "schema_version": 2,
            "identity_and_goal": {
                "primary_target_role": {
                    "label": "Backend Engineer",
                    "basis_fact_ids": [],
                    "decision_source": "user_answer",
                }
            },
            "output_language": "en",
        }
    )
    reviewed = apply_brief_review(state, brief, "run-1")
    reviewed.brief.generated_from_source_revision = 2
    reviewed.brief.generated_from_answer_revision = 0
    approved = apply_approval(reviewed, {"session_identity": "test"})

    assert approved.brief.approved is not None
    assert approved.brief.approved_brief is not None
    assert (
        approved.brief.approved_brief.identity_and_goal.primary_target_role.label
        == "Backend Engineer"
    )
    approved.brief.draft.identity_and_goal.primary_target_role.label = "Changed draft"
    assert (
        approved.brief.approved_brief.identity_and_goal.primary_target_role.label
        == "Backend Engineer"
    )
