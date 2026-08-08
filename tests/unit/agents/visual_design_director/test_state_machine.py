"""Unit tests for the Visual Design Director state machine."""

from __future__ import annotations

import pytest

from oryxenai.agents.visual_design_director.schemas import (
    AssetBrief,
    PageVisualDirection,
    ResourceCandidate,
    VisualDesignDirectorIntake,
    VisualDesignDirectorPreferences,
    VisualDesignDirectorSourceRef,
    VisualDesignDirectorState,
    VisualDesignDirectorStatus,
)
from oryxenai.agents.visual_design_director.state import (
    InvalidTransitionError,
    apply_approval,
    apply_build_result,
    apply_build_running,
    apply_needs_attention,
    apply_revision_requested,
    apply_start,
    is_valid_transition,
)


def _source_ref() -> VisualDesignDirectorSourceRef:
    return VisualDesignDirectorSourceRef(
        content_architect_content_hash="hash1", content_architect_session_revision=1
    )


def _build_result_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "version": "visual_design_director.establish_visual_language.v1",
        "run_id": "run-1",
        "user_summary": "A restrained, evidence-first look.",
        "meta": {},
        "source_refs": {},
        "visual_language": {"creative_thesis": "x"},
        "shared_visual_systems": {},
        "navigation_direction": {},
        "motion_system": {},
        "interaction_system": {},
        "pages": [PageVisualDirection(route_id="home", path="/")],
        "asset_briefs": [],
        "resource_candidates": [],
        "accessibility_and_performance": {},
        "must_preserve": [],
        "must_not_fabricate": [],
        "conflicts": [],
        "warnings": [],
        "compiler_handoff": {},
        "stages_run": ["establish_visual_language"],
        "memory_update": {},
    }
    kwargs.update(overrides)
    return kwargs


class TestValidTransitions:
    def test_not_started_to_build_running(self):
        assert is_valid_transition(
            VisualDesignDirectorStatus.NOT_STARTED, VisualDesignDirectorStatus.BUILD_RUNNING
        )

    def test_build_running_to_design_review(self):
        assert is_valid_transition(
            VisualDesignDirectorStatus.BUILD_RUNNING, VisualDesignDirectorStatus.DESIGN_REVIEW
        )

    def test_build_running_to_needs_attention(self):
        assert is_valid_transition(
            VisualDesignDirectorStatus.BUILD_RUNNING, VisualDesignDirectorStatus.NEEDS_ATTENTION
        )

    def test_design_review_to_approved(self):
        assert is_valid_transition(
            VisualDesignDirectorStatus.DESIGN_REVIEW, VisualDesignDirectorStatus.APPROVED
        )

    def test_design_review_to_build_running_for_revision(self):
        assert is_valid_transition(
            VisualDesignDirectorStatus.DESIGN_REVIEW, VisualDesignDirectorStatus.BUILD_RUNNING
        )

    def test_needs_attention_retries(self):
        assert is_valid_transition(
            VisualDesignDirectorStatus.NEEDS_ATTENTION, VisualDesignDirectorStatus.BUILD_RUNNING
        )


class TestInvalidTransitions:
    def test_not_started_to_approved(self):
        assert not is_valid_transition(
            VisualDesignDirectorStatus.NOT_STARTED, VisualDesignDirectorStatus.APPROVED
        )

    def test_approved_has_no_outgoing(self):
        for target in VisualDesignDirectorStatus:
            assert not is_valid_transition(VisualDesignDirectorStatus.APPROVED, target)

    def test_self_transition_rejected(self):
        assert not is_valid_transition(
            VisualDesignDirectorStatus.DESIGN_REVIEW, VisualDesignDirectorStatus.DESIGN_REVIEW
        )


