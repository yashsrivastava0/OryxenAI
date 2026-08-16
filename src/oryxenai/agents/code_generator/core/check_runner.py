"""Trusted source/type check execution for Phase 3."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import SourceDiagnostic


async def prepare_toolchain(repo_dir: Path, *, settings: Any) -> SourceDiagnostic | None:
    """Install the receipt-bound scaffold dependencies without general network access."""
    config = settings.code_generator_generation
    if not bool(getattr(config, "use_real_typecheck", False)):
        return None
    npm = str(
        getattr(settings.code_generator_dependencies, "npm_executable", "") or ""
    ) or shutil.which("npm")
    if not npm:
        return _command_diagnostic(
            "TOOLCHAIN_UNAVAILABLE",
            "The configured npm executable is unavailable.",
            "toolchain",
            "",
        )
    environment = os.environ.copy()
    for key in tuple(environment):
        if key.upper().endswith(("_TOKEN", "_PASSWORD", "_SECRET", "_KEY")):
            environment.pop(key, None)
    # Offline installs read the repo's warmed npm cache; the path must be
    # absolute because npm resolves a relative cache against repo_dir.
    cache_root = str(
        getattr(settings.code_generator_dependencies, "npm_cache_root", "") or ""
    )
    if cache_root:
        environment["npm_config_cache"] = str(Path(cache_root).resolve())
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            [npm, "ci", "--ignore-scripts", "--offline", "--no-audit", "--no-fund"],
            cwd=repo_dir,
            env=environment,
            capture_output=True,
            text=True,
            timeout=float(config.typecheck_timeout_seconds),
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return _command_diagnostic(
            "TOOLCHAIN_START_FAILED", "The source toolchain could not start.", "toolchain", str(exc)
        )
    if result.returncode != 0:
        return _command_diagnostic(
            "TOOLCHAIN_INSTALL_FAILED",
            _normalize_output(result.stderr or result.stdout),
            "toolchain",
            "",
        )
    return None


async def run_source_checks(
    repo_dir: Path,
    *,
    allowed_packages: set[str],
    public_text: set[str],
    max_source_bytes: int,
    work_unit_id: str,
    settings: Any,
) -> list[SourceDiagnostic]:
    from oryxenai.agents.code_generator.core.source_validation import validate_repository

    diagnostics = validate_repository(
        repo_dir,
        allowed_packages=allowed_packages,
        public_text=public_text,
        max_source_bytes=max_source_bytes,
        work_unit_id=work_unit_id,
    )
    if diagnostics:
        return diagnostics
    if bool(getattr(settings.code_generator_generation, "use_real_typecheck", False)):
        return await _run_configured_typecheck(
            repo_dir, work_unit_id=work_unit_id, settings=settings
        )
    return _structural_typecheck(repo_dir, work_unit_id)


async def _run_configured_typecheck(
    repo_dir: Path, *, work_unit_id: str, settings: Any
) -> list[SourceDiagnostic]:
    command = [str(value) for value in settings.code_generator_generation.typecheck_command]
    if not command:
        return _structural_typecheck(repo_dir, work_unit_id)
    environment = os.environ.copy()
    for key in tuple(environment):
        if key.upper().endswith(("_TOKEN", "_PASSWORD", "_SECRET", "_KEY")):
            environment.pop(key, None)
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            command,
            cwd=repo_dir,
            env=environment,
            capture_output=True,
            text=True,
            timeout=float(settings.code_generator_generation.typecheck_timeout_seconds),
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return [
            _command_diagnostic(
                "TYPECHECK_START_FAILED",
                "The configured typecheck command could not start.",
                work_unit_id,
                str(exc),
            )
        ]
    if result.returncode == 0:
        return []
    message = _normalize_output(f"{result.stdout}\n{result.stderr}")
    return [
        _command_diagnostic(
            "TYPECHECK_FAILED",
            message or "The configured typecheck command failed.",
            work_unit_id,
            "",
        )
    ]


def _structural_typecheck(repo_dir: Path, work_unit_id: str) -> list[SourceDiagnostic]:
    for path in sorted(repo_dir.rglob("*.tsx")) + sorted(repo_dir.rglob("*.ts")):
        if any(part in {"node_modules", "dist"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        if _unbalanced(text):
            return [
                _command_diagnostic(
                    "TYPECHECK_STRUCTURE_INVALID",
                    "A generated TypeScript file has unbalanced delimiters.",
                    work_unit_id,
                    path.relative_to(repo_dir).as_posix(),
                )
            ]
    return []


def _unbalanced(text: str) -> bool:
    pairs = {"{": "}", "[": "]", "(": ")"}
    stack: list[str] = []
    quote = ""
    escaped = False
    for char in text:
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char in pairs:
            stack.append(pairs[char])
        elif char in pairs.values() and (not stack or stack.pop() != char):
            return True
    return bool(stack) or bool(quote)


def _normalize_output(value: str) -> str:
    value = re.sub(r"[A-Za-z]:\\[^\n ]+", "<workspace>", value)
    value = re.sub(r"/[^\n ]+/(?:src|node_modules)/", "<workspace>/", value)
    value = re.sub(r"\x1b\[[0-9;]*m", "", value)
    return " ".join(value.split())[:2000]


def _command_diagnostic(code: str, message: str, work_unit_id: str, file: str) -> SourceDiagnostic:
    import hashlib

    fingerprint = hashlib.sha256(f"{code}:{file}:{message}".encode()).hexdigest()[:24]
    return SourceDiagnostic(
        diagnostic_id=f"diagnostic-{fingerprint}",
        group="typecheck",
        code=code,
        phase="source_generation",
        work_unit_id=work_unit_id,
        normalized_message=message,
        file=file,
        fingerprint=fingerprint,
    )
