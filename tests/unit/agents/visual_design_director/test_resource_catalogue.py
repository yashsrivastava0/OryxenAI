"""Unit tests for the deterministic local resource-catalogue lookup."""

from __future__ import annotations

from oryxenai.agents.visual_design_director.resource_catalogue import (
    catalogue_size,
    find_candidates,
    validate_catalogue_integrity,
)


class TestCatalogueIntegrity:
    def test_no_integrity_errors(self):
        assert validate_catalogue_integrity() == []

    def test_entry_count_within_range(self):
        assert 10 <= catalogue_size() <= 20


class TestFindCandidates:
    def test_respects_limit(self):
        results = find_candidates(["hero", "single_page"], limit=2)
        assert len(results) <= 2

    def test_empty_tags_returns_baseline_shortlist(self):
        results = find_candidates([], limit=4)
        assert len(results) == 4

    def test_deterministic_for_identical_input(self):
        first = find_candidates(["diagram", "technical"], limit=5)
        second = find_candidates(["diagram", "technical"], limit=5)
        assert [entry["resource_id"] for entry in first] == [
            entry["resource_id"] for entry in second
        ]

    def test_ranks_by_tag_overlap(self):
        results = find_candidates(["hero", "text-dominant", "asymmetric"], limit=1)
        assert results[0]["resource_id"] == "hero_asymmetric_text_dominant"

    def test_no_overlap_falls_back_to_baseline(self):
        results = find_candidates(["totally_unrelated_tag_xyz"], limit=3)
        assert len(results) == 3

    def test_tags_stripped_by_caller_not_by_find_candidates(self):
        """find_candidates itself still returns full entries including tags —
        stripping tags before prompt injection is agent.py's responsibility,
        not this module's."""
        results = find_candidates(["hero"], limit=1)
        assert "tags" in results[0]

    def test_returned_entries_are_copies(self):
        results = find_candidates(["hero"], limit=1)
        results[0]["resource_id"] = "mutated"
        again = find_candidates(["hero"], limit=1)
        assert again[0]["resource_id"] != "mutated"
