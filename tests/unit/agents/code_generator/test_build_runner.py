from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from oryxenai.agents.code_generator.core import build_runner
from oryxenai.agents.code_generator.core.process_runner import ProcessResult


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


@pytest.mark.asyncio
async def test_build_runner_classifies_vite_windows_spawn_denial_as_infrastructure(
    monkeypatch, tmp_path: Path
) -> None:
    async def fake_run_command(*_args, **_kwargs):
        return ProcessResult(
            command=("npm", "run", "build"),
            returncode=1,
            stdout="",
            stderr=(
                "Error: spawn EPERM\n"
                "at windowsSafeRealPathSync (vite/dist/node/chunks/dep.js:1:1)\n"
                "at optimizeSafeRealPathSync (vite/dist/node/chunks/dep.js:2:1)"
            ),
        )

    monkeypatch.setattr(build_runner, "run_command", fake_run_command)
    settings = SimpleNamespace(
        code_generator_verification=SimpleNamespace(
            build_timeout_seconds=1.0, max_output_bytes=1024
        )
    )

    _result, issue = await build_runner._run(
        ["npm", "run", "build"],
        repo_dir=tmp_path,
        settings=settings,
        timeout_name="build_timeout_seconds",
        phase="build",
    )

    assert issue is not None
    assert issue.code == "VITE_NODE_SPAWN_EPERM"
    assert issue.owner == "infrastructure"
    assert build_runner.is_vite_windows_spawn_failure([issue])
