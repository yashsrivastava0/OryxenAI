from __future__ import annotations

import json
from pathlib import Path

import pytest

from oryxenai.agents.build_preparation import fixture_runs
from oryxenai.agents.build_preparation.fixture import (
    _content_snapshot_path,
    _fixture_path,
    _load_content_snapshot,
    _load_default,
    fixture_storage_preflight,
    run_fixture,
)
from oryxenai.core.settings import Settings


@pytest.mark.asyncio
async def test_fixture_returns_routes_needs_and_complete_events(tmp_path: Path) -> None:
    settings = Settings()
    settings.build_preparation.max_routes = 12
    settings.build_preparation.fixture_upload = False
    settings.build_preparation.fixture_output_dir = str(tmp_path)
    payload = {
        "approved": {"visual_direction_hash": "visual-hash"},
        "source_ref": {"content_architect_content_hash": "content-hash"},
        "pages": [{"route_id": "home", "publication_status": "approved", "scenes": []}],
        "asset_briefs": [],
        "resource_candidates": [],
    }
    result = await run_fixture(
        settings,
        raw_override=payload,
        content_architect_override={
            "page_content_packs": [{"route_id": "home", "sections": [{"section_id": "hero"}]}]
        },
        local_result_root=str(tmp_path / "fixture-result"),
    )
    assert result["status"] == "ready"
    assert result["routes"][0]["route_id"] == "home"
    assert result["events"][-1]["event_id"] == "phase_3_complete"
    assert result["stage"] == "phase_3"
    assert result["materialization"]["manifest_path"] == "resources/manifest.json"
    assert result["materialization"]["resource_plan_path"] == "resources/plan.json"
    assert result["handoff_report"]["handoff_eligible"] is True
    assert (tmp_path / "fixture-result" / "build-context" / "handoff-report.json").is_file()
    assert result["package"]["archive_sha256"]
    assert result["package"]["mirror_root"]
    assert (tmp_path / "fixture-result" / "build-context" / "manifest.json").is_file()
    assert (tmp_path / "fixture-result" / "build-pack.zip").is_file()


def test_fixture_auto_picks_attached_content_and_visual_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    attached = tmp_path / "Input-Output-Of-Engine"
    attached.mkdir()
    visual_path = attached / "Visual Design Director output.md"
    content_path = attached / "Content Architect output.MD"
    visual_path.write_text(json.dumps({"status": "approved", "pages": []}), encoding="utf-8")
    content_path.write_text(
        json.dumps({"status": "approved", "route_plan": [{"route_id": "home"}]}),
        encoding="utf-8",
    )

    settings = Settings()
    settings.build_preparation.fixture_input_path = str(tmp_path / "old-vdd-output.md")
    settings.build_preparation.fixture_content_input_path = str(tmp_path / "old-ca-output.md")

    assert _fixture_path(settings) == visual_path
    assert _content_snapshot_path(settings) == content_path
    assert _load_default(settings)["status"] == "approved"
    assert _load_content_snapshot(settings)["route_plan"][0]["route_id"] == "home"
    preflight = fixture_storage_preflight(settings)
    assert preflight["inputs"]["visual_design_director"]["status"] == "ready"
    assert preflight["inputs"]["content_architect"]["status"] == "ready"


def test_fixture_diagnostics_retry_transient_windows_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "diagnostics.json"
    real_replace = fixture_runs.os.replace
    attempts = 0

    def flaky_replace(source: str | Path, destination: str | Path) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PermissionError("transient Windows file lock")
        real_replace(source, destination)

    monkeypatch.setattr(fixture_runs.os, "replace", flaky_replace)
    fixture_runs.FixtureRunManager._atomic_json(path, {"status": "ready"})

    assert attempts == 2
    assert json.loads(path.read_text(encoding="utf-8")) == {"status": "ready"}
    assert list(tmp_path.glob("*.tmp")) == []
