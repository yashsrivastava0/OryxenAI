"""Unit tests for Content Architect domain schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from oryxenai.agents.content_architect.schemas import (
    ClaimGrounding,
    ContentArchitectIntake,
    ContentArchitectOutput,
    ContentArchitectPreferences,
    ContentArchitectState,
    ContentArchitectStatus,
    ContentPlanMode,
    ContentSection,
    DecisionBasis,
    DecisionRecord,
    EvidenceStatus,
    Ownership,
    PageContentPack,
    PresentationMode,
    PublicationStatus,
    RoutePlanEntry,
)


class TestContentArchitectIntake:
    def test_empty_intake(self):
        intake = ContentArchitectIntake()
        assert intake.approved_brief_title == ""
        assert intake.profile == {}
        assert intake.open_items == []

    def test_does_not_carry_full_brief_markdown(self):
        """The full Discovery brief prose is deliberately not part of this schema.

        profile + user_summary carry the compact grounded facts; keeping the
        full markdown out avoids duplicated context, latency, and the risk of
        a later stage reading stale Discovery prose instead of finalized
        Content Architect output.
        """
        assert "approved_brief_markdown" not in ContentArchitectIntake.model_fields

    def test_accepts_any_input(self):
        intake = ContentArchitectIntake(
            user_summary="A short summary.",
            profile={"name": "Test User"},
        )
        assert intake.profile["name"] == "Test User"

    def test_unknown_fields_accepted(self):
        intake = ContentArchitectIntake(approved_brief_title="t", something_else={"nested": True})
        assert intake.something_else == {"nested": True}


class TestContentArchitectPreferences:
    def test_defaults_empty(self):
        prefs = ContentArchitectPreferences()
        assert prefs.goal == ""
        assert prefs.density == ""

    def test_unknown_fields_accepted(self):
        prefs = ContentArchitectPreferences(goal="get hired", extra_pref="x")
        assert prefs.extra_pref == "x"


class TestRoutePlanEntry:
    def test_minimal_route(self):
        route = RoutePlanEntry(route_id="home", path="/", purpose="Home page")
        assert route.title == ""
        assert route.section_sequence == []
        assert route.publication_status == PublicationStatus.APPROVED

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            RoutePlanEntry(route_id="home", path="/", unknown="bad")

    def test_publication_status_can_be_pending_or_blocked(self):
        pending = RoutePlanEntry(route_id="r", path="/r", purpose="p", publication_status="pending")
        blocked = RoutePlanEntry(route_id="r", path="/r", purpose="p", publication_status="blocked")
        assert pending.publication_status == PublicationStatus.PENDING
        assert blocked.publication_status == PublicationStatus.BLOCKED


class TestClaimGrounding:
    def test_defaults(self):
        claim = ClaimGrounding(claim_id="c1", statement="x")
        assert claim.evidence_status == EvidenceStatus.UNRESOLVED
        assert claim.ownership == Ownership.UNCLEAR
        assert claim.publication_status == PublicationStatus.PENDING

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            ClaimGrounding(claim_id="c1", unknown="bad")

    def test_evidence_status_ownership_and_publication_status_are_independent(self):
        """A claim can be well-evidenced, team-owned, and still not publication-approved.

        These are three separate questions; collapsing them (e.g. a
        "team_outcome" value living inside evidence_status) is exactly the
        bug this shape must not reintroduce.
        """
        claim = ClaimGrounding(
            claim_id="c1",
            statement="The team shipped the feature.",
            source_reference="ref",
            evidence_status=EvidenceStatus.VERIFIED,
            ownership=Ownership.TEAM,
            publication_status=PublicationStatus.PENDING,
        )
        assert claim.evidence_status == EvidenceStatus.VERIFIED
        assert claim.ownership == Ownership.TEAM
        assert claim.publication_status == PublicationStatus.PENDING

    def test_team_outcome_is_not_a_valid_evidence_status(self):
        with pytest.raises(PydanticValidationError):
            ClaimGrounding(claim_id="c1", evidence_status="team_outcome")


class TestContentPlanMode:
    def test_four_modes_round_trip(self):
        assert ContentPlanMode.STRATEGY_ONLY.value == "STRATEGY_ONLY"
        assert ContentPlanMode.STRATEGY_AND_CONTENT.value == "STRATEGY_AND_CONTENT"
        assert ContentPlanMode.PAGES_READY.value == "PAGES_READY"
        assert ContentPlanMode.INTEGRATED.value == "INTEGRATED"


class TestPresentationMode:
    def test_three_modes(self):
        assert {m.value for m in PresentationMode} == {"single_page", "hybrid", "multi_page"}


class TestPublicationStatus:
    def test_three_statuses(self):
        assert {m.value for m in PublicationStatus} == {"approved", "pending", "blocked"}


class TestContentSection:
    def test_minimal_section(self):
        section = ContentSection(section_id="hero", purpose="Intro")
        assert section.content == {}
        assert section.claim_ids == []
        assert section.optional is False

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            ContentSection(section_id="hero", unknown="bad")


class TestPageContentPack:
    def test_minimal_pack(self):
        pack = PageContentPack(route_id="home")
        assert pack.sections == []
        assert pack.internal_notes == {}

    def test_sections_and_internal_notes_are_separate(self):
        pack = PageContentPack(
            route_id="home",
            sections=[ContentSection(section_id="hero", content={"text": "hi"})],
            internal_notes={"needs_confirmation": "ownership"},
        )
        assert pack.sections[0].content == {"text": "hi"}
        assert pack.internal_notes["needs_confirmation"] == "ownership"

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            PageContentPack(route_id="home", unknown="bad")


class TestDecisionRecord:
    def test_defaults(self):
        record = DecisionRecord(decision="presentation_mode", value="single_page")
        assert record.basis == DecisionBasis.SAFE_DEFAULT

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            DecisionRecord(decision="x", unknown="bad")


class TestContentArchitectOutput:
    def test_minimal_output(self):
        output = ContentArchitectOutput(mode=ContentPlanMode.STRATEGY_ONLY)
        assert output.content_included is False
        assert output.route_plan == []
        assert output.page_content_packs == []
        assert output.decision_basis == []

    def test_mode_required(self):
        with pytest.raises(PydanticValidationError):
            ContentArchitectOutput()

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            ContentArchitectOutput(mode=ContentPlanMode.STRATEGY_ONLY, unknown="bad")

    def test_full_output_shape(self):
        output = ContentArchitectOutput(
            mode=ContentPlanMode.STRATEGY_AND_CONTENT,
            content_included=True,
            site_story_strategy={"positioning": "x"},
            decision_basis=[DecisionRecord(decision="presentation_mode", value="single_page")],
            route_plan=[RoutePlanEntry(route_id="home", path="/", purpose="p")],
            claim_grounding=[ClaimGrounding(claim_id="c1", statement="s")],
            page_content_packs=[
                PageContentPack(
                    route_id="home",
                    sections=[ContentSection(section_id="hero", claim_ids=["c1"])],
                )
            ],
            public_content_manifest={"nav": []},
        )
        assert output.route_plan[0].route_id == "home"
        assert output.page_content_packs[0].route_id == "home"
        assert output.page_content_packs[0].sections[0].claim_ids == ["c1"]


class TestContentArchitectState:
    def test_default_state(self):
        state = ContentArchitectState()
        assert state.status == ContentArchitectStatus.NOT_STARTED
        assert state.max_attempts == 3
        assert state.approved is None
        assert state.route_plan == []
        assert state.decision_basis == []

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            ContentArchitectState(status=ContentArchitectStatus.NOT_STARTED, unknown="bad")

    def test_round_trips_through_json(self):
        state = ContentArchitectState(
            status=ContentArchitectStatus.CONTENT_REVIEW,
            route_plan=[RoutePlanEntry(route_id="home", path="/", purpose="p")],
            claim_grounding=[ClaimGrounding(claim_id="c1", statement="s")],
            page_content_packs=[PageContentPack(route_id="home")],
            decision_basis=[DecisionRecord(decision="d", value="v")],
        )
        dumped = state.model_dump(mode="json")
        restored = ContentArchitectState.model_validate(dumped)
        assert restored == state
