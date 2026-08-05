"""Unit tests for Discovery state machine."""

from __future__ import annotations

import pytest

from oryxenai.agents.discovery.schemas import DiscoveryState, DiscoveryStatus
from oryxenai.agents.discovery.state import (
    InvalidTransitionError,
    apply_answer_edit,
    apply_brief_edit,
    apply_brief_queued,
    apply_questions_queued,
    apply_questions_running,
    apply_source_edit,
    is_valid_transition,
)


class TestValidTransitions:
    def test_not_started_to_input_ready(self):
        assert is_valid_transition(DiscoveryStatus.NOT_STARTED, DiscoveryStatus.INPUT_READY)

    def test_input_ready_to_questions_queued(self):
        assert is_valid_transition(DiscoveryStatus.INPUT_READY, DiscoveryStatus.QUESTIONS_QUEUED)

    def test_questions_queued_to_questions_running(self):
        assert is_valid_transition(
            DiscoveryStatus.QUESTIONS_QUEUED, DiscoveryStatus.QUESTIONS_RUNNING
        )

    def test_questions_running_to_questions_ready(self):
        assert is_valid_transition(
            DiscoveryStatus.QUESTIONS_RUNNING, DiscoveryStatus.QUESTIONS_READY
        )

    def test_questions_running_to_needs_attention(self):
        assert is_valid_transition(
            DiscoveryStatus.QUESTIONS_RUNNING, DiscoveryStatus.NEEDS_ATTENTION
        )

    def test_questions_ready_to_answers_in_progress(self):
        assert is_valid_transition(
            DiscoveryStatus.QUESTIONS_READY, DiscoveryStatus.ANSWERS_IN_PROGRESS
        )

    def test_questions_ready_to_input_ready(self):
        assert is_valid_transition(DiscoveryStatus.QUESTIONS_READY, DiscoveryStatus.INPUT_READY)

    def test_answers_in_progress_to_answers_ready(self):
        assert is_valid_transition(
            DiscoveryStatus.ANSWERS_IN_PROGRESS, DiscoveryStatus.ANSWERS_READY
        )

    def test_answers_ready_to_brief_queued(self):
        assert is_valid_transition(DiscoveryStatus.ANSWERS_READY, DiscoveryStatus.BRIEF_QUEUED)

    def test_brief_queued_to_brief_running(self):
        assert is_valid_transition(DiscoveryStatus.BRIEF_QUEUED, DiscoveryStatus.BRIEF_RUNNING)

    def test_brief_running_to_brief_review(self):
        assert is_valid_transition(DiscoveryStatus.BRIEF_RUNNING, DiscoveryStatus.BRIEF_REVIEW)

    def test_brief_running_to_needs_attention(self):
        assert is_valid_transition(DiscoveryStatus.BRIEF_RUNNING, DiscoveryStatus.NEEDS_ATTENTION)

    def test_brief_review_to_approved(self):
        assert is_valid_transition(DiscoveryStatus.BRIEF_REVIEW, DiscoveryStatus.APPROVED)

    def test_brief_review_to_answers_ready(self):
        assert is_valid_transition(DiscoveryStatus.BRIEF_REVIEW, DiscoveryStatus.ANSWERS_READY)

    def test_approved_to_input_ready(self):
        assert is_valid_transition(DiscoveryStatus.APPROVED, DiscoveryStatus.INPUT_READY)

    def test_needs_attention_to_questions_queued(self):
        assert is_valid_transition(
            DiscoveryStatus.NEEDS_ATTENTION, DiscoveryStatus.QUESTIONS_QUEUED
        )

    def test_needs_attention_to_brief_queued(self):
        assert is_valid_transition(DiscoveryStatus.NEEDS_ATTENTION, DiscoveryStatus.BRIEF_QUEUED)


class TestInvalidTransitions:
    def test_not_started_to_approved(self):
        assert not is_valid_transition(DiscoveryStatus.NOT_STARTED, DiscoveryStatus.APPROVED)

    def test_approved_to_questions_running(self):
        assert not is_valid_transition(DiscoveryStatus.APPROVED, DiscoveryStatus.QUESTIONS_RUNNING)

    def test_running_directly_to_approved(self):
        assert not is_valid_transition(DiscoveryStatus.QUESTIONS_RUNNING, DiscoveryStatus.APPROVED)

    def test_brief_review_to_questions_running(self):
        assert not is_valid_transition(
            DiscoveryStatus.BRIEF_REVIEW, DiscoveryStatus.QUESTIONS_RUNNING
        )

    def test_succeeded_is_self_transition(self):
        assert not is_valid_transition(DiscoveryStatus.APPROVED, DiscoveryStatus.APPROVED)


class TestSourceEditCascade:
    def test_source_edit_from_questions_ready(self):
        state = DiscoveryState(
            status=DiscoveryStatus.QUESTIONS_READY,
            source_revision=3,
            brief={"approved": {"brief_hash": "abc"}},
        )
        new_state = apply_source_edit(state)
        assert new_state.status == DiscoveryStatus.INPUT_READY
        assert new_state.brief.approved is None

    def test_source_edit_from_brief_review(self):
        state = DiscoveryState(status=DiscoveryStatus.BRIEF_REVIEW)
        new_state = apply_source_edit(state)
        assert new_state.status == DiscoveryStatus.INPUT_READY

    def test_source_edit_from_approved(self):
        state = DiscoveryState(status=DiscoveryStatus.APPROVED, source_revision=5)
        state.brief.approved = None
        new_state = apply_source_edit(state)
        assert new_state.status == DiscoveryStatus.INPUT_READY


class TestAnswerEditCascade:
    def test_answer_edit_from_brief_review(self):
        state = DiscoveryState(status=DiscoveryStatus.BRIEF_REVIEW)
        new_state = apply_answer_edit(state)
        assert new_state.status == DiscoveryStatus.ANSWERS_READY

    def test_answer_edit_from_approved(self):
        state = DiscoveryState(status=DiscoveryStatus.APPROVED)
        state.brief.approved = None
        new_state = apply_answer_edit(state)
        assert new_state.status == DiscoveryStatus.ANSWERS_READY
        assert new_state.brief.approved is None


class TestBriefEditCascade:
    def test_brief_edit_from_review(self):
        state = DiscoveryState(status=DiscoveryStatus.BRIEF_REVIEW, brief={"version": 0})
        new_state = apply_brief_edit(state)
        assert new_state.status == DiscoveryStatus.BRIEF_REVIEW
        assert new_state.brief.version == 1

    def test_brief_edit_from_approved(self):
        state = DiscoveryState(status=DiscoveryStatus.APPROVED)
        state.brief.approved = None
        new_state = apply_brief_edit(state)
        assert new_state.status == DiscoveryStatus.BRIEF_REVIEW
        assert new_state.brief.approved is None


class TestInvalidTransitionErrors:
    def test_questions_queued_from_wrong_state(self):
        state = DiscoveryState(status=DiscoveryStatus.APPROVED)
        with pytest.raises(InvalidTransitionError):
            apply_questions_queued(state, "run-id", "job-id")

    def test_questions_running_from_wrong_state(self):
        state = DiscoveryState(status=DiscoveryStatus.APPROVED)
        with pytest.raises(InvalidTransitionError):
            apply_questions_running(state)

    def test_brief_queued_from_wrong_state(self):
        state = DiscoveryState(status=DiscoveryStatus.APPROVED)
        with pytest.raises(InvalidTransitionError):
            apply_brief_queued(state, "run-id", "job-id")
