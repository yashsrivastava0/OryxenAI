"""Clean dependency, type, build, and artifact gate execution."""

from __future__ import annotations

import hashlib
import re
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
from oryxenai.agents.code_generator.core.process_runner import ProcessResult, run_command
from oryxenai.agents.code_generator.core.workspace import repository_root


class BuildRunnerError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _normalize(value: str) -> str:
    value = re.sub(r"[A-Za-z]:\\[^\n ]+", "<workspace>", value)
    value = re.sub(r"/(?:[^\n ]+/)+(?:src|node_modules|dist)/", "<workspace>/", value)
    value = re.sub(r"\x1b\[[0-9;]*m", "", value)
    return " ".join(value.split())[:4000]


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


def _command(settings: Any, name: str, default: list[str]) -> list[str]:
    config = getattr(settings, "code_generator_verification", None)
    value = getattr(config, name, None) if config is not None else None
    return [str(item) for item in value] if value else list(default)


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
        return result, diagnostic(
            f"{phase.upper()}_FAILED",
            result.combined_output or "The trusted command failed.",
            phase=phase,
            command=" ".join(command),
        )
    return result, None


async def run_clean_build(
    repo_dir: Path,
    *,
    settings: Any,
    candidate_identity_hash: str,
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
    _, issue = await _run(
        _command(settings, "build_command", ["npm", "run", "build"]),
        repo_dir=repo_dir,
        settings=settings,
        timeout_name="build_timeout_seconds",
        phase="build",
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
