"""Unit tests for the Discovery prompt builder."""

from __future__ import annotations

import pytest

from oryxenai.agents.discovery.prompt_builder import (
    PROMPT_VERSION_BRIEF,
    PROMPT_VERSION_QUESTIONS,
    build_instructions,
    get_prompt_version,
)


class TestBuildInstructions:
    def test_understand_and_question_returns_full_tuple(self):
        system, task, version, manifest = build_instructions(
            "understand_and_question", {"message": "I am a developer"}
        )
        assert system
        assert "<role>" in system
        assert task
        assert version == PROMPT_VERSION_QUESTIONS
        assert manifest

    def test_build_or_revise_brief_returns_full_tuple(self):
        system, task, version, _manifest = build_instructions(
            "build_or_revise_brief",
            {"message": "I am a developer", "answers": {}, "existing_brief": ""},
        )
        assert system
        assert task
        assert version == PROMPT_VERSION_BRIEF

    def test_unknown_operation_raises(self):
        with pytest.raises(KeyError):
            build_instructions("nope", {})

    def test_schema_injected_into_task(self):
        _, task, _, _ = build_instructions("understand_and_question", {"message": "x"})
        assert "Output JSON schema" in task
        assert "questions" in task
        assert "assistant_message" in task

    def test_brief_schema_injected(self):
        _, task, _, _ = build_instructions(
            "build_or_revise_brief", {"message": "x", "existing_brief": ""}
        )
        assert "Output JSON schema" in task
        assert "brief_markdown" in task

    def test_user_input_included_as_cdata(self):
        _, task, _, _ = build_instructions("understand_and_question", {"message": "]] inside"})
        assert "user_input" in task
        assert "]]>]]<![CDATA[" in task

    def test_unknown_input_accepted(self):
        _system, task, _, _ = build_instructions(
            "understand_and_question",
            {"message": "x", "unexpected": {"anything": True}},
        )
        assert "anything" in task

    def test_system_prompt_loaded_from_file(self):
        system, _task, _version, _manifest = build_instructions(
            "understand_and_question", {"message": "x"}
        )
        assert "OryxenAI Discovery" in system
        assert "<trust_boundary>" in system


class TestPromptVersion:
    def test_versions_are_stable(self):
        assert get_prompt_version("understand_and_question") == PROMPT_VERSION_QUESTIONS
        assert get_prompt_version("build_or_revise_brief") == PROMPT_VERSION_BRIEF
        assert get_prompt_version("prepare_questions") == PROMPT_VERSION_QUESTIONS
        assert get_prompt_version("build_brief") == PROMPT_VERSION_BRIEF
        assert get_prompt_version("unknown") == "discovery.unknown"

    def test_manifest_hashes_content(self):
        _, _, _, manifest1 = build_instructions("understand_and_question", {"message": "x"})
        _, _, _, manifest2 = build_instructions("understand_and_question", {"message": "y"})
        assert set(manifest1) == {"system.md", "understand_and_question.md", "schema"}
        for key in ("system.md", "understand_and_question.md", "schema"):
            assert manifest1[key] == manifest2[key]
            assert isinstance(manifest1[key], str)
            assert len(manifest1[key]) == 16

    def test_manifest_hashes_brief_prompt(self):
        _, _, _, manifest = build_instructions(
            "build_or_revise_brief", {"message": "x", "existing_brief": ""}
        )
        assert set(manifest) == {"system.md", "build_or_revise_brief.md", "schema"}
        assert len(manifest["build_or_revise_brief.md"]) == 16
        assert len(manifest["system.md"]) == 16
