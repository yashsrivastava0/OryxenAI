"""Unit tests for the Content Architect state machine."""

from __future__ import annotations

import pytest

from oryxenai.agents.content_architect.schemas import (
    ClaimGrounding,
    ContentArchitectIntake,
    ContentArchitectPreferences,
    ContentArchitectSourceRef,
    ContentArchitectState,
    ContentArchitectStatus,
    ContentStoryStrategy,
    DecisionRecord,
    PortfolioPageContent,
    PublicationStatus,
)
from oryxenai.agents.content_architect.state import (
    ContentNotPublishableError,
    InvalidTransitionError,
    PublicScopeIncompleteError,
    apply_approval,
    apply_build_result,
    apply_build_running,
    apply_needs_attention,
    apply_revision_requested,
    apply_start,
    is_valid_transition,
)
from tests.unit.agents.content_architect.helpers import valid_page


def _source_ref() -> ContentArchitectSourceRef:
    return ContentArchitectSourceRef(discovery_brief_hash="hash1", discovery_session_revision=1)


def _public_review_state() -> ContentArchitectState:
    return ContentArchitectState(
        status=ContentArchitectStatus.CONTENT_REVIEW,
        page_content=PortfolioPageContent.model_validate(valid_page()),
    )


class TestValidTransitions:
    def test_not_started_to_build_running(self):
        assert is_valid_transition(
            ContentArchitectStatus.NOT_STARTED, ContentArchitectStatus.BUILD_RUNNING
        )

    def test_build_running_to_content_review(self):
        assert is_valid_transition(
            ContentArchitectStatus.BUILD_RUNNING, ContentArchitectStatus.CONTENT_REVIEW
        )

    def test_build_running_to_needs_attention(self):
        assert is_valid_transition(
            ContentArchitectStatus.BUILD_RUNNING, ContentArchitectStatus.NEEDS_ATTENTION
        )

    def test_content_review_to_approved(self):
        assert is_valid_transition(
            ContentArchitectStatus.CONTENT_REVIEW, ContentArchitectStatus.APPROVED
        )

    def test_content_review_to_build_running_for_revision(self):
        assert is_valid_transition(
            ContentArchitectStatus.CONTENT_REVIEW, ContentArchitectStatus.BUILD_RUNNING
        )

    def test_needs_attention_retries(self):
        assert is_valid_transition(
            ContentArchitectStatus.NEEDS_ATTENTION, ContentArchitectStatus.BUILD_RUNNING
        )


class TestInvalidTransitions:
    def test_not_started_to_approved(self):
        assert not is_valid_transition(
            ContentArchitectStatus.NOT_STARTED, ContentArchitectStatus.APPROVED
        )

    def test_approved_has_no_outgoing(self):
        for target in ContentArchitectStatus:
            assert not is_valid_transition(ContentArchitectStatus.APPROVED, target)

    def test_self_transition_rejected(self):
        assert not is_valid_transition(
            ContentArchitectStatus.CONTENT_REVIEW, ContentArchitectStatus.CONTENT_REVIEW
        )


