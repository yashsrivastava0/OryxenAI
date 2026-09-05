"""Post-promotion export of the complete generated portfolio.

After a run reaches READY, the full portfolio is copied to the configured
export root as both the source project (without disposables) and the built
static site, plus a metadata manifest. Export is advisory: a failure here is
logged as an event and never fails a promoted run.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from datetime import UTC, datetime, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from oryxenai.agents.code_generator.core import fs_safe
from oryxenai.agents.code_generator.core.workspace import repository_root

DEFAULT_EXPORT_ROOT = "output/code-gen-output"
DEFAULT_EXPORT_TIMEZONE = "Asia/Kolkata"

_DOCKER_ARTIFACT_NAMES = {
    "dockerfile",
    ".dockerignore",
    "compose.yaml",
    "compose.yml",
    "docker-compose.yaml",
    "docker-compose.yml",
}
_DISPOSABLE_SOURCE_NAMES = {"node_modules", "dist", ".workspace", ".git"}


def _is_docker_artifact(name: str) -> bool:
    lowered = name.casefold()
    return lowered in _DOCKER_ARTIFACT_NAMES or lowered.startswith("dockerfile.")


def _export_ignore(root: Path, excluded: list[str]) -> Callable[[str, list[str]], set[str]]:
    def ignore(path: str, names: list[str]) -> set[str]:
        current = Path(path)
        ignored: set[str] = set()
        for name in names:
            if name in _DISPOSABLE_SOURCE_NAMES or _is_docker_artifact(name):
                ignored.add(name)
                relative = (current / name).relative_to(root).as_posix()
                excluded.append(relative)
        return ignored

    return ignore


def _export_timestamp(config: Any) -> tuple[datetime, str]:
    timezone_name = str(getattr(config, "export_timezone", DEFAULT_EXPORT_TIMEZONE) or "")
    timezone: tzinfo
    try:
        timezone = ZoneInfo(timezone_name or DEFAULT_EXPORT_TIMEZONE)
    except Exception:
        # Windows development images may not ship the optional tzdata package.
        # Use the machine's configured local timezone rather than failing an
        # otherwise advisory export.
        timezone = datetime.now().astimezone().tzinfo or UTC
        timezone_name = "system-local"
    return datetime.now(timezone), timezone_name


def export_portfolio(
    *,
    settings: Any,
    run_id: str,
    repo_dir: Path,
    metadata: dict[str, Any],
    screenshots_dir: Path | None = None,
) -> Path:
    config = settings.code_generator_verification
    root = Path(str(getattr(config, "export_root", DEFAULT_EXPORT_ROOT)))
    if not root.is_absolute():
        root = repository_root() / root
    exported_at, timezone_name = _export_timestamp(config)
    short_id = run_id.replace("-", "")[:8] or "run"
    folder_name = f"{exported_at:%H-%M-%d-%m-%Y}-{short_id}"
    target = root / folder_name
    # UUID prefixes are collision-safe for normal runs. If a caller reuses a
    # short synthetic ID, preserve the existing export instead of deleting it.
    if target.exists():
        existing_metadata = target / "portfolio.json"
        if existing_metadata.is_file():
            try:
                existing = json.loads(existing_metadata.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                existing = {}
            if str(existing.get("run_id", "")) != run_id:
                target = root / f"{folder_name}-{run_id[:12]}"
        if target.exists():
            fs_safe.remove_tree(target, required=False)

    excluded: list[str] = []
    shutil.copytree(
        repo_dir,
        target / "source",
        symlinks=False,
        ignore=_export_ignore(repo_dir, excluded),
    )
    dist_dir = repo_dir / "dist"
    if dist_dir.is_dir():
        shutil.copytree(
            dist_dir,
            target / "dist",
            symlinks=False,
            ignore=_export_ignore(dist_dir, excluded),
        )
    has_screenshots = screenshots_dir is not None and screenshots_dir.is_dir()
    if has_screenshots and screenshots_dir is not None:
        shutil.copytree(
            screenshots_dir,
            target / "screenshots",
            symlinks=False,
            ignore=_export_ignore(screenshots_dir, excluded),
        )

    payload = {
        # v2 is additive: readers must continue accepting v1 exports while
        # new exports carry the quality/resource/route receipt references
        # supplied by the promotion handler.
        "schema_version": "oryxenai-portfolio-export-v2",
        "legacy_schema_version": "oryxenai-portfolio-export-v1",
        "run_id": run_id,
        "exported_at": exported_at.astimezone(UTC).isoformat(),
        "export_timezone": timezone_name,
        "export_folder": target.name,
        **metadata,
        "runtime": {
            "kind": "static-vite",
            "docker": False,
            "preview": "shared-static-gateway",
            "entrypoint": "dist/index.html",
        },
        "evaluator_handoff": {
            "source_path": "source",
            "dist_path": "dist" if dist_dir.is_dir() else "",
            "screenshots_path": "screenshots" if has_screenshots else "",
            "metadata_path": "portfolio.json",
            "report_path": "generation-report.md",
        },
        "excluded_source_artifacts": sorted(set(excluded)),
    }
    fs_safe.write_text_atomic(
        target / "portfolio.json",
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )
    fs_safe.write_text_atomic(target / "generation-report.md", _generation_report(payload))
    return target


def _generation_report(payload: dict[str, Any]) -> str:
    """Build a compact evaluator handoff without prompts, source, or secrets."""

    quality = payload.get("quality_review")
    quality_status = (
        quality.get("status", "not_recorded") if isinstance(quality, dict) else "not_recorded"
    )
    verification = payload.get("verification")
    verification_status = (
        verification.get("status", "not_recorded")
        if isinstance(verification, dict)
        else "not_recorded"
    )
    call_ledger = payload.get("call_ledger")
    call_count = call_ledger.get("call_count", 0) if isinstance(call_ledger, dict) else 0
    request_rounds = call_ledger.get("request_rounds", 0) if isinstance(call_ledger, dict) else 0
    repair_rounds = call_ledger.get("repair_rounds", 0) if isinstance(call_ledger, dict) else 0
    routes = payload.get("routes")
    route_lines = (
        [
            f"- `{item.get('route_id', '')}` → `{item.get('path', '')}`"
            for item in routes
            if isinstance(item, dict)
        ]
        if isinstance(routes, list)
        else []
    )
    if not route_lines:
        route_lines = ["- No route list was recorded."]
    provenance = payload.get("provenance")
    provenance_status = (
        provenance.get("status", "recorded") if isinstance(provenance, dict) else "recorded"
    )
    handoff = payload.get("evaluator_handoff")
    screenshots_path = handoff.get("screenshots_path", "") if isinstance(handoff, dict) else ""
    lines = [
        "# OryxenAI generation report",
        "",
        "This file is a safe handoff for an evaluator agent reviewing the generator. "
        "It describes the run and points at the exported artifacts; it does not contain "
        "model prompts, private intake, raw model responses, or credentials.",
        "",
        "## Run identity",
        f"- Run ID: `{payload.get('run_id', '')}`",
        f"- Trace ID: `{payload.get('trace_id', '')}`",
        f"- Exported at (UTC): `{payload.get('exported_at', '')}`",
        f"- Candidate: `{payload.get('candidate_id', '')}`",
        f"- Checkpoint: `{payload.get('checkpoint_hash', '')}`",
        f"- Build hash: `{payload.get('build_hash', '')}`",
        f"- Build Preparation reference: `{payload.get('pack_reference', '')}`",
        "",
        "## Artifact map",
        "- Source project: `source/`",
        "- Built site: `dist/`",
        *([f"- Verification screenshots: `{screenshots_path}/`"] if screenshots_path else []),
        "- Safe metadata: `portfolio.json`",
        "- This report: `generation-report.md`",
        "",
        "## Pipeline evidence",
        f"- Quality review: `{quality_status}`",
        f"- Verification: `{verification_status}`",
        f"- Provenance: `{provenance_status}`",
        f"- Recorded model-call receipts: `{call_count}`",
        f"- Generation request rounds: `{request_rounds}`",
        f"- Repair rounds: `{repair_rounds}`",
        "",
        "## Routes",
        *route_lines,
        "",
        "## Evaluator handoff",
        "1. Inspect `source/` as the generator output under test.",
        "2. Run the project's configured checks/build from `source/` when the environment permits.",
        "3. Compare visible behavior with `dist/` and the preview URL recorded in `portfolio.json`.",
        "4. Fix recurring defects as Code Generator agent changes or regression tests; do not patch this export as the durable fix.",
        "",
    ]
    return "\n".join(str(line) for line in lines) + "\n"


__all__ = ["DEFAULT_EXPORT_ROOT", "DEFAULT_EXPORT_TIMEZONE", "export_portfolio"]
