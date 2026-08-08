"""Unit tests for Discovery state machine."""

from __future__ import annotations

import pytest

from oryxenai.agents.discovery.schemas import (
    DiscoveryQuestion,
    DiscoveryState,
    DiscoveryStatus,
    OperationMode,
    StructuredProfile,
)
from oryxenai.agents.discovery.state import (
    InvalidTransitionError,
    apply_answers_in_progress,
    apply_approval,
    apply_brief_review,
    apply_brief_running,
    apply_needs_attention,
    apply_questions_ready,
    apply_questions_running,
    apply_start,
    is_valid_transition,
)


class TestValidTransitions:
    def test_not_started_to_questions_queued(self):
        assert is_valid_transition(DiscoveryStatus.NOT_STARTED, DiscoveryStatus.QUESTIONS_QUEUED)

    def test_questions_queued_to_running(self):
        assert is_valid_transition(
            DiscoveryStatus.QUESTIONS_QUEUED, DiscoveryStatus.QUESTIONS_RUNNING
        )

    def test_questions_running_to_ready(self):
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

    def test_questions_ready_can_restart_operation_a(self):
        assert is_valid_transition(
            DiscoveryStatus.QUESTIONS_READY, DiscoveryStatus.QUESTIONS_QUEUED
        )

    def test_answers_in_progress_to_brief_running(self):
        assert is_valid_transition(
            DiscoveryStatus.ANSWERS_IN_PROGRESS, DiscoveryStatus.BRIEF_RUNNING
        )

    def test_brief_running_to_review(self):
        assert is_valid_transition(DiscoveryStatus.BRIEF_RUNNING, DiscoveryStatus.BRIEF_REVIEW)

    def test_brief_running_to_needs_attention(self):
        assert is_valid_transition(DiscoveryStatus.BRIEF_RUNNING, DiscoveryStatus.NEEDS_ATTENTION)

    def test_brief_review_to_approved(self):
        assert is_valid_transition(DiscoveryStatus.BRIEF_REVIEW, DiscoveryStatus.APPROVED)

    def test_brief_review_to_brief_running_for_revision(self):
        assert is_valid_transition(DiscoveryStatus.BRIEF_REVIEW, DiscoveryStatus.BRIEF_RUNNING)

    def test_needs_attention_retries(self):
        assert is_valid_transition(
            DiscoveryStatus.NEEDS_ATTENTION, DiscoveryStatus.QUESTIONS_QUEUED
        )
        assert is_valid_transition(
            DiscoveryStatus.NEEDS_ATTENTION, DiscoveryStatus.ANSWERS_IN_PROGRESS
        )
        assert is_valid_transition(DiscoveryStatus.NEEDS_ATTENTION, DiscoveryStatus.BRIEF_RUNNING)


class TestInvalidTransitions:
    def test_not_started_to_approved(self):
        assert not is_valid_transition(DiscoveryStatus.NOT_STARTED, DiscoveryStatus.APPROVED)

    def test_approved_has_no_outgoing(self):
        for target in DiscoveryStatus:
            assert not is_valid_transition(DiscoveryStatus.APPROVED, target)

    def test_running_directly_to_approved(self):
        assert not is_valid_transition(DiscoveryStatus.QUESTIONS_RUNNING, DiscoveryStatus.APPROVED)

    def test_brief_review_to_questions_running(self):
        assert not is_valid_transition(
            DiscoveryStatus.BRIEF_REVIEW, DiscoveryStatus.QUESTIONS_RUNNING
        )

    def test_self_transition_rejected(self):
        assert not is_valid_transition(DiscoveryStatus.BRIEF_REVIEW, DiscoveryStatus.BRIEF_REVIEW)


