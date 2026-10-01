"""Unit tests for Content Architect output validators (transport contract only)."""

from __future__ import annotations

from typing import Any

from oryxenai.agents.content_architect.validators import validate_stage_output
from tests.unit.agents.content_architect.helpers import claim, valid_page


def _plan_with_content(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "mode": "STRATEGY_AND_CONTENT",
        "content_included": True,
        "site_story_strategy": {"positioning": "x"},
        "claim_grounding": [claim()],
        "page_content": valid_page(),
    }
    base.update(overrides)
    return base


class TestValidatePlanContent:
    def test_valid_single_page_with_content(self):
        outcome = validate_stage_output(_plan_with_content(), "plan_content")
        assert outcome.is_valid
        assert outcome.errors == []

    def test_valid_strategy_only_without_content(self):
        outcome = validate_stage_output(
            {
                "mode": "STRATEGY_ONLY",
                "content_included": False,
                "site_story_strategy": {"positioning": "x"},
            },
            "plan_content",
        )
        assert outcome.is_valid

    def test_mode_must_match_operation(self):
        outcome = validate_stage_output(_plan_with_content(mode="PAGES_READY"), "plan_content")
        assert not outcome.is_valid
        assert any("'mode'" in e for e in outcome.errors)

    def test_content_included_inconsistent_with_mode(self):
        outcome = validate_stage_output(
            _plan_with_content(mode="STRATEGY_ONLY"),
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("inconsistent" in e for e in outcome.errors)

    def test_empty_strategy_rejected(self):
        outcome = validate_stage_output(_plan_with_content(site_story_strategy={}), "plan_content")
        assert not outcome.is_valid
        assert any("site_story_strategy" in e for e in outcome.errors)

    def test_content_included_true_requires_page_content(self):
        payload = _plan_with_content()
        del payload["page_content"]
        outcome = validate_stage_output(payload, "plan_content")
        assert not outcome.is_valid
        assert any("page_content" in e for e in outcome.errors)

    def test_incomplete_page_is_a_readiness_concern_not_a_validation_error(self):
        """Completeness (e.g. four pillars) is repaired by the agent, not rejected here."""
        payload = _plan_with_content()
        payload["page_content"]["systems_practice"]["pillars"] = []
        assert validate_stage_output(payload, "plan_content").is_valid

    def test_wrong_scalar_type_in_page_rejected(self):
        payload = _plan_with_content()
        payload["page_content"]["hero"]["name"] = 123
        outcome = validate_stage_output(payload, "plan_content")
        assert not outcome.is_valid
        assert any("hero.name" in e for e in outcome.errors)

    def test_page_regions_must_be_objects(self):
        payload = _plan_with_content()
        payload["page_content"]["hero"] = "Mock User"
        outcome = validate_stage_output(payload, "plan_content")
        assert not outcome.is_valid
        assert any("hero must be an object" in e for e in outcome.errors)

    def test_pillars_must_be_objects(self):
        payload = _plan_with_content()
        payload["page_content"]["systems_practice"]["pillars"] = ["a", "b", "c", "d"]
        outcome = validate_stage_output(payload, "plan_content")
        assert not outcome.is_valid

    def test_group_items_must_be_strings(self):
        payload = _plan_with_content()
        payload["page_content"]["technical_capabilities"]["groups"][0]["items"] = [1, 2]
        outcome = validate_stage_output(payload, "plan_content")
        assert not outcome.is_valid

    def test_verified_claim_without_source_rejected(self):
        outcome = validate_stage_output(
            _plan_with_content(claim_grounding=[claim() | {"source_reference": ""}]),
            "plan_content",
        )
        assert not outcome.is_valid
        assert any("no source_reference" in e for e in outcome.errors)

    def test_unresolved_claim_without_source_accepted(self):
        unresolved = claim() | {"evidence_status": "unresolved", "source_reference": ""}
        outcome = validate_stage_output(
            _plan_with_content(claim_grounding=[unresolved]), "plan_content"
        )
        assert outcome.is_valid

    def test_duplicate_claim_ids_rejected(self):
        outcome = validate_stage_output(
            _plan_with_content(claim_grounding=[claim("c1"), claim("c1")]), "plan_content"
        )
        assert not outcome.is_valid
        assert any("Duplicate claim_id" in e for e in outcome.errors)

    def test_invalid_enums_rejected(self):
        for field, value in (
            ("evidence_status", "mostly"),
            ("ownership", "everyone"),
            ("publication_status", "maybe"),
        ):
            outcome = validate_stage_output(
                _plan_with_content(claim_grounding=[claim() | {field: value}]), "plan_content"
            )
            assert not outcome.is_valid, field

    def test_claim_field_paths_must_be_strings(self):
        outcome = validate_stage_output(
            _plan_with_content(claim_grounding=[claim() | {"field_paths": [1]}]), "plan_content"
        )
        assert not outcome.is_valid

    def test_claim_with_unknown_key_rejected(self):
        outcome = validate_stage_output(
            _plan_with_content(claim_grounding=[claim() | {"section_ids": ["hero"]}]),
            "plan_content",
        )
        assert not outcome.is_valid


class TestPublicationGating:
    def test_blocked_claim_bound_to_field_rejected(self):
        blocked = claim("c9", publication_status="blocked", field_paths=["hero.intro"])
        outcome = validate_stage_output(
            _plan_with_content(claim_grounding=[blocked]), "plan_content"
        )
        assert not outcome.is_valid
        assert any("blocked claim" in e for e in outcome.errors)

    def test_blocked_claim_with_no_field_paths_is_fine(self):
        blocked = claim("c9", publication_status="blocked")
        assert validate_stage_output(
            _plan_with_content(claim_grounding=[blocked]), "plan_content"
        ).is_valid

    def test_pending_claim_may_exist(self):
        pending = claim("c8", publication_status="pending")
        assert validate_stage_output(
            _plan_with_content(claim_grounding=[pending]), "plan_content"
        ).is_valid

    def test_known_blocked_claim_still_checked_when_stage_omits_claims(self):
        outcome = validate_stage_output(
            {"mode": "PAGES_READY", "content_included": False, "page_content": valid_page()},
            "write_pages",
            known_claim_grounding=[
                claim("c9", publication_status="blocked", field_paths=["hero.intro"])
            ],
        )
        assert not outcome.is_valid


class TestInternalNoteLeakage:
    def test_status_note_inside_page_content_rejected(self):
        payload = _plan_with_content()
        payload["page_content"]["hero"]["status_note"] = "Ownership pending confirmation."
        outcome = validate_stage_output(payload, "plan_content")
        assert not outcome.is_valid
        assert any("status_note" in e for e in outcome.errors)

    def test_nested_internal_key_rejected(self):
        payload = _plan_with_content()
        payload["page_content"]["systems_practice"]["pillars"][0]["evidence_status"] = "verified"
        outcome = validate_stage_output(payload, "plan_content")
        assert not outcome.is_valid
        assert any("evidence_status" in e for e in outcome.errors)

    def test_internal_notes_field_itself_is_fine(self):
        payload = _plan_with_content(internal_notes={"review_note": "confirm the client name"})
        assert validate_stage_output(payload, "plan_content").is_valid


class TestDecisionBasis:
    def test_valid_decision_basis(self):
        outcome = validate_stage_output(
            _plan_with_content(
                decision_basis=[{"decision": "tone", "value": "plain", "basis": "safe_default"}]
            ),
            "plan_content",
        )
        assert outcome.is_valid

    def test_invalid_basis_value_rejected(self):
        outcome = validate_stage_output(
            _plan_with_content(decision_basis=[{"decision": "tone", "basis": "vibes"}]),
            "plan_content",
        )
        assert not outcome.is_valid

    def test_missing_decision_name_rejected(self):
        outcome = validate_stage_output(
            _plan_with_content(decision_basis=[{"value": "x", "basis": "safe_default"}]),
            "plan_content",
        )
        assert not outcome.is_valid


class TestCoverageLedgerShape:
    def test_ledger_entry_must_be_valid_model(self):
        outcome = validate_stage_output(
            _plan_with_content(
                coverage_ledger=[{"source_id": "fact/1", "disposition": "used", "field_paths": "x"}]
            ),
            "plan_content",
        )
        assert not outcome.is_valid

    def test_legacy_public_refs_key_is_tolerated_as_stray(self):
        outcome = validate_stage_output(
            _plan_with_content(coverage_ledger=[{"source_id": "fact/1", "public_refs": []}]),
            "plan_content",
        )
        assert outcome.is_valid


class TestValidateWritePages:
    def test_valid_write_pages(self):
        outcome = validate_stage_output(
            {"mode": "PAGES_READY", "content_included": False, "page_content": valid_page()},
            "write_pages",
        )
        assert outcome.is_valid

    def test_missing_content_rejected(self):
        outcome = validate_stage_output(
            {"mode": "PAGES_READY", "content_included": False}, "write_pages"
        )
        assert not outcome.is_valid
        assert any("page_content" in e for e in outcome.errors)

    def test_wrong_mode_rejected(self):
        outcome = validate_stage_output(
            {"mode": "INTEGRATED", "content_included": False, "page_content": valid_page()},
            "write_pages",
        )
        assert not outcome.is_valid


class TestValidateIntegrateContent:
    def test_valid_integrate(self):
        outcome = validate_stage_output(
            {"mode": "INTEGRATED", "content_included": False, "page_content": valid_page()},
            "integrate_content",
        )
        assert outcome.is_valid

    def test_missing_page_content_rejected(self):
        outcome = validate_stage_output(
            {"mode": "INTEGRATED", "content_included": False, "page_content": {}},
            "integrate_content",
        )
        assert not outcome.is_valid


class TestDefensiveShapeChecks:
    def test_non_dict_input_rejected(self):
        assert not validate_stage_output([], "plan_content").is_valid  # type: ignore[arg-type]

    def test_unknown_operation_rejected(self):
        assert not validate_stage_output({}, "bogus").is_valid

    def test_non_bool_content_included_rejected(self):
        outcome = validate_stage_output(_plan_with_content(content_included="yes"), "plan_content")
        assert not outcome.is_valid

    def test_non_list_claim_grounding_rejected(self):
        outcome = validate_stage_output(_plan_with_content(claim_grounding={}), "plan_content")
        assert not outcome.is_valid

    def test_non_dict_internal_notes_rejected(self):
        outcome = validate_stage_output(_plan_with_content(internal_notes=[]), "plan_content")
        assert not outcome.is_valid

    def test_non_object_page_content_rejected(self):
        outcome = validate_stage_output(_plan_with_content(page_content=[]), "plan_content")
        assert not outcome.is_valid
