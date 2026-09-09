"""Post-promotion export of the complete generated portfolio.

After a run reaches READY, the full portfolio is copied to the configured
export root as both the source project (without disposables) and the built
static site, plus a metadata manifest. Export is advisory: a failure here is
logged as an event and never fails a promoted run.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections.abc import Callable
from datetime import UTC, datetime, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from oryxenai.agents.code_generator.core import fs_safe
from oryxenai.agents.code_generator.core.build_runner import run_clean_build
from oryxenai.agents.code_generator.core.resource_policy import is_image_category
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


def build_image_evidence(*, repo_dir: Path, run_root: Path, plan: Any) -> dict[str, Any]:
    """Summarize image lineage without exposing prompts or private content."""

    blueprint = getattr(plan, "experience_blueprint", None)
    bindings = {
        str(item.resource_slot_id): item.category
        for item in getattr(plan, "execution_bindings", [])
        if str(getattr(item, "resource_slot_id", ""))
    }
    placements = [
        item
        for item in getattr(blueprint, "resource_placements", [])
        if is_image_category(bindings.get(str(item.resource_slot_id), ""))
    ]
    projections_path = run_root / "ledger" / "projections.json"
    projections: dict[str, Any] = {}
    if projections_path.is_file():
        try:
            raw = json.loads(projections_path.read_text(encoding="utf-8"))
            projections = raw if isinstance(raw, dict) else {}
        except (OSError, ValueError, TypeError):
            projections = {}
    generated = projections.get("generated/resource-assets.json", {})
    assets = generated.get("image_assets", []) if isinstance(generated, dict) else []
    assets_by_slot = {
        str(item.get("resource_slot_id") or item.get("resource_id") or ""): item
        for item in assets
        if isinstance(item, dict) and is_image_category(item.get("category", "image"))
    }
    source_files = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in repo_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".tsx", ".ts", ".css"}
        and "node_modules" not in path.parts
    )
    entries: list[dict[str, Any]] = []
    for placement in placements:
        slot_id = str(placement.resource_slot_id)
        asset = assets_by_slot.get(slot_id)
        rendered = _source_references_resource_slot(source_files, slot_id)
        entries.append(
            {
                "resource_slot_id": slot_id,
                "route_id": str(placement.route_id),
                "section_id": str(placement.section_id),
                "materialized": bool(asset),
                "rendered": rendered,
                "source_count": len(asset.get("sources", [])) if asset else 0,
                "local_paths": [
                    str(item.get("path", ""))
                    for item in (asset.get("sources", []) if asset else [])
                    if isinstance(item, dict) and str(item.get("path", ""))
                ],
                "disposition": "admitted" if asset and rendered else "fallback_or_missing",
            }
        )
    return {
        "planned_count": len(entries),
        "materialized_count": sum(1 for item in entries if item["materialized"]),
        "rendered_count": sum(1 for item in entries if item["rendered"]),
        "failed_count": sum(1 for item in entries if not item["materialized"] or not item["rendered"]),
        "entries": entries,
    }


def _source_references_resource_slot(source: str, slot_id: str) -> bool:
    """Recognize literal JSX prop forms used by the generator contract."""

    escaped = re.escape(slot_id)
    return bool(
        re.search(
            rf"\bresourceId\s*=\s*(?:['\"]{escaped}['\"]|\{{\s*['\"`]"
            rf"{escaped}['\"`]\s*\}})",
            source,
        )
    )


def _generation_report(payload: dict[str, Any]) -> str:
    """Build a compact evaluator handoff without prompts, source, or secrets."""

    quality = payload.get("quality_review")
    if isinstance(quality, dict) and isinstance(quality.get("accepted"), bool):
        quality_status = "accepted" if quality["accepted"] else "rejected"
    else:
        quality_status = "unknown"
    verification = payload.get("verification")
    gate_results = verification.get("gate_results", []) if isinstance(verification, dict) else []
    gate_statuses = {
        str(item.get("gate_id", "")): str(item.get("status", "unknown"))
        for item in gate_results
        if isinstance(item, dict) and str(item.get("gate_id", ""))
    }
    if gate_statuses:
        statuses = set(gate_statuses.values())
        if "failed" in statuses:
            verification_status = "failed"
        elif statuses == {"passed"}:
            verification_status = "passed"
        else:
            verification_status = "partial"
    else:
        verification_status = "unknown"
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
    build_attempt = payload.get("build_attempt")
    build_attempt_status = (
        build_attempt.get("status", "not_recorded")
        if isinstance(build_attempt, dict)
        else "not_recorded"
    )
    image_evidence = payload.get("image_evidence")
    blocking_findings: list[dict[str, Any]] = []
    advisory_findings: list[dict[str, Any]] = []
    if isinstance(verification, dict):
        for gate in gate_results:
            if not isinstance(gate, dict):
                continue
            for finding in gate.get("diagnostics", []):
                if not isinstance(finding, dict):
                    continue
                if str(finding.get("severity", "blocking")) == "advisory":
                    advisory_findings.append(finding)
                else:
                    blocking_findings.append(finding)
        for advisory in verification.get("advisories", []):
            if isinstance(advisory, dict):
                advisory_findings.append(advisory)
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
        f"- Build attempt: `{build_attempt_status}`",
        f"- Provenance: `{provenance_status}`",
        f"- Recorded model-call receipts: `{call_count}`",
        f"- Generation request rounds: `{request_rounds}`",
        f"- Repair rounds: `{repair_rounds}`",
        f"- Verification gates: `{json.dumps(gate_statuses, sort_keys=True)}`",
        f"- Blocking findings: `{len(blocking_findings)}`",
        f"- Advisory observations: `{len(advisory_findings)}`",
        "",
        "## Image evidence",
        (
            f"- Planned: `{image_evidence.get('planned_count', 0)}`; "
            f"materialized: `{image_evidence.get('materialized_count', 0)}`; "
            f"rendered: `{image_evidence.get('rendered_count', 0)}`; "
            f"failed: `{image_evidence.get('failed_count', 0)}`"
            if isinstance(image_evidence, dict)
            else "- Image evidence: `unknown`"
        ),
        *(
            [
                "- "
                + json.dumps(
                    {
                        "resource_slot_id": item.get("resource_slot_id", ""),
                        "route_id": item.get("route_id", ""),
                        "section_id": item.get("section_id", ""),
                        "materialized": item.get("materialized", False),
                        "rendered": item.get("rendered", False),
                        "disposition": item.get("disposition", ""),
                    },
                    sort_keys=True,
                )
                for item in image_evidence.get("entries", [])
                if isinstance(item, dict)
            ]
            if isinstance(image_evidence, dict)
            else []
        ),
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


async def _attempt_best_effort_build(
    *, repo_dir: Path, settings: Any, run_id: str
) -> dict[str, Any]:
    """Try to produce a real `dist/` for a run that did not reach promotion,
    so an evaluator (or a human) does not have to `npm ci`/`npm run build`
    by hand just to look at a needs_attention/failed export. This reuses the
    same clean-build gate the promoted path already runs
    (`build_runner.run_clean_build`); a failure here is expected for many
    exports (e.g. the run was rejected before source ever compiled) and is
    only ever recorded, never allowed to interrupt the export itself. The
    identity hash is a deterministic placeholder -- this manifest is for
    export/inspection only and is never used for promotion."""

    placeholder_identity = hashlib.sha256(f"failed-export:{run_id}".encode()).hexdigest()
    try:
        manifest, diagnostics = await run_clean_build(
            repo_dir,
            settings=settings,
            candidate_identity_hash=placeholder_identity,
        )
    except Exception as exc:
        return {"status": "error", "diagnostics": [str(exc)]}
    if manifest is not None:
        return {"status": "success", "diagnostics": []}
    return {
        "status": "failed",
        "diagnostics": [d.model_dump(mode="json") for d in diagnostics],
    }


async def export_failed_run(
    *,
    settings: Any,
    run_id: str,
    reason: str,
    issues: list[dict[str, Any]] | None = None,
) -> Path | None:
    """Best-effort export of whatever source tree exists for a run that did
    not reach a promoted READY state (needs_attention or failed). Unlike
    `export_portfolio`, this never requires promotion-only state (a build
    manifest, an active preview, a candidate identity) -- only a run id and
    whatever the generation/verification workspace already has on disk.
    Returns None (never raises) when there is nothing yet to export, e.g. a
    run that failed before generation produced any source tree.

    Before exporting, this also attempts a best-effort clean build so the
    export gets a real `dist/` (and an honest build status in the report)
    whenever the source is actually buildable, instead of always shipping
    source-only and leaving the reader to build it themselves."""

    config = settings.code_generator_generation
    workspace_root = Path(str(getattr(config, "workspace_root", "")))
    if not workspace_root.is_absolute():
        workspace_root = repository_root() / workspace_root
    run_root = (workspace_root / run_id).resolve()
    repo_dir = run_root / "repo"
    if not repo_dir.is_dir():
        return None
    build_attempt = await _attempt_best_effort_build(
        repo_dir=repo_dir, settings=settings, run_id=run_id
    )
    return export_portfolio(
        settings=settings,
        run_id=run_id,
        repo_dir=repo_dir,
        screenshots_dir=run_root / "verification-screenshots",
        metadata={
            "status": "needs_attention",
            "export_reason": reason,
            "issues": issues or [],
            "build_attempt": build_attempt,
        },
    )


def build_export_receipt(exported: Path) -> dict[str, Any]:
    """Build the same compact receipt shape the promoted-export path already
    writes onto a run's `export_receipt` field, from an export folder that
    `export_failed_run` produced. Callers CAS-write the result themselves --
    this only shapes the dict so a needs_attention run's export is as
    discoverable through the run API/UI as a promoted run's export already
    is, instead of only existing on disk with nothing pointing at it."""

    try:
        relative_export_path = exported.resolve().relative_to(repository_root().resolve()).as_posix()
    except ValueError:
        relative_export_path = exported.name
    return {
        "status": "exported",
        "relative_path": relative_export_path,
        "folder": exported.name,
        "source_path": "source",
        "dist_path": "dist" if (exported / "dist").is_dir() else "",
        "metadata_path": "portfolio.json",
        "report_path": "generation-report.md",
        "exported_at": datetime.now(UTC).isoformat(),
    }


__all__ = [
    "DEFAULT_EXPORT_ROOT",
    "DEFAULT_EXPORT_TIMEZONE",
    "build_export_receipt",
    "export_failed_run",
    "export_portfolio",
]
