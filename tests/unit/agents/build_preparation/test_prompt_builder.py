from __future__ import annotations

from oryxenai.agents.build_preparation.prompt_builder import build_instructions


def test_prompt_builder_keeps_untrusted_input_delimited_and_returns_manifest() -> None:
    system, task, version, manifest = build_instructions(
        "compose_resource_queries", {"untrusted": "]]"}
    )

    assert "trusted" in system.lower()
    assert '<user_input trust="untrusted"' in task
    assert "]]<![CDATA[" in task
    assert version.startswith("build_preparation.compose_resource_queries")
    assert set(manifest) == {"system.md", "compose_resource_queries.md", "schema"}
