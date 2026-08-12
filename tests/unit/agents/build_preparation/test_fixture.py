from __future__ import annotations

import pytest

from oryxenai.agents.build_preparation.fixture import run_fixture
from oryxenai.core.settings import Settings


@pytest.mark.asyncio
async def test_fixture_returns_routes_needs_and_complete_events() -> None:
    settings = Settings()
    settings.build_preparation.max_routes = 12
    payload = {
        "pages": [{"route_id": "home", "publication_status": "approved", "scenes": []}],
        "asset_briefs": [],
        "resource_candidates": [],
    }
    result = await run_fixture(settings, raw_override=payload)
    assert result["status"] == "ready"
    assert result["routes"][0]["route_id"] == "home"
    assert result["events"][-1]["event_id"] == "phase_3_complete"
    assert result["stage"] == "phase_3"
    assert result["materialization"]["manifest_path"] == "resources/manifest.json"
    assert result["package"]["archive_sha256"]
    assert result["package"]["mirror_root"]
