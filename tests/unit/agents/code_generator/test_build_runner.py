from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from oryxenai.agents.code_generator.core import build_runner


@pytest.mark.asyncio
async def test_clean_build_serializes_package_installs(monkeypatch, tmp_path: Path) -> None:
    active_installs = 0
    maximum_concurrent_installs = 0

    async def fake_run(*args, **kwargs):
        nonlocal active_installs, maximum_concurrent_installs
        if kwargs["phase"] == "install":
            active_installs += 1
            maximum_concurrent_installs = max(maximum_concurrent_installs, active_installs)
            await asyncio.sleep(0.02)
            active_installs -= 1
        return SimpleNamespace(timed_out=False, returncode=0, combined_output=""), None

    monkeypatch.setattr(build_runner, "_run", fake_run)
    monkeypatch.setattr(build_runner, "build_manifest", lambda *args, **kwargs: object())
    settings = SimpleNamespace(
        code_generator_verification=SimpleNamespace(
            install_command=["npm", "ci"],
            typecheck_command=["npm", "run", "typecheck"],
            format_command=[],
            build_command=["npm", "run", "build"],
            install_timeout_seconds=1.0,
            typecheck_timeout_seconds=1.0,
            format_timeout_seconds=1.0,
            build_timeout_seconds=1.0,
            max_output_bytes=1024,
            max_artifact_bytes=1024,
            reject_source_maps=True,
        ),
        code_generator_dependencies=SimpleNamespace(npm_cache_root=""),
    )
    repositories = [tmp_path / "one", tmp_path / "two"]
    results = await asyncio.gather(
        *(
            build_runner.run_clean_build(
                repository,
                settings=settings,
                candidate_identity_hash=f"candidate-{index}",
            )
            for index, repository in enumerate(repositories)
        )
    )

    assert all(manifest is not None and not diagnostics for manifest, diagnostics in results)
    assert maximum_concurrent_installs == 1
