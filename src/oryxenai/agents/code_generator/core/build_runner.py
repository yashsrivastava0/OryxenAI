"""Clean dependency, type, build, and artifact gate execution."""

from __future__ import annotations

import asyncio
import hashlib
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from oryxenai.agents.code_generator.core import fs_safe
from oryxenai.agents.code_generator.core.artifact_manifest import (
    ArtifactValidationError,
    build_manifest,
)
from oryxenai.agents.code_generator.core.development_schemas import (
    BuildManifest,
    Diagnostic,
)
from oryxenai.agents.code_generator.core.process_runner import (
    ProcessResult,
    resolve_npm_executable,
    run_command,
)
from oryxenai.agents.code_generator.core.workspace import repository_root


class BuildRunnerError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


# npm's cache and registry connection pool are shared by all verification
# jobs in a worker.  Concurrent clean installs can starve each other and hit
# the command timeout even though either install succeeds in isolation.  Keep
# the expensive package-manager section single-flight while allowing the
# subsequent typecheck/build/runtime work to remain concurrent.
_PACKAGE_INSTALL_LOCK = asyncio.Lock()
_VITE_WINDOWS_SPAWN_DENIED = "VITE_NODE_SPAWN_EPERM"
_VITE_WINDOWS_SPAWN_RETRY_DELAY_SECONDS = 0.25


def _normalize(value: str) -> str:
    value = re.sub(r"[A-Za-z]:\\[^\n ]+", "<workspace>", value)
    value = re.sub(r"/(?:[^\n ]+/)+(?:src|node_modules|dist)/", "<workspace>/", value)
    value = re.sub(r"\x1b\[[0-9;]*m", "", value)
    return " ".join(value.split())[:4000]


