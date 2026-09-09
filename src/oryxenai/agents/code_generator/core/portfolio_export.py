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
from uuid import uuid4
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
    root.mkdir(parents=True, exist_ok=True)
    exported_at, timezone_name = _export_timestamp(config)
    short_id = run_id.replace("-", "")[:8] or "run"
    folder_name = f"{exported_at:%H-%M-%d-%m-%Y}-{short_id}"
    target = root / folder_name
    collision = 0
    while target.exists():
        collision += 1
        target = root / f"{folder_name}-{short_id}-{collision}"
    staging = root / f".{folder_name}.staging-{uuid4().hex}"
    excluded: list[str] = []
    try:
        staging.mkdir(parents=True, exist_ok=False)
        shutil.copytree(
            repo_dir,
            staging / "source",
            symlinks=False,
            ignore=_export_ignore(repo_dir, excluded),
        )
        dist_dir = repo_dir / "dist"
        if dist_dir.is_dir():
            shutil.copytree(
                dist_dir,
                staging / "dist",
                symlinks=False,
                ignore=_export_ignore(dist_dir, excluded),
            )
        has_screenshots = screenshots_dir is not None and screenshots_dir.is_dir()
        if has_screenshots and screenshots_dir is not None:
            shutil.copytree(
                screenshots_dir,
                staging / "screenshots",
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
                "entrypoint": "dist/index.html" if dist_dir.is_dir() else "",
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
        payload["evidence_summary"] = build_safe_evidence_summary(payload)
        fs_safe.write_text_atomic(
            staging / "portfolio.json",
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        )
        fs_safe.write_text_atomic(staging / "generation-report.md", _generation_report(payload))
        fs_safe.rename_dir_with_retry(staging, target)
        return target
    except Exception:
        fs_safe.remove_tree(staging, required=False)
        raise


def build_image_evidence(
    *,
    repo_dir: Path,
    run_root: Path,
    plan: Any,
    runtime_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Summarize planning, source, and browser image evidence separately."""

    blueprint = getattr(plan, "experience_blueprint", None)
    bindings = {
        str(item.resource_slot_id): item.category
        for item in getattr(plan, "execution_bindings", [])
        if str(getattr(item, "resource_slot_id", ""))
    }
    placements = [
        item
        for item in getattr(blueprint, "resource_placements", [])
        if (
            is_image_category(bindings.get(str(item.resource_slot_id), ""))
            if bindings
            else True
        )
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
    source_by_path = {
        path.relative_to(repo_dir).as_posix(): path.read_text(encoding="utf-8", errors="ignore")
        for path in repo_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".tsx", ".ts", ".css"}
        and "node_modules" not in path.parts
    }
    source_files = "\n".join(source_by_path.values())
    runtime_items: list[dict[str, Any]] = []
    for raw_item in runtime_evidence or []:
        item = raw_item.model_dump(mode="json") if hasattr(raw_item, "model_dump") else raw_item
        if not isinstance(item, dict):
            continue
        journey_defaults = {
            "journey_id": str(item.get("journey_id", "")),
            "route_id": str(item.get("route_id", "")),
            "viewport": str(item.get("viewport", item.get("viewport_profile", ""))),
        }
        observations = item.get("resource_observations", [])
        if isinstance(observations, list):
            for raw_observation in observations:
                if not isinstance(raw_observation, dict):
                    continue
                runtime_items.append({**journey_defaults, **raw_observation})
        # Accept a direct observation as well so small diagnostics and older
        # callers can feed the exporter without manufacturing a journey
        # wrapper.
        if str(item.get("resource_slot_id", "")):
            runtime_items.append({**journey_defaults, **item})

    def source_for_route(route_id: str) -> str:
        route = next(
            (item for item in getattr(plan, "routes", []) if item.route_id == route_id), None
        )
        if route is None:
            return source_files
        storage_key = str(route.storage_key or route.route_id).replace("\\", "/").strip("/")
        if storage_key.startswith("routes/"):
            storage_key = storage_key.removeprefix("routes/")
        if hasattr(blueprint, "route_shells"):
            from oryxenai.agents.code_generator.core.path_policy import semantic_segment

            storage_key = semantic_segment(storage_key or route_id)
        prefix = f"src/routes/{storage_key}/"
        scoped = "\n".join(
            text for path, text in source_by_path.items() if path.startswith(prefix)
        )
        return scoped or source_files

    entries: list[dict[str, Any]] = []
    for placement in placements:
        slot_id = str(placement.resource_slot_id)
        asset = assets_by_slot.get(slot_id)
        referenced = _source_references_resource_slot(
            source_for_route(str(placement.route_id)), slot_id
        )
        observations = [
            item
            for item in runtime_items
            if str(item.get("resource_slot_id", item.get("id", ""))) == slot_id
            and (
                not str(item.get("route_id", ""))
                or str(item.get("route_id", "")) == str(placement.route_id)
            )
            and (
                not str(item.get("section_id", ""))
                or str(item.get("section_id", "")) == str(placement.section_id)
            )
        ]
        browser_checked = bool(observations)
        decoded = (
            any(item.get("decoded_in_browser", item.get("decoded", False)) is True for item in observations)
            if browser_checked
            else None
        )
        visible = (
            any(item.get("visible_in_browser", item.get("visible", False)) is True for item in observations)
            if browser_checked
            else None
        )
        if not asset:
            disposition = "fallback_or_missing"
        elif visible is True:
            disposition = "admitted_verified"
        elif decoded is True:
            disposition = "admitted_decoded_unverified_visibility"
        elif referenced:
            disposition = "admitted_referenced_unverified_browser"
        else:
            disposition = "admitted_unreferenced"
        entries.append(
            {
                "resource_slot_id": slot_id,
                "route_id": str(placement.route_id),
                "section_id": str(placement.section_id),
                "materialized": bool(asset),
                # `rendered` remains as a v1 compatibility alias. New
                # consumers must use the three evidence fields below.
                "rendered": referenced,
                "referenced_in_source": referenced,
                "decoded_in_browser": decoded,
                "visible_in_browser": visible,
                "browser_evidence_state": (
                    "verified"
                    if visible is True
                    else "failed"
                    if browser_checked
                    else "not_run"
                ),
                "runtime_observation_count": len(observations),
                "browser_observations": [
                    {
                        "journey_id": str(item.get("journey_id", "")),
                        "viewport": str(item.get("viewport", "")),
                        "decoded_in_browser": item.get("decoded_in_browser"),
                        "visible_in_browser": item.get("visible_in_browser"),
                        "local_path": str(item.get("local_path", "")),
                        "frame_width": item.get("frame_width"),
                        "frame_height": item.get("frame_height"),
                        "frame_aspect_ratio": item.get("frame_aspect_ratio"),
                        "intrinsic_aspect_ratio": item.get("intrinsic_aspect_ratio"),
                        "ancestor_opacity": item.get("ancestor_opacity"),
                        "reasons": list(item.get("reasons", []))
                        if isinstance(item.get("reasons", []), list)
                        else [],
                    }
                    for item in observations
                ],
                "source_count": len(asset.get("sources", [])) if asset else 0,
                "local_paths": [
                    str(item.get("path", ""))
                    for item in (asset.get("sources", []) if asset else [])
                    if isinstance(item, dict) and str(item.get("path", ""))
                ],
                "disposition": disposition,
            }
        )
    return {
        "planned_count": len(entries),
        "materialized_count": sum(1 for item in entries if item["materialized"]),
        "referenced_count": sum(1 for item in entries if item["referenced_in_source"]),
        "decoded_count": sum(1 for item in entries if item["decoded_in_browser"] is True),
        "visible_count": sum(1 for item in entries if item["visible_in_browser"] is True),
        "rendered_count": sum(1 for item in entries if item["rendered"]),
        "failed_count": sum(
            1
            for item in entries
            if not item["materialized"]
            or not item["referenced_in_source"]
            or (
                item["runtime_observation_count"] > 0
                and item["visible_in_browser"] is not True
            )
        ),
        "browser_evidence_complete": not entries
        or all(item["runtime_observation_count"] > 0 for item in entries),
        "browser_evidence_not_run_count": sum(
            1 for item in entries if item["runtime_observation_count"] == 0
        ),
        "entries": entries,
    }


def build_safe_evidence_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the safe, stage-neutral facts shared by every export report.

    Successful and failed exports call the same ``export_portfolio`` writer,
    but terminal paths often possess different subsets of evidence. This
    summary keeps those differences explicit without copying prompts, model
    responses, private intake, or machine-local absolute paths into the
    downloadable receipt.
    """

    issues = [
        item
        for item in payload.get("issues", [])
        if isinstance(item, dict) and str(item.get("code", ""))
    ]
    raw_terminal = payload.get("terminal_failure")
    terminal = raw_terminal if isinstance(raw_terminal, dict) else {}
    terminal_code = str(terminal.get("code") or terminal.get("terminal_code") or "")
    terminal_message = str(
        terminal.get("message") or terminal.get("safe_user_summary") or ""
    )[:500]
    terminal_stage = str(
        terminal.get("stage")
        or terminal.get("phase")
        or payload.get("stage")
        or payload.get("failing_stage")
        or ""
    )
    generation = payload.get("generation_projection")
    generation = generation if isinstance(generation, dict) else {}
    call_ledger = payload.get("call_ledger")
    call_ledger = call_ledger if isinstance(call_ledger, dict) else {}
    accepted_checkpoint = generation.get("accepted_checkpoint")
    accepted_checkpoint_hash = (
        str(accepted_checkpoint.get("checkpoint_hash", ""))
        if isinstance(accepted_checkpoint, dict)
        else ""
    )
    if not accepted_checkpoint_hash:
        accepted_checkpoint_hash = str(payload.get("checkpoint_hash", ""))
    calls = generation.get("call_receipts", [])
    attempts = generation.get("attempt_records", [])
    image_evidence = payload.get("image_evidence")
    image_evidence = image_evidence if isinstance(image_evidence, dict) else {}
    build_attempt = payload.get("build_attempt")
    build_attempt = build_attempt if isinstance(build_attempt, dict) else {}
    routes = [
        {
            "route_id": str(item.get("route_id", "")),
            "path": str(item.get("path", "")),
        }
        for item in payload.get("routes", [])
        if isinstance(item, dict)
    ]
    input_hashes = payload.get("input_hashes")
    safe_input_hashes = (
        {
            str(key): str(value)
            for key, value in input_hashes.items()
            if str(key) and isinstance(value, (str, int, float, bool))
        }
        if isinstance(input_hashes, dict)
        else {}
    )
    first_issue = issues[0] if issues else {}
    return {
        "status": str(payload.get("status", "unknown")),
        "source_status": str(payload.get("source_status", "")),
        "failing_stage": terminal_stage or str(payload.get("failing_stage", "")),
        "primary_issue": {
            "code": terminal_code or str(first_issue.get("code", "")),
            "message": terminal_message
            or str(first_issue.get("message", first_issue.get("normalized_message", "")))[:500],
        },
        "pipeline_issue_count": len(issues),
        "terminal_failure": {
            "code": terminal_code,
            "message": terminal_message,
        },
        "input_hashes": safe_input_hashes,
        "accepted_checkpoint_hash": accepted_checkpoint_hash,
        "candidate_id": str(payload.get("candidate_id", "")),
        "candidate_status": str(payload.get("candidate_status", "")),
        "build_outcome": str(build_attempt.get("status", "not_run")),
        "routes": routes,
        "attempt_count": len(attempts) if isinstance(attempts, list) else 0,
        "call_count": int(
            call_ledger.get("call_count", len(calls) if isinstance(calls, list) else 0) or 0
        ),
        "diagnostic_history_count": len(generation.get("diagnostic_history", []))
        if isinstance(generation.get("diagnostic_history", []), list)
        else 0,
        "request_rounds": int(
            call_ledger.get("request_rounds", generation.get("request_rounds", 0)) or 0
        ),
        "repair_rounds": int(
            call_ledger.get("repair_rounds", generation.get("repair_rounds", 0)) or 0
        ),
        "image_evidence": {
            "planned": int(image_evidence.get("planned_count", 0) or 0),
            "materialized": int(image_evidence.get("materialized_count", 0) or 0),
            "referenced_in_source": int(image_evidence.get("referenced_count", 0) or 0),
            "decoded_in_browser": int(image_evidence.get("decoded_count", 0) or 0),
            "visible_in_browser": int(image_evidence.get("visible_count", 0) or 0),
            "browser_evidence_complete": image_evidence.get("browser_evidence_complete"),
            "browser_evidence_not_run_count": int(
                image_evidence.get("browser_evidence_not_run_count", 0) or 0
            ),
        },
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

    # Failed/needs-attention exports keep the durable generation projection
    # under one nested field.  Promoted exports historically copied the same
    # values to the top level, so read both shapes and prefer the explicit
    # top-level receipt when present.  This keeps the handoff truthful instead
    # of showing ``unknown``/zero for evidence that is already persisted.
    raw_projection = payload.get("generation_projection")
    generation_evidence: dict[str, Any] = (
        raw_projection if isinstance(raw_projection, dict) else {}
    )
    quality = payload.get("quality_review")
    if not isinstance(quality, dict):
        quality = generation_evidence.get("quality_review")
    if isinstance(quality, dict) and isinstance(quality.get("accepted"), bool):
        quality_status = "accepted" if quality["accepted"] else "rejected"
    else:
        quality_status = "unknown"
    verification = payload.get("verification")
    if not isinstance(verification, dict):
        verification = generation_evidence.get("verification")
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
    if not isinstance(call_ledger, dict):
        call_ledger = generation_evidence.get("call_ledger")
    call_receipts = generation_evidence.get("call_receipts", [])
    if isinstance(call_ledger, dict) and call_ledger.get("call_count") is not None:
        call_count = call_ledger.get("call_count", 0)
    elif isinstance(call_receipts, list):
        call_count = len(call_receipts)
    else:
        call_count = 0
    request_rounds = (
        call_ledger.get("request_rounds", 0)
        if isinstance(call_ledger, dict)
        else generation_evidence.get("request_rounds", 0)
    )
    repair_rounds = (
        call_ledger.get("repair_rounds", 0)
        if isinstance(call_ledger, dict)
        else generation_evidence.get("repair_rounds", 0)
    )
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
    build_diagnostics = (
        [item for item in build_attempt.get("diagnostics", []) if isinstance(item, dict)]
        if isinstance(build_attempt, dict)
        else []
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
    terminal_failure = payload.get("terminal_failure")
    pipeline_issues = [
        item
        for item in payload.get("issues", [])
        if isinstance(item, dict) and str(item.get("code", ""))
    ]
    if isinstance(terminal_failure, dict):
        # Verification persists TerminalFailureReport; failed-export callers
        # may also provide the smaller stage/code/message shape. Normalize
        # both into the safe report vocabulary.
        terminal_failure = {
            "stage": str(
                terminal_failure.get("stage")
                or terminal_failure.get("phase")
                or ""
            ),
            "phase": str(terminal_failure.get("phase") or terminal_failure.get("stage") or ""),
            "code": str(
                terminal_failure.get("code")
                or terminal_failure.get("terminal_code")
                or ""
            ),
            "message": str(
                terminal_failure.get("message")
                or terminal_failure.get("safe_user_summary")
                or ""
            ),
        }
    elif pipeline_issues:
        first_issue = pipeline_issues[0]
        terminal_failure = {
            "code": str(first_issue.get("code", "")),
            "message": str(first_issue.get("message", "")),
        }
    artifact_lines = ["- Source project: `source/`"]
    if isinstance(handoff, dict) and handoff.get("dist_path"):
        artifact_lines.append("- Built site: `dist/`")
    if screenshots_path:
        artifact_lines.append(f"- Verification screenshots: `{screenshots_path}/`")
    image_line = "- Image evidence: `unknown`"
    if isinstance(image_evidence, dict):
        if "referenced_count" in image_evidence:
            image_line = (
                f"- Planned: `{image_evidence.get('planned_count', 0)}`; "
                f"materialized: `{image_evidence.get('materialized_count', 0)}`; "
                f"referenced: `{image_evidence.get('referenced_count', 0)}`; "
                f"decoded: `{image_evidence.get('decoded_count', 0)}`; "
                f"visible: `{image_evidence.get('visible_count', 0)}`; "
                f"failed: `{image_evidence.get('failed_count', 0)}`"
            )
        else:
            image_line = (
                f"- Planned: `{image_evidence.get('planned_count', 0)}`; "
                f"materialized: `{image_evidence.get('materialized_count', 0)}`; "
                f"rendered: `{image_evidence.get('rendered_count', 0)}`; "
                f"failed: `{image_evidence.get('failed_count', 0)}`"
            )
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
        f"- Failing stage: `{payload.get('failing_stage') or (terminal_failure or {}).get('stage') or (terminal_failure or {}).get('phase') or 'none recorded'!s}`",
        "",
        "## Artifact map",
        *artifact_lines,
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
        image_line,
        *(
            [
                "- "
                + json.dumps(
                    {
                        "resource_slot_id": item.get("resource_slot_id", ""),
                        "route_id": item.get("route_id", ""),
                        "section_id": item.get("section_id", ""),
                        "materialized": item.get("materialized", False),
                        "referenced_in_source": item.get(
                            "referenced_in_source", item.get("rendered", False)
                        ),
                        "decoded_in_browser": item.get("decoded_in_browser", False),
                        "visible_in_browser": item.get("visible_in_browser", False),
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
        "## Failure evidence",
        f"- Recorded pipeline issues: `{len(pipeline_issues)}`",
        *[
            f"- `{item.get('code', '')}`: {str(item.get('message', ''))[:400]}"
            for item in pipeline_issues
        ],
        *[
            f"- Build diagnostic `{item.get('code', '')}`: "
            f"{str(item.get('message', item.get('normalized_message', '')))[:400]}"
            for item in build_diagnostics
            if str(item.get("code", ""))
        ],
        (
            f"- Primary failure: `{terminal_failure.get('code', '')}` — "
            f"{terminal_failure.get('message', '')}"
            if isinstance(terminal_failure, dict)
            else "- Primary failure: `none recorded`"
        ),
        (
            f"- Generation phase: `{generation_evidence.get('phase', 'unknown')}`; "
            f"source ready: `{generation_evidence.get('source_ready', False)}`; "
            f"accepted checkpoint: `{(generation_evidence.get('accepted_checkpoint') or {}).get('checkpoint_hash', '')}`"
            if generation_evidence
            else "- Generation evidence: `none recorded`"
        ),
        (
        f"- Generation attempts: `{len(generation_evidence.get('attempt_records', []))}`; "
        f"context receipts: `{len(generation_evidence.get('context_receipts', []))}`; "
        f"call receipts: `{len(generation_evidence.get('call_receipts', []))}`; "
        f"diagnostic history: `{len(generation_evidence.get('diagnostic_history', []))}`; "
        f"request rounds: `{generation_evidence.get('request_rounds', 0)}`; "
            f"repair rounds: `{generation_evidence.get('repair_rounds', 0)}`"
            if generation_evidence
            else "- Generation ledger: `none recorded`"
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
    generation_projection: dict[str, Any] | None = None,
    terminal_failure: dict[str, Any] | None = None,
) -> Path | None:
    """Best-effort export of whatever source tree exists for a run that did
    not reach a promoted READY state (needs_attention or failed). Unlike
    `export_portfolio`, this never requires promotion-only state (a build
    manifest, an active preview, a candidate identity) -- only a run id and
    whatever the generation/verification workspace already has on disk. If a
    run failed before source creation, it still writes a metadata-only safe
    receipt with an empty `source/` directory so the failure remains
    downloadable and inspectable.

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
    source_exists = repo_dir.is_dir()
    if source_exists:
        build_attempt = await _attempt_best_effort_build(
            repo_dir=repo_dir, settings=settings, run_id=run_id
        )
    else:
        # Keep the export shape stable while making early planner/acquisition
        # failures downloadable. The empty source directory is deliberately
        # not presented as a runnable site; the report records that no build
        # was attempted because no source tree existed.
        repo_dir.mkdir(parents=True, exist_ok=True)
        build_attempt = {
            "status": "not_run",
            "diagnostics": [
                {
                    "code": "SOURCE_NOT_CREATED",
                    "message": "The run failed before a generated source tree was created.",
                }
            ],
        }
    failure_record = terminal_failure or {
        "stage": "generation_or_verification",
        "code": reason,
        "message": (
            str((issues or [{}])[0].get("message", ""))
            if issues
            else "The run ended before verified preview promotion."
        ),
    }
    return export_portfolio(
        settings=settings,
        run_id=run_id,
        repo_dir=repo_dir,
        screenshots_dir=run_root / "verification-screenshots",
        metadata={
            "status": "needs_attention",
            "export_reason": reason,
            "issues": issues or [],
            "terminal_failure": failure_record,
            "generation_projection": generation_projection or {},
            "build_attempt": build_attempt,
            "source_status": "available" if source_exists else "not_created",
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
    "build_safe_evidence_summary",
    "export_failed_run",
    "export_portfolio",
]
