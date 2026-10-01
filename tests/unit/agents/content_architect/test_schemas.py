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
    ContentCoverageEntry,
    ContentPlanMode,
    ContentStoryStrategy,
    CoverageDisposition,
    DecisionBasis,
    DecisionRecord,
    EvidenceStatus,
    HeroContent,
    Ownership,
    PortfolioPageContent,
    PublicationStatus,
    SystemsPracticeContent,
)
from tests.unit.agents.content_architect.helpers import valid_page


class TestContentArchitectIntake:
    def test_empty_intake(self):
        intake = ContentArchitectIntake()
        assert intake.approved_brief_title == ""
        assert intake.profile == {}
        assert intake.dossier == {}
        assert intake.open_items == []

    def test_does_not_carry_full_brief_markdown(self):
        """The full Discovery brief prose is deliberately not part of this schema.

        The source-linked dossier, rather than duplicate Markdown, now carries
        the complete approved factual handoff for new sessions.
        """
        assert "approved_brief_markdown" not in ContentArchitectIntake.model_fields

    def test_accepts_any_input(self):
        intake = ContentArchitectIntake(
            user_summary="A short summary.",
            profile={"name": "Test User"},
            dossier={"facts": [{"id": "fact:1", "statement": "An exact detail"}]},
        )
        assert intake.profile["name"] == "Test User"
        assert intake.dossier["facts"][0]["statement"] == "An exact detail"

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


class TestClaimGrounding:
    def test_defaults(self):
        claim = ClaimGrounding(claim_id="c1", statement="x")
        assert claim.evidence_status == EvidenceStatus.UNRESOLVED
        assert claim.ownership == Ownership.UNCLEAR
        assert claim.publication_status == PublicationStatus.PENDING
        assert claim.field_paths == []

    def test_field_paths_round_trip(self):
        claim = ClaimGrounding(claim_id="c1", field_paths=["hero.intro"])
        assert ClaimGrounding.model_validate(claim.model_dump(mode="json")).field_paths == [
            "hero.intro"
        ]

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


class TestPublicationStatus:
    def test_three_statuses(self):
        assert {m.value for m in PublicationStatus} == {"approved", "pending", "blocked"}


class TestCoverageDisposition:
    def test_six_dispositions(self):
        assert {m.value for m in CoverageDisposition} == {
            "used",
            "condensed",
            "retained_internally",
            "excluded_by_restriction",
            "excluded_editorially",
            "unresolved",
        }

    def test_entry_defaults_and_round_trip(self):
        entry = ContentCoverageEntry(source_id="fact/1", disposition="used", field_paths=["a.b"])
        assert ContentCoverageEntry.model_validate(entry.model_dump(mode="json")) == entry

    def test_entry_loads_rows_saved_with_the_old_public_refs_key(self):
        entry = ContentCoverageEntry.model_validate(
            {"source_id": "fact/1", "disposition": "published", "public_refs": ["home#hero"]}
        )
        assert entry.field_paths == []


class TestPortfolioPageContent:
    def test_empty_page_defaults(self):
        page = PortfolioPageContent()
        assert page.hero.name == ""
        assert page.systems_practice.pillars == []
        assert page.marquee_keywords == []

    def test_pillar_count_is_a_validator_rule_not_a_schema_rule(self):
        assert len(SystemsPracticeContent(pillars=[]).pillars) == 0

    def test_valid_page_round_trips(self):
        page = PortfolioPageContent.model_validate(valid_page())
        assert page.hero.headline_emphasis == "stay up."
        assert len(page.systems_practice.pillars) == 4
        assert page.connect.destinations[0].featured is True
        assert PortfolioPageContent.model_validate(page.model_dump(mode="json")) == page

    def test_stray_keys_are_ignored(self):
        assert not hasattr(HeroContent.model_validate({"name": "A", "bogus": 1}), "bogus")

    def test_wrong_types_rejected(self):
        with pytest.raises(PydanticValidationError):
            HeroContent.model_validate({"name": 5})


class TestContentStoryStrategy:
    def test_defaults(self):
        strategy = ContentStoryStrategy()
        assert strategy.positioning == ""
        assert strategy.leading_evidence == []

    def test_legacy_free_form_strategy_still_loads(self):
        strategy = ContentStoryStrategy.model_validate(
            {"positioning": "x", "presentation_mode": "single_page", "presentation_rationale": "y"}
        )
        assert strategy.positioning == "x"


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
        assert output.page_content == PortfolioPageContent()
        assert output.decision_basis == []
        assert output.internal_notes == {}

    def test_mode_required(self):
        with pytest.raises(PydanticValidationError):
            ContentArchitectOutput()

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            ContentArchitectOutput(mode=ContentPlanMode.STRATEGY_ONLY, unknown="bad")

    def test_legacy_route_fields_are_rejected(self):
        with pytest.raises(PydanticValidationError):
            ContentArchitectOutput(mode=ContentPlanMode.STRATEGY_ONLY, route_plan=[])

    def test_full_output_shape(self):
        output = ContentArchitectOutput(
            mode=ContentPlanMode.STRATEGY_AND_CONTENT,
            content_included=True,
            site_story_strategy=ContentStoryStrategy(positioning="x"),
            decision_basis=[DecisionRecord(decision="tone", value="plain")],
            page_content=PortfolioPageContent.model_validate(valid_page()),
            claim_grounding=[ClaimGrounding(claim_id="c1", field_paths=["hero.intro"])],
        )
        assert output.page_content.hero.name == "Mock User"
        assert output.claim_grounding[0].field_paths == ["hero.intro"]


class TestContentArchitectState:
    def test_default_state(self):
        state = ContentArchitectState()
        assert state.status == ContentArchitectStatus.NOT_STARTED
        assert state.max_attempts == 3
        assert state.approved is None
        assert state.page_content == PortfolioPageContent()
        assert state.decision_basis == []

    def test_unknown_saved_fields_are_ignored(self):
        state = ContentArchitectState(status=ContentArchitectStatus.NOT_STARTED, unknown="bad")
        assert "unknown" not in state.model_dump()

    def test_state_saved_with_the_route_schema_still_loads(self):
        state = ContentArchitectState.model_validate(
            {
                "status": "content_review",
                "route_plan": [{"route_id": "home", "path": "/"}],
                "page_content_packs": [{"route_id": "home"}],
                "public_content_manifest": {"nav": []},
                "site_story_strategy": {"positioning": "x", "presentation_mode": "single_page"},
                "coverage_ledger": [{"source_id": "fact/1", "public_refs": []}],
            }
        )
        assert state.status == ContentArchitectStatus.CONTENT_REVIEW
        assert state.page_content == PortfolioPageContent()

    def test_round_trips_through_json(self):
        state = ContentArchitectState(
            status=ContentArchitectStatus.CONTENT_REVIEW,
            page_content=PortfolioPageContent.model_validate(valid_page()),
            claim_grounding=[ClaimGrounding(claim_id="c1", statement="s")],
            decision_basis=[DecisionRecord(decision="d", value="v")],
            internal_notes={"note": "x"},
        )
        dumped = state.model_dump(mode="json")
        restored = ContentArchitectState.model_validate(dumped)
        assert restored == state
