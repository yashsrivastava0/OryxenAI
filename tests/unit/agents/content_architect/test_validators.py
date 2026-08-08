"""Unit tests for Content Architect output validators (transport contract only)."""

from __future__ import annotations

from oryxenai.agents.content_architect.validators import validate_stage_output


def _route(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "route_id": "home",
        "path": "/",
        "purpose": "Home page",
        "publication_status": "approved",
    }
    base.update(overrides)
    return base


def _claim(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "claim_id": "c1",
        "statement": "Did a thing",
        "source_reference": "profile.projects[0]",
        "evidence_status": "verified",
        "ownership": "individual",
        "publication_status": "approved",
    }
    base.update(overrides)
    return base


def _section(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "section_id": "hero",
        "purpose": "Intro",
        "content": {"text": "hello"},
        "claim_ids": [],
    }
    base.update(overrides)
    return base


def _pack(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "route_id": "home",
        "sections": [_section()],
        "internal_notes": {},
    }
    base.update(overrides)
    return base


def _plan_content_single_page(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "mode": "STRATEGY_AND_CONTENT",
        "content_included": True,
        "site_story_strategy": {"positioning": "x"},
        "route_plan": [_route()],
        "claim_grounding": [_claim()],
        "page_content_packs": [_pack()],
        "public_content_manifest": {"nav": []},
    }
    base.update(overrides)
    return base


