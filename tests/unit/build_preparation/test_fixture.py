from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from oryxenai.build_preparation.fixture import (
    FixturePreparationError,
    build_fixture_content,
    load_fixture,
    run_fixture,
)
from oryxenai.build_preparation.storage import MemoryArtifactStore
from oryxenai.core.settings import Settings


def _settings() -> Settings:
    settings = Settings()
    settings.build_preparation.fixture_enabled = True
    settings.build_preparation.fixture_upload = False
    return settings


def test_checked_in_visual_fixture_loads_and_normalizes_runtime_metadata() -> None:
    visual, payload, digest, path = load_fixture(_settings())
    assert path.name == "visual_design_director_Output.md"
    assert visual.status.value == "design_review"
    assert "elapsed_seconds" not in payload
    assert len(digest) == 64
    assert len(visual.pages) == 1


def test_fixture_content_is_explicitly_unapproved_and_preserves_public_sections() -> None:
    visual, _, _, _ = load_fixture(_settings())
    content = build_fixture_content(visual)
    assert content.status.value == "content_review"
    assert content.approved is None
    assert content.page_content_packs[0].sections[0].section_id == "home:hero"
    assert content.claim_grounding == []


def test_fixture_runner_builds_non_publishable_bundle_without_network() -> None:
    store = MemoryArtifactStore()
    result = asyncio.run(run_fixture(_settings(), artifact_store=store))
    repeat = asyncio.run(run_fixture(_settings(), artifact_store=store))
    assert result["status"] == "succeeded"
    assert result["publishable"] is False
    assert result["input"]["visual_status"] == "design_review"
    assert result["blueprint"]["route_map"]
    assert result["page_packets"]
    assert result["bundle_sha256"]
    assert result["bundle_sha256"] == repeat["bundle_sha256"]
    assert result["bundle"]["object_key"] == repeat["bundle"]["object_key"]
    assert any("fixture mode" in warning for warning in result["warnings"])
    assert any("claim" in warning for warning in result["warnings"])


def test_fixture_runner_rejects_disabled_configuration() -> None:
    settings = _settings()
    settings.build_preparation.fixture_enabled = False
    with pytest.raises(FixturePreparationError) as error:
        asyncio.run(run_fixture(settings, artifact_store=MemoryArtifactStore()))
    assert error.value.code == "FIXTURE_DISABLED"


def test_fixture_runner_accepts_browser_provided_vdd_output() -> None:
    settings = _settings()
    visual, payload, _, _ = load_fixture(settings)
    payload["user_summary"] = "Browser supplied fixture"
    result = asyncio.run(
        run_fixture(settings, artifact_store=MemoryArtifactStore(), raw_override=payload)
    )
    assert result["status"] == "succeeded"
    assert result["input"]["path"] == "browser-provided JSON"
    assert result["input"]["sha256"] != ""
    assert visual.pages


def test_fixture_loader_rejects_invalid_json() -> None:
    settings = _settings()
    bad = Path("scratch") / "invalid-json-fixture.json"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("not json", encoding="utf-8")
    settings.build_preparation.fixture_input_path = str(bad)
    with pytest.raises(FixturePreparationError) as error:
        try:
            load_fixture(settings)
        finally:
            bad.unlink(missing_ok=True)
    assert error.value.code == "FIXTURE_INPUT_INVALID"


def test_fixture_loader_rejects_malformed_checked_in_shape() -> None:
    # This test uses a repository-relative replacement so the path policy is
    # exercised independently from the schema validator.
    settings = _settings()
    relative = Path("scratch") / "invalid-vdd-fixture.json"
    relative.parent.mkdir(parents=True, exist_ok=True)
    relative.write_text(json.dumps({"status": "not-a-visual-state"}), encoding="utf-8")
    settings.build_preparation.fixture_input_path = str(relative)
    try:
        with pytest.raises(FixturePreparationError) as error:
            load_fixture(settings)
        assert error.value.code == "FIXTURE_SCHEMA_INVALID"
    finally:
        relative.unlink(missing_ok=True)