class TestFlowTransitions:
    def test_start_records_started_at_and_snapshot(self):
        state = apply_start(
            VisualDesignDirectorState(),
            source_ref=_source_ref(),
            intake=VisualDesignDirectorIntake(presentation_mode="single_page"),
            preferences=VisualDesignDirectorPreferences(visual_tone="restrained"),
        )
        assert state.status == VisualDesignDirectorStatus.BUILD_RUNNING
        assert state.started_at is not None
        assert state.source_ref.content_architect_content_hash == "hash1"
        assert state.intake.presentation_mode == "single_page"
        assert state.preferences.visual_tone == "restrained"

    def test_start_preserves_existing_started_at(self):
        started = apply_start(
            VisualDesignDirectorState(),
            source_ref=_source_ref(),
            intake=VisualDesignDirectorIntake(),
            preferences=VisualDesignDirectorPreferences(),
        )
        first = started.started_at
        needs_attention = VisualDesignDirectorState(
            status=VisualDesignDirectorStatus.NEEDS_ATTENTION, started_at=first
        )
        again = apply_start(
            needs_attention,
            source_ref=_source_ref(),
            intake=VisualDesignDirectorIntake(),
            preferences=VisualDesignDirectorPreferences(),
        )
        assert again.started_at == first

    def test_retry_from_needs_attention_clears_error(self):
        state = VisualDesignDirectorState(
            status=VisualDesignDirectorStatus.NEEDS_ATTENTION,
            latest_error={"code": "X", "message": "y"},
        )
        next_state = apply_start(
            state,
            source_ref=_source_ref(),
            intake=VisualDesignDirectorIntake(),
            preferences=VisualDesignDirectorPreferences(),
        )
        assert next_state.status == VisualDesignDirectorStatus.BUILD_RUNNING
        assert next_state.latest_error is None

    def test_build_running_is_idempotent_reentry(self):
        state = VisualDesignDirectorState(status=VisualDesignDirectorStatus.BUILD_RUNNING)
        next_state = apply_build_running(state, "run-1", "job-1")
        assert next_state.status == VisualDesignDirectorStatus.BUILD_RUNNING
        assert next_state.run_id == "run-1"
        assert next_state.job_id == "job-1"

    def test_build_running_recovers_from_needs_attention(self):
        state = VisualDesignDirectorState(status=VisualDesignDirectorStatus.NEEDS_ATTENTION)
        next_state = apply_build_running(state, "run-1", "job-1")
        assert next_state.status == VisualDesignDirectorStatus.BUILD_RUNNING

    def test_revision_requested_moves_to_build_running(self):
        state = VisualDesignDirectorState(status=VisualDesignDirectorStatus.DESIGN_REVIEW)
        next_state = apply_revision_requested(state, "run-2", "job-2", "Use a lighter palette")
        assert next_state.status == VisualDesignDirectorStatus.BUILD_RUNNING
        assert next_state.run_id == "run-2"
        assert next_state.revision_request == "Use a lighter palette"

    def test_build_result_stores_direction_and_merges_memory(self):
        state = VisualDesignDirectorState(
            status=VisualDesignDirectorStatus.BUILD_RUNNING, memory={"old": "kept"}
        )
        result = apply_build_result(
            state,
            **_build_result_kwargs(
                asset_briefs=[AssetBrief(asset_id="a1")],
                resource_candidates=[ResourceCandidate(resource_id="r1")],
                memory_update={"new": "value"},
            ),
        )
        assert result.status == VisualDesignDirectorStatus.DESIGN_REVIEW
        assert result.pages[0].route_id == "home"
        assert result.asset_briefs[0].asset_id == "a1"
        assert result.resource_candidates[0].resource_id == "r1"
        assert result.memory["old"] == "kept"
        assert result.memory["new"] == "value"
        assert result.latest_error is None

    def test_approval_snapshot(self):
        state = VisualDesignDirectorState(status=VisualDesignDirectorStatus.DESIGN_REVIEW)
        approved = apply_approval(state, "abc123")
        assert approved.status == VisualDesignDirectorStatus.APPROVED
        assert approved.approved is not None
        assert approved.approved.visual_direction_hash == "abc123"

    def test_needs_attention_records_error(self):
        state = apply_needs_attention(
            VisualDesignDirectorState(status=VisualDesignDirectorStatus.BUILD_RUNNING),
            {"code": "MODEL_TIMEOUT", "message": "Timed out", "retryable": True},
        )
        assert state.status == VisualDesignDirectorStatus.NEEDS_ATTENTION
        assert state.latest_error["code"] == "MODEL_TIMEOUT"


class TestInvalidTransitionErrors:
    def test_build_result_from_wrong_state(self):
        with pytest.raises(InvalidTransitionError):
            apply_build_result(
                VisualDesignDirectorState(status=VisualDesignDirectorStatus.NOT_STARTED),
                **_build_result_kwargs(),
            )

    def test_approval_from_wrong_state(self):
        with pytest.raises(InvalidTransitionError):
            apply_approval(
                VisualDesignDirectorState(status=VisualDesignDirectorStatus.BUILD_RUNNING), "h"
            )

    def test_needs_attention_rejected_from_terminal(self):
        with pytest.raises(InvalidTransitionError):
            apply_needs_attention(
                VisualDesignDirectorState(status=VisualDesignDirectorStatus.APPROVED),
                {"code": "X", "message": "y"},
            )

    def test_revision_requested_from_wrong_state(self):
        with pytest.raises(InvalidTransitionError):
            apply_revision_requested(
                VisualDesignDirectorState(status=VisualDesignDirectorStatus.APPROVED),
                "r",
                "j",
                "revise it",
            )
