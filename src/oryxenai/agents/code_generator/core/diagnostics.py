"""Stable, redacted diagnostic normalization for final repair."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import Diagnostic, DiagnosticBundle

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b", re.IGNORECASE)
_WINDOWS_ROOT_RE = re.compile(r"[A-Za-z]:\\[^\s:]+")
_POSIX_ROOT_RE = re.compile(r"/(?:[^\s/]+/)+(?:src|dist|node_modules)/[^\s]+")
_LINE_RE = re.compile(r"(:\d+)(?::\d+)?")


def normalize_message(value: str) -> str:
    value = _ANSI_RE.sub("", value)
    value = _WINDOWS_ROOT_RE.sub("<workspace>", value)
    value = _POSIX_ROOT_RE.sub("<workspace>", value)
    value = _UUID_RE.sub("<id>", value)
    value = _LINE_RE.sub("", value)
    return " ".join(value.split())[:4000]


def make_diagnostic(
    *,
    group: str,
    code: str,
    message: str,
    phase: str,
    owner: str = "generator",
    file: str = "",
    route_id: str = "",
    interaction_id: str = "",
    command: str = "",
    expected: str = "",
    observed: str = "",
    receipts: list[str] | None = None,
) -> Diagnostic:
    normalized = normalize_message(message)
    fingerprint = hashlib.sha256(
        f"{group}:{code}:{file}:{route_id}:{interaction_id}:{normalized}".encode()
    ).hexdigest()[:24]
    return Diagnostic(
        diagnostic_id=f"diagnostic-{fingerprint}",
        group=group,  # type: ignore[arg-type]
        code=code,
        owner=owner,  # type: ignore[arg-type]
        phase=phase,
        route_id=route_id,
        interaction_id=interaction_id,
        command=command,
        normalized_message=normalized,
        file=file,
        expected=expected,
        observed=observed,
        relevant_receipt_hashes=list(receipts or []),
        fingerprint=fingerprint,
    )


def build_bundle(
    *,
    checkpoint_hash: str,
    diagnostics: list[Diagnostic],
    allowed_paths: list[str],
    plan_slice: dict[str, Any],
    source_root: Path,
    required_checks: list[str],
    resource_bindings: list[dict[str, Any]] | None = None,
    dependency_signatures: list[dict[str, Any]] | None = None,
    prior_strategies: list[str] | None = None,
) -> DiagnosticBundle:
    implicated = sorted({item.file for item in diagnostics if item.file})
    bounded: dict[str, str] = {}
    for relative in implicated:
        path = (source_root / relative).resolve()
        if path.is_file() and path.is_relative_to(source_root.resolve()):
            try:
                bounded[relative] = path.read_text(encoding="utf-8")[:12000]
            except (OSError, UnicodeDecodeError):
                continue
    group = next(
        (item.group for item in diagnostics if item.severity == "blocking"), "source_contract"
    )
    return DiagnosticBundle(
        based_on_checkpoint=checkpoint_hash,
        failed_group=group,  # type: ignore[arg-type]
        diagnostics=diagnostics,
        allowed_paths=allowed_paths,
        affected_plan_slice=plan_slice,
        affected_resource_bindings=list(resource_bindings or []),
        dependency_signatures=list(dependency_signatures or []),
        implicated_source_files=implicated,
        bounded_related_source=bounded,
        required_checks_after_change=required_checks,
        prior_repair_strategies=list(prior_strategies or []),
    )
