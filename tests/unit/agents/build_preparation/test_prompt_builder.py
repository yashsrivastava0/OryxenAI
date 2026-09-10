from __future__ import annotations

from oryxenai.agents.build_preparation.prompt_builder import build_instructions


def test_prompt_builder_keeps_untrusted_input_delimited_and_returns_manifest() -> None:
    system, task, version, manifest = build_instructions({"untrusted": "]]"})
    other_system, other_task, other_version, other_manifest = build_instructions(
        {"untrusted": "different"}
    )

    assert "trusted" in system.lower()
    assert "<untrusted_input>" in task
    assert "]]" not in task
    assert system == other_system
    assert task == other_task
    assert version == other_version
    assert manifest == other_manifest
    assert version.startswith("build_preparation.compose_visual_brief")
    assert set(manifest) == {"system.md", "compose_visual_brief.md", "schema"}


def test_prompt_builder_requires_detailed_route_guidance() -> None:
    system, task, _version, _manifest = build_instructions({"routes": []})

    assert "approved content and visual direction are authorized inputs" in system
    assert "The visual brief must be detailed enough" in system
    assert "developed" in task
    assert "every approved route" in task