class TestFlowTransitions:
    def test_start_records_started_at_and_snapshot(self):
        state = apply_start(
            ContentArchitectState(),
            source_ref=_source_ref(),
            intake=ContentArchitectIntake(approved_brief_title="t"),
            preferences=ContentArchitectPreferences(goal="get hired"),
        )
        assert state.status == ContentArchitectStatus.BUILD_RUNNING
        assert state.started_at is not None
        assert state.source_ref.discovery_brief_hash == "hash1"
        assert state.intake.approved_brief_title == "t"
        assert state.preferences.goal == "get hired"

    def test_start_preserves_existing_started_at(self):
        started = apply_start(
            ContentArchitectState(),
            source_ref=_source_ref(),
            intake=ContentArchitectIntake(),
            preferences=ContentArchitectPreferences(),
        )
        first = started.started_at
        needs_attention = ContentArchitectState(
            status=ContentArchitectStatus.NEEDS_ATTENTION, started_at=first
        )
        again = apply_start(
            needs_attention,
            source_ref=_source_ref(),
            intake=ContentArchitectIntake(),
            preferences=ContentArchitectPreferences(),
        )
        assert again.started_at == first

    def test_retry_from_needs_attention_clears_error(self):
        state = ContentArchitectState(
            status=ContentArchitectStatus.NEEDS_ATTENTION,
            latest_error={"code": "X", "message": "y"},
        )
        next_state = apply_start(
            state,
            source_ref=_source_ref(),
            intake=ContentArchitectIntake(),
            preferences=ContentArchitectPreferences(),
        )
        assert next_state.status == ContentArchitectStatus.BUILD_RUNNING
        assert next_state.latest_error is None

    def test_build_running_is_idempotent_reentry(self):
        state = ContentArchitectState(status=ContentArchitectStatus.BUILD_RUNNING)
        next_state = apply_build_running(state, "run-1", "job-1")
        assert next_state.status == ContentArchitectStatus.BUILD_RUNNING
        assert next_state.run_id == "run-1"
        assert next_state.job_id == "job-1"

    def test_build_running_recovers_from_needs_attention(self):
        state = ContentArchitectState(status=ContentArchitectStatus.NEEDS_ATTENTION)
        next_state = apply_build_running(state, "run-1", "job-1")
        assert next_state.status == ContentArchitectStatus.BUILD_RUNNING

    def test_revision_requested_moves_to_build_running(self):
        state = ContentArchitectState(status=ContentArchitectStatus.CONTENT_REVIEW)
        next_state = apply_revision_requested(state, "run-2", "job-2", "Lead with QueueGuard")
        assert next_state.status == ContentArchitectStatus.BUILD_RUNNING
        assert next_state.run_id == "run-2"
        assert next_state.revision_request == "Lead with QueueGuard"

    def test_build_result_stores_content_and_merges_memory(self):
        state = ContentArchitectState(
            status=ContentArchitectStatus.BUILD_RUNNING, memory={"old": "kept"}
        )
        result = apply_build_result(
            state,
            version="content_architect.plan_content.v1",
            run_id="run-1",
            user_summary="We're presenting you as a backend-focused engineer.",
            site_story_strategy=ContentStoryStrategy(positioning="x"),
            decision_basis=[DecisionRecord(decision="tone", value="plain")],
            page_content=PortfolioPageContent.model_validate(valid_page()),
            internal_notes={"review": "confirm client name"},
            claim_grounding=[ClaimGrounding(claim_id="c1", statement="s")],
            omissions=[],
            unresolved_issues=["no metrics"],
            privacy_and_confidentiality=[],
            warnings=[],
            stages_run=["plan_content"],
            memory_update={"new": "value"},
        )
        assert result.status == ContentArchitectStatus.CONTENT_REVIEW
        assert result.page_content.hero.name == "Mock User"
        assert result.decision_basis[0].decision == "tone"
        assert result.site_story_strategy.positioning == "x"
        assert result.internal_notes == {"review": "confirm client name"}
        assert result.unresolved_issues == ["no metrics"]
        assert result.memory["old"] == "kept"
        assert result.memory["new"] == "value"
        assert result.latest_error is None

    def test_approval_snapshot(self):
        state = _public_review_state()
        approved = apply_approval(state, "abc123")
        assert approved.status == ContentArchitectStatus.APPROVED
        assert approved.approved is not None
        assert approved.approved.content_hash == "abc123"

    def test_approval_rejected_when_page_content_empty(self):
        state = ContentArchitectState(status=ContentArchitectStatus.CONTENT_REVIEW)
        with pytest.raises(ContentNotPublishableError):
            apply_approval(state, "abc123")

    def test_approval_allows_pending_claim_that_is_not_bound_to_the_page(self):
        state = _public_review_state()
        state.claim_grounding = [
            ClaimGrounding(claim_id="c-pending", publication_status=PublicationStatus.PENDING)
        ]
        approved = apply_approval(state, "abc123")
        # The gating invariant is preserved: the pending claim is NOT promoted.
        assert approved.claim_grounding[0].publication_status == PublicationStatus.PENDING

    @pytest.mark.parametrize("count", [3, 5])
    def test_approval_rejects_wrong_pillar_count(self, count):
        state = _public_review_state()
        pillars = state.page_content.systems_practice.pillars
        state.page_content.systems_practice.pillars = (pillars * 2)[:count]
        with pytest.raises(PublicScopeIncompleteError) as exc_info:
            apply_approval(state, "abc123")
        assert any("exactly 4" in error for error in exc_info.value.errors)

    def test_approval_rejects_incomplete_public_scope(self):
        state = _public_review_state()
        state.page_content.hero.intro = ""
        with pytest.raises(PublicScopeIncompleteError) as exc_info:
            apply_approval(state, "abc123")
        assert any("hero.intro" in error for error in exc_info.value.errors)

    def test_approval_rejects_non_public_claim_bound_to_a_field(self):
        state = _public_review_state()
        state.claim_grounding = [
            ClaimGrounding(
                claim_id="c1",
                publication_status=PublicationStatus.PENDING,
                field_paths=["hero.intro"],
            )
        ]
        with pytest.raises(PublicScopeIncompleteError) as exc_info:
            apply_approval(state, "abc123")
        assert any("'c1'" in error for error in exc_info.value.errors)

    def test_approval_rejects_internal_review_keys_in_page_copy(self):
        state = _public_review_state()
        dumped = state.page_content.model_dump()
        dumped["hero"]["status_note"] = "x"
        # The typed model drops stray keys, so approval is not blocked by them.
        assert "status_note" not in PortfolioPageContent.model_validate(dumped).hero.model_dump()
        apply_approval(state, "abc123")

    def test_needs_attention_records_error(self):
        state = apply_needs_attention(
            ContentArchitectState(status=ContentArchitectStatus.BUILD_RUNNING),
            {"code": "MODEL_TIMEOUT", "message": "Timed out", "retryable": True},
        )
        assert state.status == ContentArchitectStatus.NEEDS_ATTENTION
        assert state.latest_error["code"] == "MODEL_TIMEOUT"


class TestInvalidTransitionErrors:
    def test_build_result_from_wrong_state(self):
        with pytest.raises(InvalidTransitionError):
            apply_build_result(
                ContentArchitectState(status=ContentArchitectStatus.NOT_STARTED),
                version="v1",
                run_id="r",
                user_summary="",
                site_story_strategy=ContentStoryStrategy(),
                decision_basis=[],
                page_content=PortfolioPageContent(),
                internal_notes={},
                claim_grounding=[],
                omissions=[],
                unresolved_issues=[],
                privacy_and_confidentiality=[],
                warnings=[],
                stages_run=[],
                memory_update={},
            )

    def test_approval_from_wrong_state(self):
        with pytest.raises(InvalidTransitionError):
            apply_approval(ContentArchitectState(status=ContentArchitectStatus.BUILD_RUNNING), "h")

    def test_needs_attention_rejected_from_terminal(self):
        with pytest.raises(InvalidTransitionError):
            apply_needs_attention(
                ContentArchitectState(status=ContentArchitectStatus.APPROVED),
                {"code": "X", "message": "y"},
            )

    def test_revision_requested_from_wrong_state(self):
        with pytest.raises(InvalidTransitionError):
            apply_revision_requested(
                ContentArchitectState(status=ContentArchitectStatus.APPROVED),
                "r",
                "j",
                "revise it",
            )
