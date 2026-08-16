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
    DecisionRecord,
    PageContentPack,
    PublicationStatus,
    RoutePlanEntry,
)
from oryxenai.agents.content_architect.state import (
    InvalidTransitionError,
    NoPublishableRoutesError,
    PublicScopeIncompleteError,
    apply_approval,
    apply_build_result,
    apply_build_running,
    apply_needs_attention,
    apply_revision_requested,
    apply_start,
    is_valid_transition,
)


def _source_ref() -> ContentArchitectSourceRef:
    return ContentArchitectSourceRef(discovery_brief_hash="hash1", discovery_session_revision=1)


def _public_review_state(*, include_pending: bool = False) -> ContentArchitectState:
    routes = [
        RoutePlanEntry(
            route_id="home",
            path="/",
            title="Home",
            purpose="Present the professional profile.",
            section_sequence=["hero"],
            publication_status=PublicationStatus.APPROVED,
        )
    ]
    if include_pending:
        routes.append(
            RoutePlanEntry(
                route_id="secret",
                path="/secret",
                title="Restricted work",
                purpose="Review-only material.",
                publication_status=PublicationStatus.PENDING,
            )
        )
    return ContentArchitectState(
        status=ContentArchitectStatus.CONTENT_REVIEW,
        route_plan=routes,
        page_content_packs=[
            PageContentPack(
                route_id="home",
                sections=[
                    {
                        "section_id": "hero",
                        "purpose": "Establish the positioning.",
                        "content": {"headline": "Grounded portfolio"},
                    }
                ],
            )
        ],
        public_content_manifest={"nav": [{"label": "Home", "target": "home"}]},
        visual_director_handoff={"content_hierarchy": ["hero"]},
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
            site_story_strategy={"positioning": "x"},
            decision_basis=[DecisionRecord(decision="presentation_mode", value="single_page")],
            route_plan=[RoutePlanEntry(route_id="home", path="/", purpose="p")],
            page_content_packs=[PageContentPack(route_id="home")],
            public_content_manifest={"nav": []},
            claim_grounding=[ClaimGrounding(claim_id="c1", statement="s")],
            omissions=[],
            unresolved_issues=["no metrics"],
            privacy_and_confidentiality=[],
            media_status={},
            visual_director_handoff={},
            warnings=[],
            stages_run=["plan_content"],
            memory_update={"new": "value"},
        )
        assert result.status == ContentArchitectStatus.CONTENT_REVIEW
        assert result.route_plan[0].route_id == "home"
        assert result.decision_basis[0].decision == "presentation_mode"
        assert result.page_content_packs[0].route_id == "home"
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
        assert approved.route_plan[0].publication_status == PublicationStatus.APPROVED

    def test_approval_rejected_when_no_publishable_routes(self):
        state = ContentArchitectState(
            status=ContentArchitectStatus.CONTENT_REVIEW,
            route_plan=[
                RoutePlanEntry(
                    route_id="home", path="/", publication_status=PublicationStatus.PENDING
                ),
                RoutePlanEntry(
                    route_id="about", path="/about", publication_status=PublicationStatus.BLOCKED
                ),
            ],
        )
        with pytest.raises(NoPublishableRoutesError) as exc_info:
            apply_approval(state, "abc123")
        assert exc_info.value.route_count == 2
        assert exc_info.value.route_statuses == {"home": "pending", "about": "blocked"}

    def test_approval_rejected_when_route_plan_empty(self):
        state = ContentArchitectState(status=ContentArchitectStatus.CONTENT_REVIEW, route_plan=[])
        with pytest.raises(NoPublishableRoutesError) as exc_info:
            apply_approval(state, "abc123")
        assert exc_info.value.route_count == 0
        assert exc_info.value.route_statuses == {}

    def test_approval_allows_mixed_approved_and_pending(self):
        state = _public_review_state(include_pending=True)
        approved = apply_approval(state, "abc123")
        assert approved.status == ContentArchitectStatus.APPROVED
        # The gating invariant is preserved: the pending route is NOT promoted.
        statuses = {route.route_id: route.publication_status for route in approved.route_plan}
        assert statuses == {
            "home": PublicationStatus.APPROVED,
            "secret": PublicationStatus.PENDING,
        }

    def test_approval_rejects_incomplete_public_scope(self):
        state = _public_review_state()
        state.page_content_packs[0].sections[0].content = {}
        with pytest.raises(PublicScopeIncompleteError) as exc_info:
            apply_approval(state, "abc123")
        assert exc_info.value.route_ids == ["home"]
        assert any("has no content" in error for error in exc_info.value.errors)

    def test_approval_rejects_paths_that_collide_after_pack_normalization(self):
        state = _public_review_state()
        state.route_plan.append(
            RoutePlanEntry(
                route_id="about",
                path="/",
                title="About",
                purpose="Provide concise context.",
                section_sequence=["about"],
                publication_status=PublicationStatus.APPROVED,
            )
        )
        state.page_content_packs.append(
            PageContentPack(
                route_id="about",
                sections=[
                    {
                        "section_id": "about",
                        "purpose": "Provide concise context.",
                        "content": {"body": "Grounded detail."},
                    }
                ],
            )
        )
        state.route_plan[1].path = "/home/"
        state.route_plan[0].path = "/home"

        with pytest.raises(PublicScopeIncompleteError) as exc_info:
            apply_approval(state, "abc123")

        assert any("collides" in error for error in exc_info.value.errors)

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
                site_story_strategy={},
                decision_basis=[],
                route_plan=[],
                page_content_packs=[],
                public_content_manifest={},
                claim_grounding=[],
                omissions=[],
                unresolved_issues=[],
                privacy_and_confidentiality=[],
                media_status={},
                visual_director_handoff={},
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
