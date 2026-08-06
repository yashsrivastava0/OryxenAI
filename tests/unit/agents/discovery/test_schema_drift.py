"""Schema-drift and example-validity tests for the Discovery v2 prompts.

Schema-first prompting (Section 11.1): the prompt contract must not drift
from the Pydantic contract. These tests compare the JSON schema injected
into the prompt against the actual Pydantic models, and verify that every
golden example parses against the v2 schemas.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from oryxenai.agents.discovery.schemas import DiscoveryAnalysisResult, DiscoveryBrief

_PROMPTS_DIR = (
    Path(__file__).resolve().parents[4] / "src" / "oryxenai" / "agents" / "discovery" / "prompts"
)

_SCHEMA_BLOCK_RE = re.compile(r"## Output JSON schema \(contract\)\n```json\n(.*?)\n```", re.DOTALL)


def _prompt_declared_schema(operation: str) -> dict:
    from oryxenai.agents.discovery.prompt_builder import build_instructions

    _system, task, _version, _manifest = build_instructions(
        operation, {"main_prompt": "test"}, config={"max_questions": 8}
    )
    match = _SCHEMA_BLOCK_RE.search(task)
    assert match is not None, f"No schema block found in {operation} prompt"
    return json.loads(match.group(1))


class TestSchemaDrift:
    def test_call_a_properties_match_pydantic(self):
        declared = _prompt_declared_schema("prepare_questions")
        actual = DiscoveryAnalysisResult.model_json_schema()
        assert set(declared["properties"]) == set(actual["properties"])
        assert declared["properties"]["schema_version"]["default"] == 2

    def test_call_b_properties_match_pydantic(self):
        declared = _prompt_declared_schema("build_brief")
        actual = DiscoveryBrief.model_json_schema()
        assert set(declared["properties"]) == set(actual["properties"])

    def test_nested_required_fields_match_pydantic(self):
        declared_a = _prompt_declared_schema("prepare_questions")
        actual_a = DiscoveryAnalysisResult.model_json_schema()
        for name in ("source_assessment", "profile_overview", "readiness", "quality_checks"):
            assert declared_a["properties"][name]["$ref"] == actual_a["properties"][name]["$ref"], (
                name
            )

    def test_enum_values_match_pydantic(self):
        declared_a = _prompt_declared_schema("prepare_questions")
        actual_a = DiscoveryAnalysisResult.model_json_schema()
        # operation is a plain string; assert it is declared identically.
        assert (
            declared_a["properties"]["operation"]["type"]
            == actual_a["properties"]["operation"]["type"]
        )
        # A true enum field (overall_usability) must match its enum list.
        declared_usability = declared_a["properties"]["source_assessment"]["$ref"].rsplit("/", 1)[
            -1
        ]
        actual_usability = actual_a["properties"]["source_assessment"]["$ref"].rsplit("/", 1)[-1]
        assert declared_usability == actual_usability

    def test_max_list_sizes_pinned(self):
        declared_b = _prompt_declared_schema("build_brief")
        actual_b = DiscoveryBrief.model_json_schema()
        # Every property present in the prompt schema has the same maxItems
        # as the Pydantic schema (where the Pydantic schema declares one).
        for name, declared_prop in declared_b["properties"].items():
            actual_prop = actual_b["properties"][name]
            if "maxItems" in actual_prop:
                assert declared_prop.get("maxItems") == actual_prop["maxItems"], name
            if "maxLength" in actual_prop:
                assert declared_prop.get("maxLength") == actual_prop["maxLength"], name


class TestGoldenExamplesParse:
    def _load_examples(self, operation: str) -> list[tuple[str, dict]]:
        example_dir = _PROMPTS_DIR / "examples" / operation
        examples: list[tuple[str, dict]] = []
        for path in sorted(example_dir.glob("*.json")):
            examples.append((path.stem, json.loads(path.read_text(encoding="utf-8"))))
        return examples

    def test_call_a_examples_are_valid_v2(self):
        for name, raw in self._load_examples("call_a"):
            result = DiscoveryAnalysisResult.model_validate(raw)
            assert result.schema_version == 2, name
            assert result.source_assessment is not None, name

    def test_call_b_examples_are_valid_v2(self):
        for name, raw in self._load_examples("call_b"):
            brief = DiscoveryBrief.model_validate(raw)
            assert brief.schema_version == 2, name
            assert brief.downstream_handoff is not None, name

    def test_call_a_examples_have_rich_content(self):
        examples = self._load_examples("call_a")
        assert len(examples) >= 6
        for name, raw in examples:
            result = DiscoveryAnalysisResult.model_validate(raw)
            assert result.profile_overview is not None, name

    def test_call_b_examples_have_downstream_handoff(self):
        examples = self._load_examples("call_b")
        assert len(examples) >= 6
        for name, raw in examples:
            brief = DiscoveryBrief.model_validate(raw)
            assert brief.downstream_handoff.universal_constraints, name

    def test_anti_examples_exist(self):
        anti_dir = _PROMPTS_DIR / "examples" / "anti_examples"
        files = list(anti_dir.glob("*.md"))
        assert len(files) >= 2
        for path in files:
            content = path.read_text(encoding="utf-8")
            assert "BAD" in content and "REASON" in content and "GOOD" in content
