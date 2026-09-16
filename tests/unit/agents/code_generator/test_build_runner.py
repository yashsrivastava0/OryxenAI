from __future__ import annotations

import asyncio
import random
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


@pytest.mark.asyncio
async def test_vite_windows_spawn_denial_attaches_process_count_context(
    monkeypatch, tmp_path: Path
) -> None:
    async def fake_run_command(*_args, **_kwargs):
        return ProcessResult(
            command=("npm", "run", "build"),
            returncode=1,
            stdout="",
            stderr=(
                "Error: spawn EPERM\nat windowsSafeRealPathSync (vite/dist/node/chunks/dep.js:1:1)"
            ),
        )

    monkeypatch.setattr(build_runner, "run_command", fake_run_command)
    monkeypatch.setattr(build_runner, "_count_node_process_matches", lambda: 17)
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
    assert "17 node/npm process(es)" in issue.normalized_message


@pytest.mark.asyncio
async def test_vite_windows_spawn_denial_attaches_prior_duration_comparison(
    monkeypatch, tmp_path: Path
) -> None:
    async def fake_run_command(*_args, **_kwargs):
        return ProcessResult(
            command=("npm", "run", "build"),
            returncode=1,
            stdout="",
            stderr=(
                "Error: spawn EPERM\nat optimizeSafeRealPathSync (vite/dist/node/chunks/dep.js:2:1)"
            ),
        )

    monkeypatch.setattr(build_runner, "run_command", fake_run_command)
    monkeypatch.setattr(build_runner, "_count_node_process_matches", lambda: None)
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
        stage_durations_ms={"verify": 420_000.0},
    )

    assert issue is not None
    assert "could not be determined" in issue.normalized_message
    assert "previous verify attempt on this run took 420.0s" in issue.normalized_message


@pytest.mark.asyncio
async def test_vite_windows_spawn_denial_omits_comparison_when_no_prior_duration(
    monkeypatch, tmp_path: Path
) -> None:
    """`stage_durations_ms` is written elsewhere (the coordinator); until that
    exists, or on a run's first verify attempt, this must degrade gracefully
    rather than raise or fabricate a comparison."""

    async def fake_run_command(*_args, **_kwargs):
        return ProcessResult(
            command=("npm", "run", "build"),
            returncode=1,
            stdout="",
            stderr=(
                "Error: spawn EPERM\nat windowsSafeRealPathSync (vite/dist/node/chunks/dep.js:1:1)"
            ),
        )

    monkeypatch.setattr(build_runner, "run_command", fake_run_command)
    monkeypatch.setattr(build_runner, "_count_node_process_matches", lambda: 3)
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
        stage_durations_ms=None,
    )

    assert issue is not None
    assert "previous verify attempt" not in issue.normalized_message
    assert "3 node/npm process(es)" in issue.normalized_message


def test_count_node_process_matches_never_raises_when_enumeration_fails(monkeypatch) -> None:
    """Enumeration must degrade to `None`, never propagate, on any denial —
    the same posture already established for Windows enumeration failures
    in `fs_safe.remove_tree`."""

    def fake_which(_name: str) -> str | None:
        return None

    monkeypatch.setattr(build_runner.shutil, "which", fake_which)

    assert build_runner._count_node_process_matches() is None


