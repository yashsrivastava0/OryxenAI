"""Unit tests for Discovery prompt builder (v2 modular architecture)."""

from __future__ import annotations

import pytest

from oryxenai.agents.discovery.prompt_builder import (
    PROMPT_VERSION_CALL_A,
    PROMPT_VERSION_CALL_B,
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
        assert "Build the editable, strategic Discovery brief" in prompt

    def test_repair_loads(self):
        prompt = load_operation_prompt("repair")
        assert "Correct the structured result" in prompt

    def test_unknown_operation_raises(self):
        with pytest.raises(ValueError):
            load_operation_prompt("nonexistent")


class TestBuildInstructions:
    def test_returns_quadruple(self):
        system, task, version, manifest = build_instructions(
            "prepare_questions",
            {"main_prompt": "test"},
        )
        assert isinstance(system, str)
        assert isinstance(task, str)
        assert isinstance(version, str)
        assert isinstance(manifest, dict)
        assert manifest

    def test_includes_source_data(self):
        source = {"main_prompt": "I need a portfolio.", "resume_text": "Engineer"}
        _system, task, _version, _manifest = build_instructions("prepare_questions", source)
        assert "I need a portfolio" in task
        assert "Engineer" in task

    def test_source_data_escaped(self):
        source = {"main_prompt": "test with ]] in content"}
        _system, task, _version, _manifest = build_instructions("prepare_questions", source)
        assert "<source_packet" in task
        assert "CDATA" in task

    def test_static_material_precedes_dynamic_packet(self):
        _system, task, _version, _manifest = build_instructions(
            "prepare_questions", {"main_prompt": "dynamic user data"}
        )
        static_marker = task.index("Output JSON schema")
        dynamic_marker = task.index("source_packet")
        assert static_marker < dynamic_marker

    def test_prompt_version_correct(self):
        _, _, v1, _ = build_instructions("prepare_questions", {})
        assert v1 == PROMPT_VERSION_CALL_A
        _, _, v2, _ = build_instructions("build_brief", {})
        assert v2 == PROMPT_VERSION_CALL_B

    def test_different_operations_different_prompts(self):
        _, task_a, _, _ = build_instructions("prepare_questions", {})
        _, task_b, _, _ = build_instructions("build_brief", {})
        assert task_a != task_b

    def test_config_included_in_prompt(self):
        config = {"max_questions": 8, "max_featured_projects": 3}
        _, task, _, _ = build_instructions("prepare_questions", {}, config=config)
        assert "max_questions" in task

    def test_schema_injected_into_output_contract(self):
        _, task_a, _, _ = build_instructions("prepare_questions", {})
        assert '"operation"' in task_a or "schema_version" in task_a
        _, task_b, _, _ = build_instructions("build_brief", {})
        assert "schema_version" in task_b

    def test_module_manifest_stable(self):
        _, _, _, manifest1 = build_instructions("prepare_questions", {"main_prompt": "x"})
        _, _, _, manifest2 = build_instructions("prepare_questions", {"main_prompt": "y"})
        assert manifest1 == manifest2

    def test_examples_selected_for_sparse_profile(self):
        source = {"main_prompt": "Need portfolio", "resume_text": "short"}
        _system, task, _version, _manifest = build_instructions("prepare_questions", source)
        assert "Reference examples" in task

    def test_anti_examples_not_in_runtime_prompt(self):
        _system, task, _version, _manifest = build_instructions("prepare_questions", {})
        assert "BAD QUESTION" not in task


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

    def test_includes_valid_ids_and_operation(self):
        _, task, _ = build_repair_instructions(
            {},
            ["e1"],
            valid_source_ids=["main_prompt"],
            valid_fact_ids=["fact-1"],
            operation_name="build_brief",
        )
        assert "main_prompt" in task
        assert "fact-1" in task
        assert "build_brief" in task

    def test_bounded_instructions_present(self):
        _, task, _ = build_repair_instructions({"goal": "x"}, ["error1"])
        assert "Correct ONLY the listed validation failures" in task
        assert "Do not add professional facts" in task
        assert "Do not invent" in task


class TestGetPromptVersion:
    def test_prepare_questions_version(self):
        assert get_prompt_version("prepare_questions") == PROMPT_VERSION_CALL_A

    def test_build_brief_version(self):
        assert get_prompt_version("build_brief") == PROMPT_VERSION_CALL_B

    def test_repair_version(self):
        assert get_prompt_version("repair") == PROMPT_VERSION_REPAIR

    def test_unknown_operation(self):
        assert get_prompt_version("unknown") == "discovery.unknown"
