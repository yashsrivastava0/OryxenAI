"""Final trusted source/contract integrity gate."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import Diagnostic, SitePlan
from oryxenai.agents.code_generator.core.source_validation import validate_repository

_IMPORT_RE = re.compile(
    r"(?:import\s+(?:[^;]*?\s+from\s+)?|export\s+[^;]*?\s+from\s+|import\s*\()\s*[\"']([^\"']+)[\"']"
)


def _diag(code: str, message: str, *, file: str = "", route_id: str = "") -> Diagnostic:
    fingerprint = hashlib.sha256(f"{code}:{file}:{route_id}:{message}".encode()).hexdigest()[:24]
    return Diagnostic(
        diagnostic_id=f"diagnostic-{fingerprint}",
        group="source_contract",
        code=code,
        phase="source_contract",
        route_id=route_id,
        normalized_message=message,
        file=file,
        fingerprint=fingerprint,
    )


def _all_text(repo_dir: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in sorted(repo_dir.rglob("*")):
        if not path.is_file() or any(part in {"node_modules", "dist"} for part in path.parts):
            continue
        if path.suffix.lower() not in {".ts", ".tsx", ".css", ".html", ".json"}:
            continue
        try:
            values[path.relative_to(repo_dir).as_posix()] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    return values


def _strings(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, str) and value.strip():
        result.add(" ".join(value.split()))
    elif isinstance(value, dict):
        for item in value.values():
            result.update(_strings(item))
    elif isinstance(value, list):
        for item in value:
            result.update(_strings(item))
    return result


def _resolve_local(repo_dir: Path, source: Path, imported: str) -> bool:
    if imported.startswith("/"):
        target = (repo_dir / imported.lstrip("/")).resolve()
    else:
        target = (source.parent / imported).resolve()
    if not target.is_relative_to(repo_dir.resolve()):
        return False
    if target.is_file():
        return True
    for suffix in (".ts", ".tsx", ".css", ".json"):
        if target.with_suffix(suffix).is_file():
            return True
    return (target / "index.ts").is_file() or (target / "index.tsx").is_file()


def validate_final_source(
    repo_dir: Path,
    *,
    plan: SitePlan,
    projections: dict[str, dict[str, Any]],
    allowed_packages: set[str],
    public_text: set[str],
    work_unit_id: str = "final-source",
) -> list[Diagnostic]:
    del work_unit_id
    diagnostics: list[Diagnostic] = []
    source_diagnostics = validate_repository(
        repo_dir,
        allowed_packages=allowed_packages,
        public_text=public_text,
        max_source_bytes=8 * 1024 * 1024,
        work_unit_id="final-source",
    )
    diagnostics.extend(
        _diag(item.code, item.normalized_message, file=item.file, route_id=item.route_id)
        for item in source_diagnostics
    )
    files = _all_text(repo_dir)
    combined = "\n".join(files.values())
    registry = files.get("src/generated/route-registry.ts", "")
    site = projections.get("site/contract.json", {})
    routes = [item for item in site.get("routes", []) if isinstance(item, dict)]
    content_by_route = {
        str(item.get("route_id", "")): item
        for item in site.get("public_content", [])
        if isinstance(item, dict)
    }
    for route in routes:
        route_id = str(route.get("route_id", ""))
        path = str(route.get("path", ""))
        storage_key = str(route.get("storage_key", route_id)).replace("\\", "/").strip("/")
        if storage_key.startswith("routes/"):
            storage_key = storage_key.removeprefix("routes/")
        route_file = f"src/routes/{storage_key}/index.tsx"
        if route_id not in registry or path not in registry:
            diagnostics.append(
                _diag(
                    "SOURCE_ROUTE_REGISTRY_MISMATCH",
                    "The generated route registry does not match the approved route.",
                    file="src/generated/route-registry.ts",
                    route_id=route_id,
                )
            )
        if route_file not in files:
            diagnostics.append(
                _diag(
                    "SOURCE_ROUTE_FILE_MISSING",
                    "An approved route has no generated route source.",
                    file=route_file,
                    route_id=route_id,
                )
            )
            continue
        route_source = files[route_file]
        if route_id not in route_source:
            diagnostics.append(
                _diag(
                    "SOURCE_ROUTE_ID_MISSING",
                    "Route source does not carry its authoritative route ID.",
                    file=route_file,
                    route_id=route_id,
                )
            )
        content_pack = content_by_route.get(route_id, {})
        for section in content_pack.get("sections", []) if isinstance(content_pack, dict) else []:
            if not isinstance(section, dict):
                continue
            section_id = str(section.get("section_id", ""))
            if section_id and section_id not in route_source:
                diagnostics.append(
                    _diag(
                        "SOURCE_SECTION_COVERAGE_MISSING",
                        "An approved section is not mapped to route source.",
                        file=route_file,
                        route_id=route_id,
                    )
                )
            for text in _strings(section.get("content", {})):
                # Prose only: single-word enum-ish values are data shape,
                # not rendered copy the route must carry verbatim.
                if " " in text and len(text) >= 6 and text not in route_source:
                    diagnostics.append(
                        _diag(
                            "SOURCE_CONTENT_COVERAGE_MISSING",
                            "Approved public content is absent from route source.",
                            file=route_file,
                            route_id=route_id,
                        )
                    )
    execution = projections.get("execution/contract.json", {})
    for slot in execution.get("slots", []) if isinstance(execution, dict) else []:
        if not isinstance(slot, dict):
            continue
        slot_id = str(slot.get("resource_slot_id", ""))
        resolution = slot.get("resolution", {})
        local_paths = resolution.get("local_paths", []) if isinstance(resolution, dict) else []
        package_name = (
            str(resolution.get("package_name", "")) if isinstance(resolution, dict) else ""
        )
        evidence = [slot_id, package_name, *[str(item) for item in local_paths]]
        if slot.get("required") and not any(item and item in combined for item in evidence):
            diagnostics.append(
                _diag(
                    "SOURCE_EXECUTION_SLOT_UNUSED",
                    "A required v3 execution slot has no source binding.",
                    file="src/generated/resource-manifest.ts",
                    route_id=str(slot.get("route_id", "")),
                )
            )
    for path, text in files.items():
        source_path = repo_dir / path
        for imported in _IMPORT_RE.findall(text):
            if imported.startswith((".", "/")) and not _resolve_local(
                repo_dir, source_path, imported
            ):
                diagnostics.append(
                    _diag(
                        "SOURCE_LOCAL_IMPORT_MISSING",
                        "A generated local import does not resolve.",
                        file=path,
                    )
                )
    visual = projections.get("design/visual-direction.json", {})
    for required_text in _strings(visual.get("global", {}).get("must_preserve", [])):
        if required_text and required_text not in combined:
            diagnostics.append(
                _diag(
                    "SOURCE_VISUAL_CONTRACT_MISSING",
                    "An approved preservation requirement is absent from source.",
                    file="src/generated/content-manifest.ts",
                )
            )
    route_source_by_id = {
        str(route.get("route_id", "")): files.get(
            f"src/routes/{str(route.get('storage_key', route.get('route_id', ''))).replace(chr(92), '/').removeprefix('routes/').strip('/')}/index.tsx",
            "",
        )
        for route in routes
        if isinstance(route, dict)
    }
    for coverage in plan.acceptance_coverage:
        marker = coverage.source_marker.strip()
        route_source = route_source_by_id.get(coverage.route_id, combined)
        if marker and marker not in route_source:
            diagnostics.append(
                _diag(
                    "SOURCE_ACCEPTANCE_MARKER_MISSING",
                    "A planned acceptance criterion has no declared source marker.",
                    route_id=coverage.route_id,
                )
            )
    for interaction in plan.interactions:
        marker = f'data-interaction-id="{interaction.interaction_id}"'
        route_source = route_source_by_id.get(interaction.route_id, combined)
        if interaction.interaction_id and marker not in route_source:
            diagnostics.append(
                _diag(
                    "SOURCE_INTERACTION_MARKER_MISSING",
                    "A planned interaction has no traceable source marker.",
                    route_id=interaction.route_id,
                )
            )
    return _dedupe(diagnostics)


def _dedupe(values: list[Diagnostic]) -> list[Diagnostic]:
    seen: set[str] = set()
    result: list[Diagnostic] = []
    for value in values:
        if value.fingerprint not in seen:
            seen.add(value.fingerprint)
            result.append(value)
    return result