class TestFlowTransitions:
    def test_start_records_started_at(self):
        state = apply_start(DiscoveryState())
        assert state.status == DiscoveryStatus.QUESTIONS_QUEUED
        assert state.started_at is not None

    def test_start_preserves_existing_started_at(self):
        started = apply_start(DiscoveryState())
        first = started.started_at
        state = DiscoveryState(status=DiscoveryStatus.NEEDS_ATTENTION, started_at=first)
        again = apply_start(state)
        assert again.started_at == first

    def test_retry_from_needs_attention_resets(self):
        state = DiscoveryState(status=DiscoveryStatus.NEEDS_ATTENTION)
        next_state = apply_start(state)
        assert next_state.status == DiscoveryStatus.QUESTIONS_QUEUED
        assert next_state.latest_error is None

    def test_questions_ready_can_restart(self):
        state = DiscoveryState(status=DiscoveryStatus.QUESTIONS_READY)
        next_state = apply_start(state)
        assert next_state.status == DiscoveryStatus.QUESTIONS_QUEUED

    def test_questions_ready_stores_items(self):
        question = DiscoveryQuestion(id="q1", text="What is your role?")
        state = apply_questions_ready(
            DiscoveryState(status=DiscoveryStatus.QUESTIONS_RUNNING),
            items=[question],
            version="discovery.understand_and_question.v3",
            run_id="run-1",
            mode=OperationMode.ASK_QUESTIONS,
            assistant_message="Please answer.",
            memory_update={},
        )
        assert state.status == DiscoveryStatus.QUESTIONS_READY
        assert state.operation_a.version == "discovery.understand_and_question.v3"
        assert state.operation_a.run_id == "run-1"
        assert state.operation_a.items[0].id == "q1"
        assert state.operation_a.mode == OperationMode.ASK_QUESTIONS

    def test_questions_ready_persists_mode_and_memory(self):
        question = DiscoveryQuestion(id="q1", text="Q")
        state = apply_questions_ready(
            DiscoveryState(status=DiscoveryStatus.QUESTIONS_RUNNING, memory={"old": "kept"}),
            items=[question],
            version="v2",
            run_id="run-1",
            mode=OperationMode.NEEDS_DETAILS,
            assistant_message="Share more details.",
            memory_update={"intent_summary": "backend role", "open_items": ["no metrics"]},
        )
        assert state.operation_a.mode == OperationMode.NEEDS_DETAILS
        assert state.operation_a.assistant_message == "Share more details."
        assert state.operation_a.memory_update["intent_summary"] == "backend role"
        assert state.memory["old"] == "kept"
        assert state.memory["intent_summary"] == "backend role"
        assert state.memory["open_items"] == ["no metrics"]

    def test_brief_running_stores_run_and_job(self):
        state = apply_brief_running(
            DiscoveryState(status=DiscoveryStatus.ANSWERS_IN_PROGRESS), "run-2", "job-2"
        )
        assert state.status == DiscoveryStatus.BRIEF_RUNNING
        assert state.brief.run_id == "run-2"
        assert state.brief.job_id == "job-2"

    def test_brief_review_stores_markdown(self):
        state = apply_brief_review(
            DiscoveryState(status=DiscoveryStatus.BRIEF_RUNNING),
            version="discovery.build_or_revise_brief.v4",
            run_id="run-2",
            title="Portfolio Discovery Brief — Test",
            markdown="# Portfolio Discovery Brief\n\nContent.",
            open_items=["no metrics"],
            memory_update={"intent_summary": "backend"},
            user_summary="A short friendly summary.",
            profile={"name": "Test User", "skills": ["Python"]},
        )
        assert state.status == DiscoveryStatus.BRIEF_REVIEW
        assert state.brief.title == "Portfolio Discovery Brief — Test"
        assert state.brief.markdown.startswith("# Portfolio Discovery Brief")
        assert state.brief.open_items == ["no metrics"]
        assert state.brief.version == "discovery.build_or_revise_brief.v4"
        assert state.brief.run_id == "run-2"
        assert state.brief.user_summary == "A short friendly summary."
        assert state.brief.profile.name == "Test User"
        assert state.brief.profile.skills == ["Python"]

    def test_brief_review_defaults_user_summary_and_profile_when_omitted(self):
        # Locks in backward compatibility: callers that don't know about the
        # new fields yet still get a valid, empty StructuredProfile.
        state = apply_brief_review(
            DiscoveryState(status=DiscoveryStatus.BRIEF_RUNNING),
            version="v3",
            run_id="run-3",
            title="t",
            markdown="x",
            open_items=[],
            memory_update={},
        )
        assert state.brief.user_summary == ""
        assert state.brief.profile == StructuredProfile()

    def test_brief_review_merges_memory(self):
        state = apply_brief_review(
            DiscoveryState(status=DiscoveryStatus.BRIEF_RUNNING, memory={"old": "kept"}),
            version="v2",
            run_id="r",
            title="t",
            markdown="x",
            open_items=[],
            memory_update={"privacy_choices": ["email only"]},
        )
        assert state.memory["old"] == "kept"
        assert state.memory["privacy_choices"] == ["email only"]

    def test_brief_review_records_revision_request(self):
        state = apply_brief_review(
            DiscoveryState(status=DiscoveryStatus.BRIEF_RUNNING),
            version="v2",
            run_id="r",
            title="t",
            markdown="x",
            open_items=[],
            memory_update={},
            revision_request="Lead with QueueGuard",
        )
        assert state.brief.revision_request == "Lead with QueueGuard"

    def test_approval_snapshot(self):
        state = apply_brief_review(
            DiscoveryState(status=DiscoveryStatus.BRIEF_RUNNING),
            version="v2",
            run_id="r",
            title="t",
            markdown="content",
            open_items=[],
            memory_update={},
        )
        approved = apply_approval(state, "abc123")
        assert approved.status == DiscoveryStatus.APPROVED
        assert approved.brief.approved is not None
        assert approved.brief.approved.brief_hash == "abc123"

    def test_needs_attention_records_error(self):
        state = apply_needs_attention(
            DiscoveryState(status=DiscoveryStatus.QUESTIONS_RUNNING),
            {"code": "MODEL_TIMEOUT", "message": "Timed out", "retryable": True},
        )
        assert state.status == DiscoveryStatus.NEEDS_ATTENTION
        assert state.latest_error["code"] == "MODEL_TIMEOUT"


class TestInvalidTransitionErrors:
    def test_questions_running_from_wrong_state(self):
        with pytest.raises(InvalidTransitionError):
            apply_questions_running(DiscoveryState(status=DiscoveryStatus.APPROVED))

    def test_brief_review_from_wrong_state(self):
        with pytest.raises(InvalidTransitionError):
            apply_brief_review(
                DiscoveryState(status=DiscoveryStatus.QUESTIONS_READY),
                version="v2",
                run_id="r",
                title="t",
                markdown="x",
                open_items=[],
                memory_update={},
            )

    def test_approval_from_wrong_state(self):
        with pytest.raises(InvalidTransitionError):
            apply_approval(DiscoveryState(status=DiscoveryStatus.QUESTIONS_READY), "h")

    def test_answers_in_progress_from_wrong_state(self):
        with pytest.raises(InvalidTransitionError):
            apply_answers_in_progress(DiscoveryState(status=DiscoveryStatus.NOT_STARTED))

    def test_needs_attention_rejected_from_terminal(self):
        with pytest.raises(InvalidTransitionError):
            apply_needs_attention(
                DiscoveryState(status=DiscoveryStatus.APPROVED),
                {"code": "X", "message": "y"},
            )