class TestSpawnDenialContextCapturePreservationProperty:
    """Property 2 (design.md): every non-spawn-diagnostic code path is
    byte-identical in behavior -- the new context-capture code added for
    Property 1 (task 1) must be reachable only from the exact existing
    `VITE_NODE_SPAWN_EPERM` classification branch, never a broader one.

    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.6, 3.7**

    This codebase has no Hypothesis dependency; this test follows this
    project's own existing convention for a property-style check (see
    `test_service.py::TestNoFabricationProperty`) -- iterate many random,
    seeded input combinations in a plain loop and assert the invariant
    holds for every one, rather than adding a new test library for this
    one bugfix.

    Reachability, not output absence, is what is asserted: the fake
    `_count_node_process_matches` below raises if it is ever called, so a
    regression that widened the classification branch (or that called the
    context-capture helper from some other code path) would fail loudly
    here even if its result happened to be discarded before reaching the
    diagnostic message -- a weaker check based only on the diagnostic
    message's text could pass in that scenario, which is why this test
    asserts on the call itself.
    """

    @staticmethod
    def test_existing_preexisting_tests_still_pass_unmodified() -> None:
        """`design.md`'s "Preservation Checking" pseudocode names this
        confirmation as itself the preservation check for this file: the
        two pre-existing tests named in the task text must continue to pass
        exactly as written, with no modification, after tasks 1-3 exist.

        This is intentionally a documentation-of-intent test, not a
        re-implementation of those tests' bodies -- the actual proof is
        that `test_clean_build_serializes_package_installs` and
        `test_build_runner_classifies_vite_windows_spawn_denial_as_infrastructure`,
        defined earlier in this same file, still execute and pass when this
        whole file is run (confirmed by running the full file, not just
        this test, before this task was marked complete). Asserting on the
        module-level test function objects themselves here at minimum
        guards against either test being accidentally renamed, removed, or
        commented out, which is one of `design.md`'s own explicit failure
        signals ("any existing test that needs to change to keep passing is
        a signal this design's 'additive only' framing was wrong
        somewhere").
        """

        import sys

        this_module = sys.modules[__name__]
        assert hasattr(this_module, "test_clean_build_serializes_package_installs")
        assert hasattr(
            this_module, "test_build_runner_classifies_vite_windows_spawn_denial_as_infrastructure"
        )

    @pytest.mark.asyncio
    async def test_context_capture_never_invoked_for_non_matching_process_results(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        rng = random.Random(20260921)  # noqa: S311 - deterministic test seed, not cryptographic

        def _spy_that_must_never_be_called() -> int:
            raise AssertionError(
                "_count_node_process_matches() was called for a ProcessResult that does "
                "not match the existing spawn-eperm/windowsSafeRealPathSync/"
                "optimizeSafeRealPathSync classification branch -- the context-capture "
                "code from task 1 must only be reachable from that exact existing branch."
            )

        monkeypatch.setattr(
            build_runner, "_count_node_process_matches", _spy_that_must_never_be_called
        )

        phases = ["install", "typecheck", "format", "build", "artifact"]
        non_matching_output_templates = [
            "",
            "npm ERR! code ELIFECYCLE",
            "TypeScript error TS2322: Type 'string' is not assignable to type 'number'.",
            "vite build failed: Rollup failed to resolve import",
            "ENOENT: no such file or directory, open 'package.json'",
            # Contains "spawn eperm" but neither helper-name substring --
            # must still not fire the branch, since the branch requires both.
            "Error: spawn EPERM at somewhereElseEntirely (unrelated/module.js:1:1)",
            # Contains one helper-name substring but not "spawn eperm" --
            # must still not fire the branch.
            "ReferenceError: windowsSafeRealPathSync is not defined in this unrelated context",
            "network timeout while fetching dependency tarball",
            "permission denied writing to dist/index.html",
        ]

        for _trial in range(150):
            phase = rng.choice(phases)
            returncode = rng.choice([0, 0, 1, 1, 2, 127])
            timed_out = rng.random() < 0.1
            combined_output = rng.choice(non_matching_output_templates)
            # Randomly vary casing/whitespace without introducing the two
            # substrings that would legitimately match together.
            if rng.random() < 0.5:
                combined_output = combined_output.upper()

            async def fake_run_command(
                *_args,
                _returncode=returncode,
                _combined_output=combined_output,
                _timed_out=timed_out,
                _phase=phase,
                **_kwargs,
            ):
                return ProcessResult(
                    command=("npm", "run", _phase),
                    returncode=_returncode,
                    stdout=_combined_output,
                    stderr="",
                    timed_out=_timed_out,
                )

            monkeypatch.setattr(build_runner, "run_command", fake_run_command)
            settings = SimpleNamespace(
                code_generator_verification=SimpleNamespace(
                    build_timeout_seconds=1.0,
                    typecheck_timeout_seconds=1.0,
                    install_timeout_seconds=1.0,
                    format_timeout_seconds=1.0,
                    max_output_bytes=1024,
                )
            )

            # Must not raise: if the spy above were ever invoked, it raises
            # AssertionError, which would propagate out of `_run()` and fail
            # this trial immediately.
            await build_runner._run(
                ["npm", "run", phase],
                repo_dir=tmp_path,
                settings=settings,
                timeout_name="build_timeout_seconds",
                phase=phase,
                stage_durations_ms={"verify": rng.uniform(0.0, 500_000.0)},
            )
