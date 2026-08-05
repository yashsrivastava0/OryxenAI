"""Unit tests for Discovery prompt builder."""

from __future__ import annotations

from oryxenai.agents.discovery.prompt_builder import (
    PROMPT_VERSION_BUILD_BRIEF,
    PROMPT_VERSION_PREPARE_QUESTIONS,
    PROMPT_VERSION_REPAIR,
    build_instructions,
    build_repair_instructions,
    get_prompt_version,
    load_operation_prompt,
    load_system_prompt,
)


class TestLoadPrompts:
    def test_system_prompt_loads(self):
        prompt = load_system_prompt()
        assert "Discovery Agent" in prompt
        assert len(prompt) > 100

    def test_prepare_questions_loads(self):
        prompt = load_operation_prompt("prepare_questions")
        assert "Prepare the Discovery analysis" in prompt

    def test_build_brief_loads(self):
        prompt = load_operation_prompt("build_brief")
        assert "Build the editable Discovery brief" in prompt

    def test_repair_loads(self):
        prompt = load_operation_prompt("repair")
        assert "Correct the structured result" in prompt

    def test_unknown_operation_raises(self):
        import pytest

        with pytest.raises(ValueError):
            load_operation_prompt("nonexistent")


class TestBuildInstructions:
    def test_returns_tuple(self):
        system, task, version = build_instructions(
            "prepare_questions",
            {"main_prompt": "test"},
        )
        assert isinstance(system, str)
        assert isinstance(task, str)
        assert isinstance(version, str)

    def test_includes_source_data(self):
        source = {"main_prompt": "I need a portfolio.", "resume_text": "Engineer"}
        _system, task, _version = build_instructions("prepare_questions", source)
        assert "I need a portfolio" in task
        assert "Engineer" in task

    def test_source_data_escaped(self):
        source = {"main_prompt": "test with ]] in content"}
        _system, task, _version = build_instructions("prepare_questions", source)
        assert "]]" in task

    def test_prompt_version_correct(self):
        _, _, v1 = build_instructions("prepare_questions", {})
        assert v1 == PROMPT_VERSION_PREPARE_QUESTIONS
        _, _, v2 = build_instructions("build_brief", {})
        assert v2 == PROMPT_VERSION_BUILD_BRIEF

    def test_different_operations_different_prompts(self):
        _, task_a, _ = build_instructions("prepare_questions", {})
        _, task_b, _ = build_instructions("build_brief", {})
        assert task_a != task_b

    def test_config_included_in_prompt(self):
        config = {"max_questions": 8, "max_featured_projects": 3}
        _, task, _ = build_instructions("prepare_questions", {}, config=config)
        assert "max_questions" in task


class TestBuildRepairInstructions:
    def test_returns_tuple(self):
        system, task, version = build_repair_instructions({"field": "value"}, ["error1"])
        assert isinstance(system, str)
        assert isinstance(task, str)
        assert isinstance(version, str)

    def test_includes_validation_errors(self):
        _, task, _ = build_repair_instructions({}, ["error1", "error2"])
        assert "error1" in task
        assert "error2" in task

    def test_includes_original_output(self):
        original = {"goal": "test"}
        _, task, _ = build_repair_instructions(original, [])
        assert "test" in task


class TestGetPromptVersion:
    def test_prepare_questions_version(self):
        assert get_prompt_version("prepare_questions") == PROMPT_VERSION_PREPARE_QUESTIONS

    def test_build_brief_version(self):
        assert get_prompt_version("build_brief") == PROMPT_VERSION_BUILD_BRIEF

    def test_repair_version(self):
        assert get_prompt_version("repair") == PROMPT_VERSION_REPAIR

    def test_unknown_operation(self):
        assert get_prompt_version("unknown") == "discovery.unknown"