class TestValidatePlanContent:
    def test_valid_single_page_with_content(self):
        outcome = validate_stage_output(_plan_content_single_page(), "plan_content")
        assert outcome.is_valid
        assert outcome.errors == []

    def test_valid_strategy_only_without_content(self):
        outcome = validate_stage_output(
            {
                "mode": "STRATEGY_ONLY",
                "content_included": False,
                "site_story_strategy": {"positioning": "x"},
                "route_plan": [_route(), _route(route_id="about", path="/about")],
            },
            "plan_content",
        )
        assert outcome.is_valid

    def test_mode_must_match_operation(self):
        outcome = validate_stage_output(
            {**_plan_content_single_page(), "mode": "PAGES_READY"}, "plan_content"
        )
        assert not outcome.is_valid
        assert any("'mode' must be one of" in error for error in outcome.errors)

    def test_content_included_inconsistent_with_mode(self):
        outcome = validate_stage_output(
            {**_plan_content_single_page(), "mode": "STRATEGY_ONLY"}, "plan_content"
        )
        assert not outcome.is_valid
        assert any("inconsistent with content_included" in error for error in outcome.errors)

    def test_empty_route_plan_rejected(self):
        outcome = validate_stage_output(
            {
                "mode": "STRATEGY_ONLY",
                "content_included": False,
                "site_story_strategy": {"positioning": "x"},
                "route_plan": [],
            },
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("'route_plan' must not be empty" in error for error in outcome.errors)

    def test_empty_strategy_rejected(self):
        outcome = validate_stage_output(
            {
                "mode": "STRATEGY_ONLY",
                "content_included": False,
                "site_story_strategy": {},
                "route_plan": [_route()],
            },
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("'site_story_strategy' must not be empty" in error for error in outcome.errors)

    def test_content_included_true_requires_content(self):
        outcome = validate_stage_output(
            {
                "mode": "STRATEGY_AND_CONTENT",
                "content_included": True,
                "site_story_strategy": {"positioning": "x"},
                "route_plan": [_route()],
                "page_content_packs": [],
                "public_content_manifest": {},
            },
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("'page_content_packs' must not be empty" in error for error in outcome.errors)
        assert any(
            "'public_content_manifest' must not be empty" in error for error in outcome.errors
        )

    def test_large_route_count_is_not_a_validation_error(self):
        """A long route plan is a fact about the input, not a shape defect.

        ContentArchitectAgent truncates route_plan/page_content_packs to
        [content_architect].max_routes after validation instead of this
        validator rejecting it — see test_agent.py, mirroring Discovery's
        validate_brief_output/max_projects precedent.
        """
        routes = [_route(route_id=f"r{i}", path=f"/{i}") for i in range(20)]
        outcome = validate_stage_output(
            {
                "mode": "STRATEGY_ONLY",
                "content_included": False,
                "site_story_strategy": {"positioning": "x"},
                "route_plan": routes,
            },
            "plan_content",
        )
        assert outcome.is_valid

    def test_duplicate_route_ids_rejected(self):
        outcome = validate_stage_output(
            {
                "mode": "STRATEGY_ONLY",
                "content_included": False,
                "site_story_strategy": {"positioning": "x"},
                "route_plan": [_route(), _route()],
            },
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("Duplicate route_id" in error for error in outcome.errors)

    def test_route_missing_path_rejected(self):
        outcome = validate_stage_output(
            {
                "mode": "STRATEGY_ONLY",
                "content_included": False,
                "site_story_strategy": {"positioning": "x"},
                "route_plan": [_route(path="")],
            },
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("has no path" in error for error in outcome.errors)

    def test_invalid_route_publication_status_rejected(self):
        outcome = validate_stage_output(
            {
                "mode": "STRATEGY_ONLY",
                "content_included": False,
                "site_story_strategy": {"positioning": "x"},
                "route_plan": [_route(publication_status="maybe")],
            },
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("invalid publication_status" in error for error in outcome.errors)

    def test_verified_claim_without_source_rejected(self):
        outcome = validate_stage_output(
            {**_plan_content_single_page(), "claim_grounding": [_claim(source_reference="")]},
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("has no source_reference" in error for error in outcome.errors)

    def test_unresolved_claim_without_source_accepted(self):
        outcome = validate_stage_output(
            {
                **_plan_content_single_page(),
                "claim_grounding": [_claim(evidence_status="unresolved", source_reference="")],
            },
            "plan_content",
        )
        assert outcome.is_valid

    def test_duplicate_claim_ids_rejected(self):
        outcome = validate_stage_output(
            {**_plan_content_single_page(), "claim_grounding": [_claim(), _claim()]},
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("Duplicate claim_id" in error for error in outcome.errors)

    def test_invalid_evidence_status_rejected(self):
        outcome = validate_stage_output(
            {
                **_plan_content_single_page(),
                "claim_grounding": [_claim(evidence_status="team_outcome")],
            },
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("invalid evidence_status" in error for error in outcome.errors)

    def test_invalid_ownership_rejected(self):
        outcome = validate_stage_output(
            {**_plan_content_single_page(), "claim_grounding": [_claim(ownership="solo")]},
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("invalid ownership" in error for error in outcome.errors)

    def test_invalid_claim_publication_status_rejected(self):
        outcome = validate_stage_output(
            {
                **_plan_content_single_page(),
                "claim_grounding": [_claim(publication_status="maybe")],
            },
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("invalid publication_status" in error for error in outcome.errors)


class TestPublicationGating:
    def test_blocked_route_referenced_in_page_content_packs_rejected(self):
        outcome = validate_stage_output(
            {
                **_plan_content_single_page(),
                "route_plan": [_route(publication_status="blocked")],
            },
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("blocked route_id" in error for error in outcome.errors)

    def test_pending_route_may_appear_in_page_content_packs(self):
        outcome = validate_stage_output(
            {**_plan_content_single_page(), "route_plan": [_route(publication_status="pending")]},
            "plan_content",
        )
        assert outcome.is_valid

    def test_blocked_claim_referenced_by_section_rejected(self):
        outcome = validate_stage_output(
            {
                **_plan_content_single_page(),
                "claim_grounding": [_claim(publication_status="blocked")],
                "page_content_packs": [_pack(sections=[_section(claim_ids=["c1"])])],
            },
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("blocked claim_id" in error for error in outcome.errors)

    def test_pack_referencing_unknown_route_rejected(self):
        outcome = validate_stage_output(
            {
                **_plan_content_single_page(),
                "page_content_packs": [_pack(route_id="does-not-exist")],
            },
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("unknown route_id" in error for error in outcome.errors)

    def test_section_referencing_unknown_claim_rejected(self):
        outcome = validate_stage_output(
            {
                **_plan_content_single_page(),
                "page_content_packs": [_pack(sections=[_section(claim_ids=["nope"])])],
            },
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("unknown claim_id" in error for error in outcome.errors)


class TestInternalNoteLeakage:
    def test_status_note_inside_content_rejected(self):
        outcome = validate_stage_output(
            {
                **_plan_content_single_page(),
                "page_content_packs": [
                    _pack(
                        sections=[_section(content={"text": "x", "status_note": "pending review"})]
                    )
                ],
            },
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("internal-review key" in error for error in outcome.errors)

    def test_nested_internal_key_rejected(self):
        outcome = validate_stage_output(
            {
                **_plan_content_single_page(),
                "page_content_packs": [
                    _pack(
                        sections=[
                            _section(
                                content={
                                    "items": [{"title": "x", "publication_check": ["confirm"]}]
                                }
                            )
                        ]
                    )
                ],
            },
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("internal-review key" in error for error in outcome.errors)

    def test_internal_notes_field_itself_is_fine(self):
        outcome = validate_stage_output(
            {
                **_plan_content_single_page(),
                "page_content_packs": [_pack(internal_notes={"status_note": "needs review"})],
            },
            "plan_content",
        )
        assert outcome.is_valid

    def test_duplicate_section_id_within_pack_rejected(self):
        outcome = validate_stage_output(
            {
                **_plan_content_single_page(),
                "page_content_packs": [_pack(sections=[_section(), _section()])],
            },
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("duplicate section_id" in error for error in outcome.errors)


class TestDecisionBasis:
    def test_valid_decision_basis(self):
        outcome = validate_stage_output(
            {
                **_plan_content_single_page(),
                "decision_basis": [
                    {
                        "decision": "presentation_mode",
                        "value": "single_page",
                        "basis": "safe_default",
                    }
                ],
            },
            "plan_content",
        )
        assert outcome.is_valid

    def test_invalid_basis_value_rejected(self):
        outcome = validate_stage_output(
            {
                **_plan_content_single_page(),
                "decision_basis": [{"decision": "presentation_mode", "basis": "guessed"}],
            },
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("invalid 'basis'" in error for error in outcome.errors)

    def test_missing_decision_name_rejected(self):
        outcome = validate_stage_output(
            {**_plan_content_single_page(), "decision_basis": [{"basis": "safe_default"}]},
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("has no 'decision' name" in error for error in outcome.errors)


class TestValidateWritePages:
    def test_valid_write_pages(self):
        outcome = validate_stage_output(
            {
                "mode": "PAGES_READY",
                "content_included": False,
                "page_content_packs": [_pack()],
                "public_content_manifest": {"nav": []},
            },
            "write_pages",
            known_route_plan=[_route()],
        )
        assert outcome.is_valid

    def test_missing_content_rejected(self):
        outcome = validate_stage_output(
            {
                "mode": "PAGES_READY",
                "content_included": False,
                "page_content_packs": [],
                "public_content_manifest": {},
            },
            "write_pages",
        )
        assert not outcome.is_valid

    def test_wrong_mode_rejected(self):
        outcome = validate_stage_output(
            {
                "mode": "STRATEGY_ONLY",
                "content_included": False,
                "page_content_packs": [_pack()],
                "public_content_manifest": {"nav": []},
            },
            "write_pages",
        )
        assert not outcome.is_valid

    def test_known_route_plan_still_blocks_blocked_routes(self):
        outcome = validate_stage_output(
            {
                "mode": "PAGES_READY",
                "content_included": False,
                "page_content_packs": [_pack()],
                "public_content_manifest": {"nav": []},
            },
            "write_pages",
            known_route_plan=[_route(publication_status="blocked")],
        )
        assert not outcome.is_valid
        assert any("blocked route_id" in error for error in outcome.errors)


class TestValidateIntegrateContent:
    def test_valid_integrate(self):
        outcome = validate_stage_output(
            {
                "mode": "INTEGRATED",
                "content_included": False,
                "page_content_packs": [_pack()],
                "public_content_manifest": {"nav": []},
                "visual_director_handoff": {"content_hierarchy": ["hero"]},
            },
            "integrate_content",
            known_route_plan=[_route()],
        )
        assert outcome.is_valid

    def test_missing_handoff_rejected(self):
        outcome = validate_stage_output(
            {
                "mode": "INTEGRATED",
                "content_included": False,
                "page_content_packs": [_pack()],
                "public_content_manifest": {"nav": []},
                "visual_director_handoff": {},
            },
            "integrate_content",
        )
        assert not outcome.is_valid
        assert any(
            "'visual_director_handoff' must not be empty" in error for error in outcome.errors
        )


class TestDefensiveShapeChecks:
    def test_non_dict_input_rejected(self):
        outcome = validate_stage_output([], "plan_content")  # type: ignore[arg-type]
        assert not outcome.is_valid

    def test_unknown_operation_rejected(self):
        outcome = validate_stage_output(_plan_content_single_page(), "not_a_real_operation")
        assert not outcome.is_valid

    def test_non_list_route_plan_rejected(self):
        outcome = validate_stage_output(
            {**_plan_content_single_page(), "route_plan": "not-a-list"}, "plan_content"
        )
        assert not outcome.is_valid
        assert any("'route_plan' must be a list" in error for error in outcome.errors)

    def test_non_bool_content_included_rejected(self):
        outcome = validate_stage_output(
            {**_plan_content_single_page(), "content_included": "yes"}, "plan_content"
        )
        assert not outcome.is_valid
        assert any("'content_included' must be a boolean" in error for error in outcome.errors)

    def test_non_list_page_content_packs_rejected(self):
        outcome = validate_stage_output(
            {**_plan_content_single_page(), "page_content_packs": "nope"}, "plan_content"
        )
        assert not outcome.is_valid
        assert any("'page_content_packs' must be a list" in error for error in outcome.errors)

    def test_pack_sections_must_be_a_list(self):
        outcome = validate_stage_output(
            {**_plan_content_single_page(), "page_content_packs": [_pack(sections="nope")]},
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("'sections' must be a list" in error for error in outcome.errors)
