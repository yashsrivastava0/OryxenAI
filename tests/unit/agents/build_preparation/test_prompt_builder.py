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
