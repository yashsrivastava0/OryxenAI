"""Final trusted source/contract integrity gate."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import Diagnostic, SitePlan
from oryxenai.agents.code_generator.core.source_validation import (
    _canonical_visible_text,
    validate_repository,
)
from oryxenai.agents.code_generator.core.typescript_ast_audit import audit_typescript_source

_IMPORT_RE = re.compile(
    r"(?:import\s+(?:[^;]*?\s+from\s+)?|export\s+[^;]*?\s+from\s+|import\s*\()\s*[\"']([^\"']+)[\"']"
)
_COMMENT_RE = re.compile(r"/\*.*?\*/|//[^\r\n]*|<!--[\s\S]*?-->", re.DOTALL)
_COMPONENT_IMPORT_RE = re.compile(
    r"import\s+(?P<bindings>[\s\S]*?)\s+from\s+[\"'](?P<module>[^\"']+)[\"']"
)
_HEADING_TEXT_RE = re.compile(r"<h[1-6]\b[^>]*>([^<]*)</h[1-6]>", re.DOTALL)


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


def _without_comments(value: str) -> str:
    """Return source suitable for binding checks, excluding marker comments."""

    return _COMMENT_RE.sub(" ", value)


def _local_binding_tokens(local_paths: list[str]) -> set[str]:
    """Translate pack-relative paths into the paths the generator can use.

    Build Preparation paths are archive paths (``resources/...``). Media is
    served from ``public/resources/pack``; component source is copied into
    ``src/generated/resources/pack``. Both forms are accepted only as actual
    source references, never as comments or manifest text.
    """

    tokens: set[str] = set()
    for value in local_paths:
        normalized = value.replace("\\", "/").strip("/")
        if not normalized:
            continue
        tokens.add(normalized)
        suffix = Path(normalized).suffix
        if suffix:
            tokens.add(normalized[: -len(suffix)])
        if normalized.startswith("resources/"):
            relative = normalized.removeprefix("resources/")
            tokens.update(
                {
                    f"/resources/pack/{relative}",
                    f"resources/pack/{relative}",
                    f"public/resources/pack/{relative}",
                    f"generated/resources/pack/{relative}",
                    f"src/generated/resources/pack/{relative}",
                }
            )
        if normalized.startswith("src/generated/resources/acquired/"):
            relative = normalized.removeprefix("src/generated/resources/acquired/")
            tokens.update(
                {
                    f"/resources/acquired/{relative}",
                    f"resources/acquired/{relative}",
                    f"public/resources/acquired/{relative}",
                    f"src/generated/resources/acquired/{relative}",
                }
            )
        tokens.add(Path(normalized).name)
    return tokens


def _slot_is_bound(
    *,
    slot: dict[str, Any],
    source_by_path: dict[str, str],
) -> bool:
    """Check executable source usage for one required execution slot.

    This deliberately does not search the complete repository for arbitrary
    token presence: generated manifests and comments are not implementation.
    """

    source_files = {
        path: _without_comments(text)
        for path, text in source_by_path.items()
        if not path.startswith("src/generated/")
        and not path.startswith("public/")
        and path not in {"package.json", "package-lock.json"}
    }
    source = "\n".join(source_files.values())
    resolution_type = str(slot.get("resolution_type", ""))
    category = str(slot.get("category", "")).casefold()
    if resolution_type == "target_package_binding":
        package_name = str(slot.get("package_name", ""))
        if not package_name:
            return False
        package_imports = [
            match.group(1)
            for text in source_files.values()
            for match in _IMPORT_RE.finditer(text)
            if match.group(1) == package_name
        ]
        if not package_imports:
            return False
        expected = [str(item) for item in slot.get("expected_exports", []) if str(item)]
        return not expected or any(
            re.search(rf"\b{re.escape(item)}\b", source) for item in expected
        )
    if resolution_type != "local_materialized":
        return True
    tokens = _local_binding_tokens([str(item) for item in slot.get("local_paths", []) if str(item)])
    if not tokens:
        return False
    if category in {"component_source", "visual_component", "component"}:
        imports = [
            match for text in source_files.values() for match in _COMPONENT_IMPORT_RE.finditer(text)
        ]
        for match in imports:
            module = match.group("module").replace("\\", "/")
            if not any(token in module or module.endswith(Path(token).name) for token in tokens):
                continue
            bindings = match.group("bindings")
            names = re.findall(r"\b[A-Za-z_$][\w$]*\b", bindings)
            if any(re.search(rf"\b{re.escape(name)}\b", source[match.end() :]) for name in names):
                return True
        return False
    # Media and fonts must be used as a URL/CSS value. A filename in a
    # comment, a manifest, or a generated resource file is intentionally not
    # enough.
    return any(token in source for token in tokens)


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
    diagnostics.extend(
        audit_typescript_source(
            repo_dir,
            files=files,
            plan=plan,
            projections=projections,
        )
    )
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
        route_anchor_source = files[route_file]
        route_prefix = f"src/routes/{storage_key}/"
        route_source = "\n".join(
            text for file_path, text in files.items() if file_path.startswith(route_prefix)
        )
        # Model responses occasionally contain UTF-8 text decoded as
        # Windows-1252 (for example ``Iâ€™m``) or harmless JSX quote wrappers.
        # Compare approved copy in the same canonical visible-text space used
        # by the source validator so encoding noise cannot trigger a repair
        # loop or make an otherwise grounded route fail closed.
        canonical_route_source = _canonical_visible_text(route_source)
        if route_id not in route_anchor_source:
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
            content_anchor = f'data-content-id="{section_id}"'
            if section_id and (
                section_id not in route_source or content_anchor not in route_source
            ):
                diagnostics.append(
                    _diag(
                        "SOURCE_SECTION_COVERAGE_MISSING",
                        "An approved section is missing its route-source content anchor.",
                        file=route_file,
                        route_id=route_id,
                    )
                )
            section_content = section.get("content", {})
            if isinstance(section_content, dict):
                heading = str(section_content.get("heading", "")).strip()
                heading_present = any(
                    _canonical_visible_text(match.group(1)) == _canonical_visible_text(heading)
                    for match in _HEADING_TEXT_RE.finditer(route_source)
                )
                if heading and not heading_present:
                    diagnostics.append(
                        _diag(
                            "SOURCE_CONTENT_COVERAGE_MISSING",
                            "Approved public content is absent from route source.",
                            file=route_file,
                            route_id=route_id,
                        )
                    )
            for text in _strings(section_content):
                # Prose only: single-word enum-ish values are data shape,
                # not rendered copy the route must carry verbatim.
                if (
                    " " in text
                    and len(text) >= 6
                    and _canonical_visible_text(text) not in canonical_route_source
                ):
                    diagnostics.append(
                        _diag(
                            "SOURCE_CONTENT_COVERAGE_MISSING",
                            "Approved public content is absent from route source.",
                            file=route_file,
                            route_id=route_id,
                        )
                    )
    execution = projections.get("execution/contract.json", {})
    resource_ledger = projections.get("resources/ledger.json", {})
    requests_by_id = {
        str(item.get("request_id", "")): item
        for item in resource_ledger.get("requests", [])
        if isinstance(item, dict)
    }
    bindings_by_request_hash = {
        str(item.get("request_id_or_pack_need_id", "")): item
        for item in resource_ledger.get("active_bindings", [])
        if isinstance(item, dict)
    }
    for slot in execution.get("slots", []) if isinstance(execution, dict) else []:
        if not isinstance(slot, dict):
            continue
        resolution = slot.get("resolution", {})
        resolution_type = (
            str(resolution.get("resolution_type", "")) if isinstance(resolution, dict) else ""
        )
        local_paths = resolution.get("local_paths", []) if isinstance(resolution, dict) else []
        if resolution_type == "delegated_acquisition":
            delegated_request = requests_by_id.get(
                f"delegated-{slot.get('resource_slot_id', '')}", {}
            )
            request_hash = str(delegated_request.get("request_hash", ""))
            delegated_binding = bindings_by_request_hash.get(request_hash, {})
            local_paths = delegated_binding.get("local_paths", [])
            resolution_type = "local_materialized" if local_paths else resolution_type
        # Local recipes are intentionally non-binding design guidance. The
        # required visual floor is concrete local material or a package import.
        binding_slot = {
            "category": str(slot.get("category", "")),
            "resolution_type": resolution_type,
            "local_paths": local_paths,
            "package_name": (
                str(resolution.get("package_name", "")) if isinstance(resolution, dict) else ""
            ),
            "expected_exports": (
                resolution.get("expected_exports", []) if isinstance(resolution, dict) else []
            ),
        }
        if (
            slot.get("required")
            and resolution_type != "local_recipe"
            and not _slot_is_bound(slot=binding_slot, source_by_path=files)
        ):
            diagnostics.append(
                _diag(
                    "SOURCE_EXECUTION_SLOT_UNUSED",
                    "A required execution slot has no executable source binding; comments and manifests do not count.",
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
        str(route.get("route_id", "")): "\n".join(
            text
            for path, text in files.items()
            if path.startswith(
                "src/routes/"
                + str(route.get("storage_key", route.get("route_id", "")))
                .replace(chr(92), "/")
                .removeprefix("routes/")
                .strip("/")
                + "/"
            )
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
        trace_marker = f"OryxenAI interaction marker: {interaction.interaction_id}"
        if (
            interaction.interaction_id
            and marker not in route_source
            and trace_marker not in route_source
        ):
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
