from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import UUID

from oryxenai.agents.shared.output_export import export_agent_result


def test_export_writes_result_and_redacts_cache_identity(tmp_path) -> None:
    settings = SimpleNamespace(
        model_cache=SimpleNamespace(
            export_enabled=True,
            output_root=str(tmp_path),
        )
    )

    destination = export_agent_result(
        settings,
        agent_key="discovery",
        run_id=UUID("00000000-0000-0000-0000-000000000001"),
        output={"brief_markdown": "# A grounded brief"},
        model_metadata={
            "cache": {
                "cache_hit": True,
                "cache_key": "private-cache-key",
                "input_fingerprint": "private-input-fingerprint",
            },
            "cost_telemetry": {"estimated_cost": 0.01},
        },
    )

    assert destination is not None
    result_path = tmp_path / "discovery" / "00000000-0000-0000-0000-000000000001" / "result.json"
    metadata_path = result_path.with_name("run-metadata.json")
    assert (
        json.loads(result_path.read_text(encoding="utf-8"))["brief_markdown"]
        == "# A grounded brief"
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["model_metadata"]["cache"]["cache_hit"] is True
    assert metadata["model_metadata"]["cost_telemetry"]["estimated_cost"] == 0.01
    assert "cache_key" not in metadata["model_metadata"]["cache"]
    assert "input_fingerprint" not in metadata["model_metadata"]["cache"]