def _count_node_process_matches() -> int | None:
    """Best-effort count of currently-running ``node``/``npm`` OS processes.

    This exists only to give a future ``VITE_NODE_SPAWN_EPERM`` occurrence
    enough context to distinguish a transient, contention-driven spawn
    failure from a persistent one (see design.md's "Hypothesized Root
    Cause"). Enumeration is stdlib-only (no ``psutil``) and strictly
    best-effort: any denial, timeout, or platform quirk degrades to
    ``None`` (unknown) rather than raising, following the same posture
    already established for Windows enumeration denials in
    ``fs_safe.remove_tree`` / the toolchain preflight cleanup path.
    """

    try:
        if sys.platform == "win32":
            tasklist = shutil.which("tasklist")
            if not tasklist:
                return None
            result = subprocess.run(  # noqa: S603 - fixed command, resolved executable, no untrusted input
                [tasklist, "/FO", "CSV", "/NH"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=5.0,
                check=False,
                text=True,
            )
            lines = result.stdout.splitlines() if result.stdout else []
            return sum(
                1
                for line in lines
                if line.strip().casefold().startswith(('"node.exe"', '"npm.exe"', '"npm.cmd"'))
            )
        ps_executable = shutil.which("ps")
        if not ps_executable:
            return None
        result = subprocess.run(  # noqa: S603 - fixed command, resolved executable, no untrusted input
            [ps_executable, "-eo", "comm"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5.0,
            check=False,
            text=True,
        )
        lines = result.stdout.splitlines() if result.stdout else []
        return sum(1 for line in lines if line.strip().casefold() in {"node", "npm"})
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _prior_duration_note(stage_durations_ms: Mapping[str, float] | None, *, phase: str) -> str:
    """Best-effort comparison of this attempt's elapsed time against the
    previous recorded duration for the same phase on this run, if any.

    ``stage_durations_ms`` is populated elsewhere (the coordinator, once
    wired) and may legitimately be absent or missing this phase's entry —
    most notably on the very first verify attempt of a run, or before that
    wiring exists at all. Absence degrades to an empty note, never a raised
    error.
    """

    if not stage_durations_ms:
        return ""
    try:
        prior = stage_durations_ms.get(phase)
    except AttributeError:
        return ""
    if prior is None:
        return ""
    try:
        prior_seconds = float(prior) / 1000.0
    except (TypeError, ValueError):
        return ""
    if prior_seconds < 0:
        return ""
    return f"the previous {phase} attempt on this run took {prior_seconds:.1f}s"


def diagnostic(
    code: str,
    message: str,
    *,
    phase: str,
    command: str = "",
    file: str = "",
    owner: str = "generator",
) -> Diagnostic:
    fingerprint = hashlib.sha256(f"{code}:{phase}:{command}:{file}:{message}".encode()).hexdigest()[
        :24
    ]
    return Diagnostic(
        diagnostic_id=f"diagnostic-{fingerprint}",
        group="type_build_artifact",
        code=code,
        owner=owner,  # type: ignore[arg-type]
        phase=phase,
        command=command,
        normalized_message=_normalize(message),
        file=file,
        fingerprint=fingerprint,
    )


def is_vite_windows_spawn_failure(diagnostics: Iterable[Diagnostic]) -> bool:
    """Identify Vite's host-level Windows child-process denial.

    This occurs while Vite configures path resolution, before it evaluates the
    generated application. It must not consume source-repair budget.
    """

    values = list(diagnostics)
    return bool(values) and all(item.code == _VITE_WINDOWS_SPAWN_DENIED for item in values)


def _command(settings: Any, name: str, default: list[str]) -> list[str]:
    config = getattr(settings, "code_generator_verification", None)
    value = getattr(config, name, None) if config is not None else None
    command = [str(item) for item in value] if value else list(default)
    if command and Path(command[0]).name.casefold() in {"npm", "npm.cmd", "npm.exe"}:
        executable = resolve_npm_executable(settings)
        if executable:
            command[0] = executable
    return command


def _timeout(settings: Any, name: str, default: float) -> float:
    config = getattr(settings, "code_generator_verification", None)
    return float(getattr(config, name, default)) if config is not None else default


def _npm_cache_environment(settings: Any) -> dict[str, str] | None:
    config = getattr(settings, "code_generator_dependencies", None)
    cache_root = str(getattr(config, "npm_cache_root", "") or "")
    if not cache_root:
        return None
    # Extras only — run_command merges these onto its safe base environment.
    cache_path = Path(cache_root)
    resolved_cache = (
        cache_path if cache_path.is_absolute() else (repository_root() / cache_path).resolve()
    )
    return {"npm_config_cache": str(resolved_cache)}


async def _run(
    command: list[str],
    *,
    repo_dir: Path,
    settings: Any,
    timeout_name: str,
    phase: str,
    stage_durations_ms: Mapping[str, float] | None = None,
) -> tuple[ProcessResult | None, Diagnostic | None]:
    try:
        result = await run_command(
            command,
            cwd=repo_dir,
            timeout_seconds=_timeout(settings, timeout_name, 180.0),
            max_output_bytes=int(
                getattr(
                    getattr(settings, "code_generator_verification", None),
                    "max_output_bytes",
                    65536,
                )
            ),
            # Offline npm reads the repo's warmed cache; absolute so npm
            # resolves it correctly against the per-run repo cwd.
            environment=_npm_cache_environment(settings),
        )
    except Exception as exc:
        return None, diagnostic(
            "COMMAND_START_FAILED",
            str(exc),
            phase=phase,
            command=" ".join(command),
            owner="infrastructure",
        )
    if result.timed_out:
        return result, diagnostic(
            "COMMAND_TIMEOUT",
            "The trusted command exceeded its configured timeout.",
            phase=phase,
            command=" ".join(command),
            owner="infrastructure",
        )
    if result.returncode != 0:
        output = result.combined_output
        normalized_output = output.casefold()
        if (
            phase == "build"
            and "spawn eperm" in normalized_output
            and (
                "windowssaferealpathsync" in normalized_output
                or "optimizesaferealpathsync" in normalized_output
            )
        ):
            process_count = _count_node_process_matches()
            context_parts = [
                f"{process_count} node/npm process(es) were running concurrently at the "
                "time of failure"
                if process_count is not None
                else "the concurrent node/npm process count could not be determined"
            ]
            duration_note = _prior_duration_note(stage_durations_ms, phase="verify")
            if duration_note:
                context_parts.append(duration_note)
            context_suffix = f" ({'; '.join(context_parts)})."
            return result, diagnostic(
                _VITE_WINDOWS_SPAWN_DENIED,
                (
                    "The local Windows Node toolchain could not start Vite's required "
                    "path-resolution helper (spawn EPERM). Pause competing Node or build "
                    "activity, rerun the toolchain preflight, then retry verification."
                    + context_suffix
                ),
                phase=phase,
                command=" ".join(command),
                owner="infrastructure",
            )
        return result, diagnostic(
            f"{phase.upper()}_FAILED",
            output or "The trusted command failed.",
            phase=phase,
            command=" ".join(command),
        )
    return result, None


async def run_clean_build(
    repo_dir: Path,
    *,
    settings: Any,
    candidate_identity_hash: str,
    stage_durations_ms: Mapping[str, float] | None = None,
) -> tuple[BuildManifest | None, list[Diagnostic]]:
    """Recreate dependencies and produce one verified production manifest."""

    diagnostics: list[Diagnostic] = []
    for disposable in (repo_dir / "node_modules", repo_dir / "dist"):
        try:
            fs_safe.remove_tree(disposable)
        except fs_safe.FsSafeError as exc:
            return None, [
                diagnostic(
                    "CLEANUP_FAILED",
                    str(exc),
                    phase="install",
                    owner="infrastructure",
                )
            ]
    npm_ci = _command(
        settings,
        "install_command",
        ["npm", "ci", "--ignore-scripts", "--offline", "--no-audit", "--no-fund"],
    )
    async with _PACKAGE_INSTALL_LOCK:
        _, issue = await _run(
            npm_ci,
            repo_dir=repo_dir,
            settings=settings,
            timeout_name="install_timeout_seconds",
            phase="install",
        )
    if issue is not None:
        diagnostics.append(issue)
        return None, diagnostics
    typecheck, issue = await _run(
        _command(settings, "typecheck_command", ["npm", "run", "typecheck"]),
        repo_dir=repo_dir,
        settings=settings,
        timeout_name="typecheck_timeout_seconds",
        phase="typecheck",
    )
    del typecheck
    if issue is not None:
        diagnostics.append(issue)
        return None, diagnostics
    format_command = _command(settings, "format_command", [])
    if format_command:
        _, issue = await _run(
            format_command,
            repo_dir=repo_dir,
            settings=settings,
            timeout_name="format_timeout_seconds",
            phase="format",
        )
        if issue is not None:
            diagnostics.append(issue)
            return None, diagnostics
    build_command = _command(settings, "build_command", ["npm", "run", "build"])
    _, issue = await _run(
        build_command,
        repo_dir=repo_dir,
        settings=settings,
        timeout_name="build_timeout_seconds",
        phase="build",
        stage_durations_ms=stage_durations_ms,
    )
    if issue is not None and issue.code == _VITE_WINDOWS_SPAWN_DENIED:
        # Vite's Windows real-path helper can lose a short-lived child-process
        # launch race immediately after npm has finished installing a fresh
        # workspace. A single model-free retry is safe: it does not alter the
        # source tree or consume repair budget, and it avoids converting a
        # buildable portfolio into a false infrastructure terminal state.
        await asyncio.sleep(_VITE_WINDOWS_SPAWN_RETRY_DELAY_SECONDS)
        _, issue = await _run(
            build_command,
            repo_dir=repo_dir,
            settings=settings,
            timeout_name="build_timeout_seconds",
            phase="build",
            stage_durations_ms=stage_durations_ms,
        )
    if issue is not None:
        diagnostics.append(issue)
        return None, diagnostics
    try:
        manifest = build_manifest(
            repo_dir / "dist",
            candidate_identity_hash=candidate_identity_hash,
            max_total_bytes=int(
                getattr(
                    getattr(settings, "code_generator_verification", None),
                    "max_artifact_bytes",
                    32 * 1024 * 1024,
                )
            ),
            reject_source_maps=bool(
                getattr(
                    getattr(settings, "code_generator_verification", None),
                    "reject_source_maps",
                    True,
                )
            ),
        )
    except ArtifactValidationError as exc:
        diagnostics.append(diagnostic(exc.code, exc.message, phase="artifact", file=exc.path))
        return None, diagnostics
    return manifest, diagnostics
