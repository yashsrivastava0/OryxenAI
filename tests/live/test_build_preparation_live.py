from __future__ import annotations

import os

import pytest

from oryxenai.agents.build_preparation.fixture import run_fixture
from oryxenai.agents.shared.model_client import build_provider_client
from oryxenai.core.settings import get_settings

pytestmark = [pytest.mark.live]


@pytest.mark.asyncio
async def test_live_build_preparation_fixture() -> None:
    if os.environ.get("RUN_LIVE_BUILD_PREPARATION") != "1":
        pytest.skip("Set RUN_LIVE_BUILD_PREPARATION=1 to use configured live providers.")

    canonical_settings = get_settings()
    model_client = build_provider_client("build_preparation", canonical_settings.models)
    if model_client is None:
        pytest.skip("Configured Build Preparation model profile is unavailable.")
    if canonical_settings.artifact_storage.provider == "memory":
        pytest.skip("Live Build Preparation verification requires configured object storage.")
    if not os.environ.get(canonical_settings.artifact_storage.access_key_env) or not os.environ.get(
        canonical_settings.artifact_storage.secret_key_env
    ):
        pytest.skip("Live Build Preparation verification requires artifact storage credentials.")
    settings = canonical_settings
    settings.build_preparation.fixture_output_dir = "output/live-build-preparation"
    try:
        result = await run_fixture(
            settings,
            live_model=True,
            live_providers=True,
            model_client=model_client,
        )
    finally:
        close = getattr(model_client, "aclose", None)
        if close is not None:
            await close()

    assert result["stage"] == "phase_3"
    assert result["status"] == "ready"
    assert result["model_calls"] >= 3
    assert result["materialization"]["manifest_path"] == "resources/manifest.json"
    assert result["package"]["archive_sha256"]
    assert result["package"]["artifact"]["provider"] == canonical_settings.artifact_storage.provider
    assert result["package"]["artifact"]["size_bytes"] == result["package"]["archive_size_bytes"]
    assert result["package"]["mirror_root"]
