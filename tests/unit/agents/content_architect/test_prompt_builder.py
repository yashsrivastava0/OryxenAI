"""Unit tests for the Content Architect prompt builder."""

from __future__ import annotations

import pytest

from oryxenai.agents.content_architect.prompt_builder import (
    PROMPT_VERSION_INTEGRATE_CONTENT,
    PROMPT_VERSION_PLAN_CONTENT,
    PROMPT_VERSION_WRITE_PAGES,
    build_instructions,
    get_prompt_version,
)


class TestBuildInstructions:
    def test_plan_content_returns_full_tuple(self):
        system, task, version, manifest = build_instructions(
            "plan_content", {"approved_brief_title": "Test"}
        )
        assert system
        assert "<role>" in system
        assert task
        assert version == PROMPT_VERSION_PLAN_CONTENT
        assert manifest

    def test_write_pages_returns_full_tuple(self):
        system, task, version, _manifest = build_instructions(
            "write_pages", {"claim_grounding": []}
        )
        assert system
        assert task
        assert version == PROMPT_VERSION_WRITE_PAGES

    def test_integrate_content_returns_full_tuple(self):
        system, task, version, _manifest = build_instructions(
            "integrate_content", {"page_content": {}}
        )
        assert system
        assert task
        assert version == PROMPT_VERSION_INTEGRATE_CONTENT

    def test_unknown_operation_raises(self):
        with pytest.raises(ValueError, match="Unknown Content Architect operation"):
            build_instructions("nope", {})

    def test_schema_injected_into_task(self):
        _, task, _, _ = build_instructions("plan_content", {"approved_brief_title": "x"})
        assert "Output JSON schema" in task
        assert "page_content" in task
        assert "claim_grounding" in task
        assert "route_plan" not in task
        assert "page_content_packs" not in task

    def test_dynamic_input_is_left_out_of_stable_task(self):
        _, task, _, _ = build_instructions("plan_content", {"approved_brief_title": "]] inside"})
        _, other_task, _, _ = build_instructions(
            "plan_content", {"approved_brief_title": "different"}
        )
        assert "<untrusted_input>" in task
        assert "]] inside" not in task
        assert task == other_task

    def test_unknown_input_accepted(self):
        _system, task, _, _ = build_instructions(
            "plan_content",
            {"approved_brief_title": "x", "unexpected": {"unique_user_payload_marker": True}},
        )
        assert task
        assert "unique_user_payload_marker" not in task

    def test_system_prompt_loaded_from_file(self):
        system, _task, _version, _manifest = build_instructions(
            "plan_content", {"approved_brief_title": "x"}
        )
        assert "OryxenAI Content Architect" in system
        assert "<trust_boundary>" in system

    def test_never_re_interviews_language_present(self):
        system, _task, _version, _manifest = build_instructions(
            "plan_content", {"approved_brief_title": "x"}
        )
        assert "re-interview" in system

    def test_source_use_and_detail_guidance_is_explicit(self):
        system, _task, _version, _manifest = build_instructions(
            "plan_content", {"approved_brief_title": "x"}
        )
        assert "Use those facts fully" in system
        assert "Write finished copy, not placeholders" in system


class TestTemplateRulesReachEveryOperation:
    """Only one operation file loads per call, so shared rules live in system.md."""

    @pytest.mark.parametrize("operation", ["plan_content", "write_pages", "integrate_content"])
    def test_page_template_contract_is_in_every_call(self, operation):
        system, _task, _version, _manifest = build_instructions(operation, {})
        assert "<page_template>" in system
        assert "EXACTLY 4 entries" in system
        assert "organization NAMES ONLY" in system
        assert "<claim_binding>" in system
        assert "<coverage_ledger>" in system

    def test_prompts_no_longer_describe_routes_or_unrenderable_sections(self):
        for operation in ("plan_content", "write_pages", "integrate_content"):
            system, task, _version, _manifest = build_instructions(operation, {})
            text = system + task
            assert "page_content_packs" not in text
            assert "public_content_manifest" not in text
            assert "work-sample stories" not in text


class TestPromptVersion:
    def test_versions_are_stable(self):
        assert get_prompt_version("plan_content") == PROMPT_VERSION_PLAN_CONTENT
        assert get_prompt_version("write_pages") == PROMPT_VERSION_WRITE_PAGES
        assert get_prompt_version("integrate_content") == PROMPT_VERSION_INTEGRATE_CONTENT
        assert get_prompt_version("unknown") == "content_architect.unknown"

    def test_manifest_hashes_content(self):
        _, _, _, manifest1 = build_instructions("plan_content", {"approved_brief_title": "x"})
        _, _, _, manifest2 = build_instructions("plan_content", {"approved_brief_title": "y"})
        assert set(manifest1) == {"system.md", "plan_content.md", "schema"}
        for key in ("system.md", "plan_content.md", "schema"):
            assert manifest1[key] == manifest2[key]
            assert isinstance(manifest1[key], str)
            assert len(manifest1[key]) == 16

    def test_manifest_hashes_write_pages_prompt(self):
        _, _, _, manifest = build_instructions("write_pages", {"route_plan": []})
        assert set(manifest) == {"system.md", "write_pages.md", "schema"}
        assert len(manifest["write_pages.md"]) == 16
