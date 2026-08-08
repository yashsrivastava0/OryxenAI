"""Unit tests for the Visual Design Director prompt builder."""

from __future__ import annotations

import pytest

from oryxenai.agents.visual_design_director.prompt_builder import (
    PROMPT_VERSION_DIRECT_PAGES,
    PROMPT_VERSION_ESTABLISH,
    PROMPT_VERSION_INTEGRATE,
    build_instructions,
    get_prompt_version,
)


class TestBuildInstructions:
    def test_establish_visual_language_returns_full_tuple(self):
        system, task, version, manifest = build_instructions(
            "establish_visual_language", {"presentation_mode": "single_page"}
        )
        assert system
        assert "<role>" in system
        assert task
        assert version == PROMPT_VERSION_ESTABLISH
        assert manifest

    def test_direct_page_experience_returns_full_tuple(self):
        system, task, version, _manifest = build_instructions(
            "direct_page_experience", {"route_plan": []}
        )
        assert system
        assert task
        assert version == PROMPT_VERSION_DIRECT_PAGES

    def test_integrate_site_experience_returns_full_tuple(self):
        system, task, version, _manifest = build_instructions(
            "integrate_site_experience", {"pages": []}
        )
        assert system
        assert task
        assert version == PROMPT_VERSION_INTEGRATE

    def test_unknown_operation_raises(self):
        with pytest.raises(ValueError, match="Unknown Visual Design Director operation"):
            build_instructions("nope", {})

    def test_schema_injected_into_task(self):
        _, task, _, _ = build_instructions(
            "establish_visual_language", {"presentation_mode": "single_page"}
        )
        assert "Output JSON schema" in task
        assert "visual_language" in task
        assert "resource_candidates" in task

    def test_user_input_included_as_cdata(self):
        _, task, _, _ = build_instructions(
            "establish_visual_language", {"presentation_mode": "]] inside"}
        )
        assert "user_input" in task
        assert "]]>]]<![CDATA[" in task

    def test_unknown_input_accepted(self):
        _system, task, _, _ = build_instructions(
            "establish_visual_language",
            {"presentation_mode": "x", "unexpected": {"anything": True}},
        )
        assert "anything" in task

    def test_system_prompt_loaded_from_file(self):
        system, _task, _version, _manifest = build_instructions(
            "establish_visual_language", {"presentation_mode": "x"}
        )
        assert "OryxenAI Visual Design Director" in system
        assert "<trust_boundary>" in system

    def test_never_fabricate_language_present(self):
        system, _task, _version, _manifest = build_instructions(
            "establish_visual_language", {"presentation_mode": "x"}
        )
        assert "never_fabricate" in system or "Never invent" in system

    def test_resource_catalogue_rule_present(self):
        system, _task, _version, _manifest = build_instructions(
            "establish_visual_language", {"presentation_mode": "x"}
        )
        assert "resource_id" in system


class TestPromptVersion:
    def test_versions_are_stable(self):
        assert get_prompt_version("establish_visual_language") == PROMPT_VERSION_ESTABLISH
        assert get_prompt_version("direct_page_experience") == PROMPT_VERSION_DIRECT_PAGES
        assert get_prompt_version("integrate_site_experience") == PROMPT_VERSION_INTEGRATE
        assert get_prompt_version("unknown") == "visual_design_director.unknown"

    def test_manifest_hashes_content(self):
        _, _, _, manifest1 = build_instructions(
            "establish_visual_language", {"presentation_mode": "x"}
        )
        _, _, _, manifest2 = build_instructions(
            "establish_visual_language", {"presentation_mode": "y"}
        )
        assert set(manifest1) == {"system.md", "establish_visual_language.md", "schema"}
        for key in ("system.md", "establish_visual_language.md", "schema"):
            assert manifest1[key] == manifest2[key]
            assert isinstance(manifest1[key], str)
            assert len(manifest1[key]) == 16

    def test_manifest_hashes_direct_page_experience_prompt(self):
        _, _, _, manifest = build_instructions("direct_page_experience", {"route_plan": []})
        assert set(manifest) == {"system.md", "direct_page_experience.md", "schema"}
        assert len(manifest["direct_page_experience.md"]) == 16
