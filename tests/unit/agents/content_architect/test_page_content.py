"""Unit tests for the deterministic single-page content rules."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest

from oryxenai.agents.content_architect.page_content import (
    PILLAR_COUNT,
    claim_binding_errors,
    coverage_errors,
    page_completeness_errors,
    page_shape_errors,
    parse_field_path,
    path_is_populated,
    resolve_field_path,
)
from oryxenai.agents.content_architect.schemas import CoverageDisposition
from tests.unit.agents.content_architect.helpers import claim, valid_page


class TestFieldPaths:
    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("hero.intro", ["hero", "intro"]),
            ("systems_practice.pillars[0].title", ["systems_practice", "pillars", 0, "title"]),
            ("systems_practice.pillars.2.title", ["systems_practice", "pillars", 2, "title"]),
            ("marquee_keywords[3]", ["marquee_keywords", 3]),
            ("a.b[0][1]", ["a", "b", 0, 1]),
        ],
    )
    def test_parse(self, path, expected):
        assert parse_field_path(path) == expected

    @pytest.mark.parametrize("path", ["", "  ", "hero..intro", "hero.in tro", "[x]", None, 4])
    def test_parse_rejects_malformed(self, path):
        assert parse_field_path(path) is None

    def test_resolve_and_populated(self):
        page = valid_page()
        assert resolve_field_path(page, "hero.name") == "Mock User"
        assert path_is_populated(page, "systems_practice.pillars[3].title")
        assert not path_is_populated(page, "systems_practice.pillars[4].title")
        assert not path_is_populated(page, "hero.nope")
        page["hero"]["eyebrow_secondary"] = ""
        assert not path_is_populated(page, "hero.eyebrow_secondary")


class TestCompleteness:
    def test_valid_page_has_no_errors(self):
        assert page_completeness_errors(valid_page()) == []
        assert page_shape_errors(valid_page()) == []

    @pytest.mark.parametrize("count", [0, 3, 5])
    def test_pillar_count_must_be_exactly_four(self, count):
        page = valid_page()
        pillars = page["systems_practice"]["pillars"]
        page["systems_practice"]["pillars"] = (pillars * 2)[:count]
        errors = page_completeness_errors(page)
        assert any(f"exactly {PILLAR_COUNT}" in e for e in errors)

    def test_pillar_needs_title_and_description(self):
        page = valid_page()
        page["systems_practice"]["pillars"][1]["description"] = " "
        page["systems_practice"]["pillars"][2]["title"] = ""
        errors = page_completeness_errors(page)
        assert any("pillars[1].description" in e for e in errors)
        assert any("pillars[2].title" in e for e in errors)

    def test_hero_requirements(self):
        page = valid_page()
        page["hero"].update(name="", intro="", headline_prefix="", headline_emphasis="")
        errors = page_completeness_errors(page)
        assert {"hero.name is required", "hero.intro is required"} <= set(errors)
        assert any("headline" in e for e in errors)

    def test_headline_emphasis_alone_is_enough(self):
        page = valid_page()
        page["hero"]["headline_prefix"] = ""
        assert page_completeness_errors(page) == []

    def test_metadata_and_section_labels_required(self):
        page = valid_page()
        page["metadata"]["title"] = ""
        page["connect"]["eyebrow"] = ""
        page["technical_capabilities"]["heading"] = ""
        errors = page_completeness_errors(page)
        assert "metadata.title is required" in errors
        assert "connect.eyebrow is required" in errors
        assert "technical_capabilities.heading is required" in errors

    def test_capability_group_needs_heading_and_items(self):
        page = valid_page()
        page["technical_capabilities"]["groups"] = [{"heading": "Backend", "items": []}]
        assert any("items needs at least one" in e for e in page_completeness_errors(page))
        page["technical_capabilities"]["groups"] = []
        assert any("at least one group" in e for e in page_completeness_errors(page))

    def test_empty_organizations_destinations_and_marquee_are_allowed(self):
        page = valid_page()
        page["professional_context"]["organizations"] = []
        page["connect"]["destinations"] = []
        page["marquee_keywords"] = []
        assert page_completeness_errors(page) == []

    def test_destination_urls_must_be_safe(self):
        page = valid_page()
        page["connect"]["destinations"][0]["url"] = "javascript:alert(1)"
        page["connect"]["destinations"][1]["url"] = "mailto:me@example.com"
        errors = page_completeness_errors(page)
        assert any("destinations[0].url" in e for e in errors)
        assert not any("destinations[1].url" in e for e in errors)

    def test_non_dict_page(self):
        assert page_completeness_errors(None) == ["page_content is missing"]
        assert page_shape_errors([]) == ["'page_content' must be an object"]


class TestClaimBinding:
    def test_approved_claim_must_resolve(self):
        page = valid_page()
        ok = claim(field_paths=["hero.intro"])
        bad = claim("c2", field_paths=["systems_practice.pillars[9].title"])
        assert claim_binding_errors(page, [ok]) == []
        assert any("no populated copy" in e for e in claim_binding_errors(page, [bad]))

    @pytest.mark.parametrize("status", ["pending", "blocked"])
    def test_non_approved_claim_cannot_be_bound(self, status):
        errors = claim_binding_errors(
            valid_page(), [claim(publication_status=status, field_paths=["hero.intro"])]
        )
        assert any(status in e for e in errors)

    def test_non_approved_claim_without_paths_is_fine(self):
        assert claim_binding_errors(valid_page(), [claim(publication_status="pending")]) == []

    def test_field_paths_must_be_a_list(self):
        assert claim_binding_errors(valid_page(), [claim() | {"field_paths": "hero.intro"}])


class TestCoverage:
    DOSSIER: ClassVar[dict[str, Any]] = {
        "contract_version": "DiscoveryDossier/v1",
        "facts": [{"id": "f1"}],
        "roles": [{"id": "r1"}],
        "projects": [{"id": "p1"}],
        "other_evidence": [{"id": "e1"}],
    }

    def _ledger(self):
        return [
            {"source_id": "fact/f1", "disposition": "used", "field_paths": ["hero.intro"]},
            {
                "source_id": "role/r1",
                "disposition": "condensed",
                "field_paths": ["professional_context.organizations[0]"],
            },
            {"source_id": "project/p1", "disposition": "excluded_by_restriction", "reason": "NDA"},
            {"source_id": "evidence/e1", "disposition": "unresolved", "reason": "conflict"},
        ]

    def test_complete_ledger_passes(self):
        assert coverage_errors(self.DOSSIER, self._ledger(), valid_page()) == []

    def test_legacy_dossierless_session_skips_coverage(self):
        assert coverage_errors({}, [], valid_page()) == []

    def test_all_six_dispositions_are_recognised(self):
        assert {d.value for d in CoverageDisposition} == {
            "used",
            "condensed",
            "retained_internally",
            "excluded_by_restriction",
            "excluded_editorially",
            "unresolved",
        }

    def test_missing_unknown_and_repeated_items(self):
        ledger = self._ledger()[:3]
        ledger.append({"source_id": "fact/nope", "disposition": "unresolved", "reason": "x"})
        ledger.append(ledger[0])
        errors = coverage_errors(self.DOSSIER, ledger, valid_page())
        assert any("missing dossier items: evidence/e1" in e for e in errors)
        assert any("unknown source_id 'fact/nope'" in e for e in errors)
        assert any("repeats source_id" in e for e in errors)

    def test_used_needs_populated_paths_and_others_need_reason_only(self):
        ledger = self._ledger()
        ledger[0]["field_paths"] = ["hero.nope"]
        ledger[2] = {
            "source_id": "project/p1",
            "disposition": "retained_internally",
            "field_paths": ["hero.intro"],
            "reason": "x",
        }
        ledger[3] = {"source_id": "evidence/e1", "disposition": "unresolved"}
        errors = coverage_errors(self.DOSSIER, ledger, valid_page())
        assert any("'fact/f1' needs field_paths with populated copy" in e for e in errors)
        assert any("'project/p1' needs a reason and no field_paths" in e for e in errors)
        assert any("'evidence/e1' needs a reason" in e for e in errors)

    def test_legacy_disposition_names_are_rejected(self):
        ledger = self._ledger()
        ledger[0]["disposition"] = "published"
        assert any("invalid disposition" in e for e in coverage_errors(self.DOSSIER, ledger, {}))
