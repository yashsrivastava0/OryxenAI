"""Trusted source-change and generated-repository policy validation."""

from __future__ import annotations

import html
import re
import unicodedata
from contextlib import suppress
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import (
    GenerationChanges,
    SourceDiagnostic,
    SourceFileChange,
)


class SourceValidationError(ValueError):
    def __init__(self, code: str, message: str, *, file: str = "") -> None:
        self.code = code
        self.message = message
        self.file = file
        super().__init__(message)


_IMPORT_RE = re.compile(
    r"(?:import\s+(?:[^;]*?\s+from\s+)?|export\s+[^;]*?\s+from\s+|import\s*\()\s*[\"']([^\"']+)[\"']"
)
_LOCAL_IMPORT_BINDINGS_RE = re.compile(
    r"(?:\bimport\s+(?P<import_bindings>[^;]*?)\s+from\s+|"
    r"\bexport\s+(?P<export_bindings>\{[^}]*\})\s+from\s+)"
    r"[\"'](?P<module>[^\"']+)[\"']"
)
_EXPORT_DECL_RE = re.compile(
    r"\bexport\s+(?:declare\s+)?(?:const|let|var|function|class|type|interface|enum)\s+"
    r"([A-Za-z_$][\w$]*)"
)
_EXPORT_LIST_RE = re.compile(r"\bexport\s*\{([^}]*)\}")
_REMOTE_RE = re.compile(r"https?://|//[A-Za-z0-9]", re.IGNORECASE)
_FORBIDDEN_RUNTIME_RE = re.compile(r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(")
_PLACEHOLDER_TERMS = ("lorem ipsum", "todo", "placeholder", "coming soon", "fake success")
_LINK_ATTR_RE = re.compile(r"""\b(?:href|src)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_APPROVED_URL_RE = re.compile(r"https?://[^\s\"'<>)\]}]+", re.IGNORECASE)


def _approved_urls(public_text: set[str]) -> set[str]:
    """Extract the external URLs that appear verbatim in approved content."""

    urls: set[str] = set()
    for entry in public_text:
        for match in _APPROVED_URL_RE.finditer(entry or ""):
            urls.add(match.group(0).rstrip(".,;:"))
    return urls


def _strip_approved_links(text: str, public_text: set[str]) -> str:
    """Blank URLs that appear verbatim in approved public content.

    A portfolio's approved contact/project links are content, not runtime
    network dependencies; they may appear in href attributes or as plain
    data literals. Everything else stays subject to the remote reference
    ban. Validation only — the applied file keeps the real URL.
    """

    if not public_text:
        return text

    def replace_attr(match: re.Match[str]) -> str:
        url = match.group(1)
        if url.startswith(("http://", "https://", "//")) and any(
            url.casefold() in (entry or "").casefold() for entry in public_text
        ):
            return 'href="#approved-external-link"'
        return match.group(0)

    scannable = _LINK_ATTR_RE.sub(replace_attr, text)
    for url in _approved_urls(public_text):
        scannable = scannable.replace(url, "#approved-external-link")
        scannable = scannable.replace(url.casefold(), "#approved-external-link")
    return scannable


def validate_generation_changes(
    changes: GenerationChanges,
    *,
    owned_paths: list[str],
    repo_dir: Path,
    max_file_bytes: int,
    max_response_bytes: int,
    allowed_packages: set[str],
    public_text: set[str],
) -> list[SourceFileChange]:
    if (
        sum(len(change.complete_utf8_content.encode("utf-8")) for change in changes.files)
        > max_response_bytes
    ):
        raise SourceValidationError(
            "SOURCE_RESPONSE_TOO_LARGE", "The generation response exceeds its size limit."
        )
    seen: set[str] = set()
    normalized: list[SourceFileChange] = []
    for change in changes.files:
        path = _safe_path(change.path)
        if path in seen:
            raise SourceValidationError(
                "SOURCE_DUPLICATE_PATH",
                "The generation response contains duplicate paths.",
                file=path,
            )
        seen.add(path)
        if not _owned(path, owned_paths):
            raise SourceValidationError(
                "SOURCE_OWNERSHIP_ESCAPE",
                "The change is outside the work unit ownership set.",
                file=path,
            )
        data = change.complete_utf8_content.encode("utf-8")
        if len(data) > max_file_bytes:
            raise SourceValidationError(
                "SOURCE_FILE_TOO_LARGE", "A generated file exceeds the configured limit.", file=path
            )
        if path in {
            "package.json",
            "package-lock.json",
            "vite.config.ts",
            "tsconfig.json",
            "tsconfig.app.json",
            "tsconfig.node.json",
            "index.html",
            "src/main.tsx",
            "src/app/AppRouter.tsx",
            "src/app/PreviewBridge.ts",
            "src/app/ResourceUrl.ts",
            "src/app/ErrorBoundary.tsx",
            "src/design/global.css",
        }:
            raise SourceValidationError(
                "SOURCE_TRUSTED_FILE_MUTATION",
                "The model cannot mutate trusted toolchain files.",
                file=path,
            )
        existing = (repo_dir / path).is_file()
        if change.operation == "create" and existing:
            raise SourceValidationError(
                "SOURCE_CREATE_EXISTS",
                "A create change would overwrite an existing source file.",
                file=path,
            )
        if change.operation == "replace" and not existing:
            raise SourceValidationError(
                "SOURCE_REPLACE_MISSING",
                "A replace change targets a source file that does not exist.",
                file=path,
            )
        if "\x00" in change.complete_utf8_content:
            raise SourceValidationError(
                "SOURCE_INVALID_UTF8", "A generated file contains a null character.", file=path
            )
        _validate_text_policy(change.complete_utf8_content, path, public_text)
        _validate_imports(change.complete_utf8_content, path, allowed_packages)
        normalized.append(change.model_copy(update={"path": path}))
    return normalized


def validate_repository(
    repo_dir: Path,
    *,
    allowed_packages: set[str],
    public_text: set[str],
    max_source_bytes: int,
    work_unit_id: str,
) -> list[SourceDiagnostic]:
    total = 0
    diagnostics: list[SourceDiagnostic] = []
    for path in sorted(repo_dir.rglob("*")):
        if not path.is_file() or any(part in {"node_modules", "dist"} for part in path.parts):
            continue
        relative = path.relative_to(repo_dir).as_posix()
        data = path.read_bytes()
        total += len(data)
        if total > max_source_bytes:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_TOTAL_TOO_LARGE",
                    "Generated source exceeds the configured total size.",
                    work_unit_id,
                    relative,
                )
            )
            break
        if path.suffix.lower() not in {".ts", ".tsx", ".css", ".html", ".json"}:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ENCODING_INVALID",
                    "Generated source is not UTF-8.",
                    work_unit_id,
                    relative,
                )
            )
            continue
        try:
            trusted_non_source = (
                relative.startswith("public/resources/")
                or relative.startswith("public/licences/")
                # Pipeline-materialized trusted artifacts carry approved
                # content (including approved external links) as data.
                or relative.startswith("src/generated/")
                or relative == "src/content/public-data.ts"
            )
            if (
                relative
                not in {
                    "package.json",
                    "package-lock.json",
                    "vite.config.ts",
                    "tsconfig.json",
                    "tsconfig.app.json",
                    "tsconfig.node.json",
                    "index.html",
                    "src/main.tsx",
                    "src/app/AppRouter.tsx",
                    "src/app/PreviewBridge.ts",
                    "src/app/ResourceUrl.ts",
                    "src/app/ErrorBoundary.tsx",
                    "src/design/global.css",
                }
                and not trusted_non_source
            ):
                _validate_text_policy(text, relative, public_text)
            if not trusted_non_source:
                _validate_imports(text, relative, allowed_packages)
        except SourceValidationError as exc:
            diagnostics.append(_diagnostic(exc.code, exc.message, work_unit_id, relative))
    return diagnostics


def validate_local_imports(
    repo_dir: Path,
    relative_paths: list[str],
    *,
    work_unit_id: str,
) -> list[SourceDiagnostic]:
    """Validate local module resolution and named bindings for a bounded set.

    Route batches are intentionally checked before the complete route shell
    exists, so the whole-site TypeScript audit cannot run at that point. This
    narrower check still catches the mechanical failures that matter to a
    batch: a section importing a trusted module or sibling that does not
    resolve from its real source location, or naming an export the target
    module does not provide. The latter prevents a batch from checkpointing a
    self-importing or invalid re-export that would only be discovered after
    route composition.
    """

    diagnostics: list[SourceDiagnostic] = []
    root = repo_dir.resolve()
    for relative in sorted({value.replace("\\", "/") for value in relative_paths}):
        source = (repo_dir / relative).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for imported in _IMPORT_RE.findall(text):
            if not imported.startswith((".", "/", "@/")):
                continue
            if _resolve_local_import(repo_dir, source, imported):
                continue
            diagnostics.append(
                _diagnostic(
                    "SOURCE_LOCAL_IMPORT_MISSING",
                    f"Generated local import does not resolve: {imported}",
                    work_unit_id,
                    relative,
                )
            )
        for match in _LOCAL_IMPORT_BINDINGS_RE.finditer(text):
            imported = match.group("module")
            if not imported.startswith((".", "/", "@/")):
                continue
            target = _resolve_local_import_path(repo_dir, source, imported)
            if target is None or target.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx"}:
                continue
            bindings = match.group("import_bindings") or match.group("export_bindings") or ""
            names = _local_binding_names(bindings)
            if not names:
                continue
            exported = _module_exports(target)
            for name in sorted(names - exported):
                diagnostics.append(
                    _diagnostic(
                        "SOURCE_LOCAL_EXPORT_MISSING",
                        f"Generated local import names an export the target module does not provide: {name}",
                        work_unit_id,
                        relative,
                    )
                )
    return diagnostics


def validate_route_batch_contract(
    repo_dir: Path,
    relative_paths: list[str],
    *,
    route_id: str = "",
    section_ids: list[str] | None = None,
    source_markers: list[str] | None = None,
    work_unit_id: str,
) -> list[SourceDiagnostic]:
    """Validate section ownership before a split batch is checkpointed.

    A split route batch has one concrete TSX owner per assigned section.  The
    route composer later assembles those independent modules.  Treating the
    first file as an aggregator makes a superficially valid checkpoint hide
    duplicate section anchors and leaves the other owned files as unrendered
    helpers, so this boundary validates the ownership map across every
    concrete file in the batch.
    """

    diagnostics = validate_local_imports(
        repo_dir,
        relative_paths,
        work_unit_id=work_unit_id,
    )
    normalized_paths = [value.replace("\\", "/") for value in relative_paths]
    source_paths = [
        value for value in normalized_paths if value.endswith(".tsx") and "*" not in value
    ]
    if not source_paths:
        return diagnostics

    sources: dict[str, str] = {}
    for relative in source_paths:
        try:
            sources[relative] = (repo_dir / relative).resolve().read_text(
                encoding="utf-8"
            )
        except (OSError, UnicodeDecodeError):
            continue

    anchor_relative = source_paths[0]
    anchor_text = sources.get(anchor_relative, "")
    if route_id and route_id not in anchor_text:
        diagnostics.append(
            _diagnostic(
                "SOURCE_ROUTE_BATCH_ROUTE_ID_MISSING",
                f"The route-batch anchor must contain the authoritative route ID: {route_id}",
                work_unit_id,
                anchor_relative,
            )
        )

    section_pattern = re.compile(r'data-content-id\s*=\s*["\']([^"\']+)["\']')
    assigned = set(section_ids or [])
    owners: dict[str, list[str]] = {section_id: [] for section_id in section_ids or []}
    for relative, text in sources.items():
        literals = section_pattern.findall(text)
        assigned_literals = [value for value in literals if value in assigned]
        if len(assigned_literals) != 1:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_SECTION_OWNERSHIP_INVALID",
                    "Each owned TSX file must contain exactly one assigned literal "
                    "data-content-id section anchor; do not aggregate sections or "
                    "return helper-only files.",
                    work_unit_id,
                    relative,
                )
            )
            continue
        owners[assigned_literals[0]].append(relative)

    for section_id in section_ids or []:
        owner_paths = owners[section_id]
        if len(owner_paths) != 1:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_SECTION_OWNERSHIP_INVALID",
                    f"The assigned section {section_id} must have exactly one owned "
                    "TSX file; split batches cannot duplicate or aggregate section anchors.",
                    work_unit_id,
                    anchor_relative,
                )
            )
            continue
        owner_relative = owner_paths[0]
        owner_text = sources.get(owner_relative, "")
        content_count = len(
            re.findall(
                rf"data-content-id\s*=\s*[\"']{re.escape(section_id)}[\"']",
                owner_text,
            )
        )
        if content_count != 1:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_ANCHOR_INVALID",
                    f"The section owner must contain exactly one data-content-id for {section_id}.",
                    work_unit_id,
                    owner_relative,
                )
            )
        dom_id_count = len(
            re.findall(
                rf"(?<![\w-])id\s*=\s*[\"']{re.escape(section_id)}[\"']",
                owner_text,
            )
        )
        if dom_id_count != 1:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_DOM_ID_INVALID",
                    f"The section owner must expose exactly one DOM id matching {section_id}.",
                    work_unit_id,
                    owner_relative,
                )
            )
    for marker in source_markers or []:
        if marker and marker not in text:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_MARKER_MISSING",
                    f"The route-batch anchor is missing its assigned source marker: {marker}",
                    work_unit_id,
                    anchor_relative,
                )
            )
    return diagnostics


def _safe_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or bool(PureWindowsPath(value).drive)
        or ".." in path.parts
        or any(not part or any(ord(char) < 32 for char in part) for part in path.parts)
    ):
        raise SourceValidationError("SOURCE_PATH_UNSAFE", "The generated path is unsafe.")
    if any(part.startswith(".") for part in path.parts):
        raise SourceValidationError("SOURCE_HIDDEN_PATH", "Hidden generated paths are not allowed.")
    return path.as_posix()


def _resolve_local_import(repo_dir: Path, source: Path, imported: str) -> bool:
    return _resolve_local_import_path(repo_dir, source, imported) is not None


def _resolve_local_import_path(repo_dir: Path, source: Path, imported: str) -> Path | None:
    if imported.startswith("@/"):
        target = (repo_dir / "src" / imported[2:]).resolve()
    elif imported.startswith("/"):
        target = (repo_dir / imported.lstrip("/")).resolve()
    else:
        target = (source.parent / imported).resolve()
    root = repo_dir.resolve()
    if not target.is_relative_to(root):
        return None
    candidates = [target]
    candidates.extend(
        target.with_suffix(suffix) for suffix in (".ts", ".tsx", ".js", ".jsx", ".css", ".json")
    )
    candidates.extend(target / f"index{suffix}" for suffix in (".ts", ".tsx", ".js", ".jsx"))
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def _local_binding_names(bindings: str) -> set[str]:
    """Return source export names referenced by an import/re-export clause."""

    value = bindings.strip()
    if not value or value.startswith("*"):
        return set()
    names: set[str] = set()
    named_match = re.search(r"\{([^}]*)\}", value, re.DOTALL)
    if named_match:
        for item in named_match.group(1).split(","):
            item = item.strip()
            if not item:
                continue
            item = re.sub(r"^type\s+", "", item).strip()
            source_name = item.split(" as ", 1)[0].strip()
            if re.fullmatch(r"[A-Za-z_$][\w$]*", source_name):
                names.add(source_name)
        value = value[: named_match.start()].rstrip(" ,")
    # A default import is the identifier before the optional named clause.
    default_match = re.match(r"^(?:type\s+)?([A-Za-z_$][\w$]*)\s*(?:,|$)", value)
    if default_match:
        names.add("default")
    return names


def _module_exports(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    clean = re.sub(r"/\*.*?\*/|//[^\r\n]*", " ", text, flags=re.DOTALL)
    exports = set(_EXPORT_DECL_RE.findall(clean))
    for group in _EXPORT_LIST_RE.findall(clean):
        for item in group.split(","):
            source_name = item.strip().split(" as ", 1)[0].strip()
            if source_name and re.fullmatch(r"[A-Za-z_$][\w$]*", source_name):
                exports.add(source_name)
            alias = item.strip().split(" as ", 1)[-1].strip()
            if alias and re.fullmatch(r"[A-Za-z_$][\w$]*", alias):
                exports.add(alias)
    if re.search(r"\bexport\s+default\b", clean):
        exports.add("default")
    return exports


def _owned(path: str, owned_paths: list[str]) -> bool:
    for owner in owned_paths:
        normalized = owner.replace("\\", "/").rstrip("/")
        if normalized.endswith("/**") and path.startswith(normalized[:-2]):
            return True
        if path == normalized:
            return True
    return False


def _validate_text_policy(text: str, path: str, public_text: set[str]) -> None:
    lowered = text.casefold()
    scannable = _strip_approved_links(text, public_text)
    if _REMOTE_RE.search(scannable) or _FORBIDDEN_RUNTIME_RE.search(text):
        raise SourceValidationError(
            "SOURCE_RUNTIME_NETWORK",
            "Generated source contains a remote or runtime network reference.",
            file=path,
        )
    if any(term in lowered for term in _PLACEHOLDER_TERMS):
        raise SourceValidationError(
            "SOURCE_PLACEHOLDER", "Generated source contains placeholder content.", file=path
        )
    if path.endswith((".ts", ".tsx")) and "process.env" in text:
        raise SourceValidationError(
            "SOURCE_SECRET_ACCESS", "Generated source cannot access environment secrets.", file=path
        )
    if path.startswith("src/routes/") and public_text:
        suspicious = re.findall(r">([^<>\n]{4,})<", text)
        for value in suspicious:
            clean = " ".join(value.split())
            if (
                clean
                and not _allowed_public_literal(clean, public_text)
                and any(char.isalpha() for char in clean)
                # Five-plus-word spans are prose; shorter spans are
                # navigational micro-labels the direction permits.
                and len(clean.split()) >= 5
            ):
                raise SourceValidationError(
                    "SOURCE_UNGROUNDED_COPY",
                    "Route source contains copy not present in the approved public contract.",
                    file=path,
                )


def _allowed_public_literal(value: str, public_text: set[str]) -> bool:
    # JSX text may carry harmless presentation wrappers (quotes around a
    # title) or HTML entities (``&amp;``). Compare the visible text rather than
    # the source-encoding wrapper so the validator does not reject a faithful
    # rendering of approved content.
    folded = _canonical_visible_text(value)
    return any(
        folded in _canonical_visible_text(allowed) or _canonical_visible_text(allowed) in folded
        for allowed in public_text
    )


def _canonical_visible_text(value: str) -> str:
    """Normalize harmless source/entity and legacy pack encoding differences."""

    visible = html.unescape(value).strip().strip("\"'\u201c\u201d\u2018\u2019").strip()
    with suppress(UnicodeEncodeError, UnicodeDecodeError):
        # Some older Build Preparation projections were UTF-8 decoded as
        # Windows-1252 (for example ``â€“`` instead of an en dash). Repair that
        # representation for comparison only; generated bytes remain intact.
        visible = visible.encode("cp1252").decode("utf-8")
    # JSX and CSS routinely wrap long approved copy across source lines. The
    # validator compares visible text, so source whitespace must not change
    # the meaning of a grounded sentence.
    return " ".join(unicodedata.normalize("NFKC", visible).casefold().split())


_INTERACTION_ATTR_RE = re.compile(
    r'data-interaction-id\s*=\s*(?P<quote>["\'])(?P<id>[^"\']+)(?P=quote)'
)
_STATIC_ARIA_LABEL_RE = re.compile(r'aria-label\s*=\s*(?P<quote>["\'])(?P<value>[^"\']*)(?P=quote)')
_HEADING_RE = re.compile(r"(<h[1-6]\b[^>]*>)([^<]*)(</h[1-6]>)", re.DOTALL)
_FUNCTION_RE = re.compile(r"function\s+[A-Za-z_$][\w$]*\s*\((?P<params>[\s\S]{0,900}?)\)")
_REPEATED_INSTANCE_PARAM_RE = re.compile(
    r"\b(?P<name>[A-Za-z_$][\w$]*(?:index|idx|position|order))\b", re.IGNORECASE
)


def normalize_generated_route_contract(
    repo_dir: Path,
    *,
    plan: Any,
    site_contract: dict[str, Any],
) -> bool:
    """Apply deterministic, contract-only repairs to model-authored route JSX.

    The model owns composition, but interaction IDs and approved section
    headings are executable contract surfaces. Duplicate IDs can make
    Playwright select a hidden navigation copy, while a one-word heading can
    be omitted by prose-only source coverage checks. Keep the creative source
    intact and normalize only those host-owned invariants from the admitted
    plan and public content.
    """

    interactions_by_route: dict[str, dict[str, str]] = {}
    escape_interactions_by_route: dict[str, set[str]] = {}
    for interaction in getattr(plan, "interactions", []) or []:
        interaction_id = str(getattr(interaction, "interaction_id", "")).strip()
        route_id = str(getattr(interaction, "route_id", "")).strip()
        if interaction_id and route_id:
            interactions_by_route.setdefault(route_id, {})[interaction_id] = str(
                getattr(interaction, "accessible_name", "") or ""
            ).strip()
            keyboard_behavior = str(getattr(interaction, "keyboard_behavior", "") or "")
            if "escape" in keyboard_behavior.casefold() and any(
                token in keyboard_behavior.casefold() for token in ("close", "collapse", "hide")
            ):
                escape_interactions_by_route.setdefault(route_id, set()).add(interaction_id)

    content_by_route = {
        str(item.get("route_id", "")): item
        for item in site_contract.get("public_content", [])
        if isinstance(item, dict)
    }
    changed = False
    for route in site_contract.get("routes", []):
        if not isinstance(route, dict):
            continue
        route_id = str(route.get("route_id", "")).strip()
        if not route_id:
            continue
        storage_key = str(route.get("storage_key", route_id)).replace("\\", "/").strip("/")
        storage_key = storage_key.removeprefix("routes/")
        route_root = repo_dir / "src" / "routes" / storage_key
        if not route_root.is_dir():
            continue
        files = sorted(route_root.rglob("*.tsx"))
        changed |= _normalize_route_interactions(
            files,
            interactions_by_route.get(route_id, {}),
            escape_interactions_by_route.get(route_id, set()),
        )
        changed |= _normalize_route_headings(
            files,
            content_by_route.get(route_id, {}).get("sections", []),
        )
    return changed


def _normalize_route_interactions(
    files: list[Path], names_by_id: dict[str, str], escape_interaction_ids: set[str]
) -> bool:
    if not names_by_id or not files:
        return False
    contents = {path: path.read_text(encoding="utf-8") for path in files}
    changed = False
    for interaction_id, accessible_name in names_by_id.items():
        occurrences: list[tuple[Path, re.Match[str], int]] = []
        for path, text in contents.items():
            for match in _INTERACTION_ATTR_RE.finditer(text):
                if match.group("id") == interaction_id:
                    prefix = text[: match.start()]
                    nav_depth = len(re.findall(r"<nav\b", prefix, re.IGNORECASE)) - len(
                        re.findall(r"</nav\s*>", prefix, re.IGNORECASE)
                    )
                    occurrences.append((path, match, max(nav_depth, 0)))
        if not occurrences:
            continue
        selected = min(occurrences, key=lambda item: (item[2] > 0, str(item[0]), item[1].start()))
        for path, match, _ in sorted(occurrences, key=lambda item: item[1].start(), reverse=True):
            if path == selected[0] and match.start() == selected[1].start():
                continue
            text = contents[path]
            contents[path] = text[: match.start()] + text[match.end() :]
            changed = True
        if accessible_name:
            path = selected[0]
            text = contents[path]
            matches = [
                item
                for item in _INTERACTION_ATTR_RE.finditer(text)
                if item.group("id") == interaction_id
            ]
            selected_match = matches[0] if matches else None
            if selected_match is not None:
                tag_start = text.rfind("<", 0, selected_match.start())
                tag_end = text.find(">", selected_match.end())
                if tag_start >= 0 and tag_end >= selected_match.end():
                    tag = text[tag_start : tag_end + 1]
                    escaped = html.escape(accessible_name, quote=True)
                    aria = _STATIC_ARIA_LABEL_RE.search(tag)
                    if aria is not None:
                        replacement = f'aria-label="{escaped}"'
                        updated_tag = tag[: aria.start()] + replacement + tag[aria.end() :]
                    else:
                        marker_start = tag.find("data-interaction-id")
                        updated_tag = (
                            tag[:marker_start] + f'aria-label="{escaped}" ' + tag[marker_start:]
                        )
                    if updated_tag != tag:
                        contents[path] = text[:tag_start] + updated_tag + text[tag_end + 1 :]
                        changed = True
        changed |= _normalize_repeated_interaction_marker(contents, interaction_id)
    changed |= _normalize_escape_interactions(contents, escape_interaction_ids)
    for path, text in contents.items():
        if text != path.read_text(encoding="utf-8"):
            path.write_text(text, encoding="utf-8")
    return changed


def _normalize_repeated_interaction_marker(contents: dict[Path, str], interaction_id: str) -> bool:
    """Keep one trace marker when a reusable component renders many controls.

    Generated React often puts one literal marker inside a component that is
    rendered by an indexed collection. A literal then expands to duplicate DOM
    markers. When the component exposes a stable index-like prop, make the
    first instance the admitted marker and leave the other controls usable by
    their contract selector. The comment preserves a source-level trace to
    the admitted interaction without inventing input-specific content.
    """

    for path, text in list(contents.items()):
        match = _INTERACTION_ATTR_RE.search(text)
        if match is None or match.group("id") != interaction_id:
            continue
        function_matches = list(_FUNCTION_RE.finditer(text[: match.start()]))
        if not function_matches:
            continue
        params = function_matches[-1].group("params")
        parameter = _REPEATED_INSTANCE_PARAM_RE.search(params)
        if parameter is None:
            continue
        tag_start = text.rfind("<", 0, match.start())
        if tag_start < 0:
            continue
        name = parameter.group("name")
        dynamic = f'data-interaction-id={{{name} === 0 ? "{interaction_id}" : undefined}}'
        comment = f"{{/* OryxenAI interaction marker: {interaction_id} */}}\n"
        updated = (
            text[:tag_start]
            + comment
            + text[tag_start : match.start()]
            + dynamic
            + text[match.end() :]
        )
        if updated != text:
            contents[path] = updated
            return True
    return False


def _normalize_escape_interactions(contents: dict[Path, str], interaction_ids: set[str]) -> bool:
    """Add the admitted Escape-close behavior to a stateful trigger."""

    changed = False
    for interaction_id in interaction_ids:
        for path, original_text in list(contents.items()):
            text, malformed_changed = _repair_malformed_escape_injection(
                original_text, interaction_id
            )
            if malformed_changed:
                contents[path] = text
                changed = True
            marker_match = _INTERACTION_ATTR_RE.search(text)
            if marker_match is None or marker_match.group("id") != interaction_id:
                continue
            tag_start = text.rfind("<", 0, marker_match.start())
            tag_end = _jsx_opening_tag_end(text, marker_match.end())
            if tag_start < 0 or tag_end < 0:
                continue
            tag = text[tag_start : tag_end + 1]
            if "onKeyDown" in tag:
                continue
            expanded = re.search(r"aria-expanded\s*=\s*\{\s*(?P<state>[A-Za-z_$][\w$]*)\s*\}", tag)
            if expanded is None:
                continue
            state_name = expanded.group("state")
            setter_match = list(
                re.finditer(
                    rf"const\s*\[\s*{re.escape(state_name)}\s*,\s*(?P<setter>[A-Za-z_$][\w$]*)\s*\]"
                    r"\s*=\s*useState\b",
                    text[:tag_start],
                )
            )
            if not setter_match:
                continue
            setter = setter_match[-1].group("setter")
            handler = (
                " onKeyDown={(event) => {"
                ' if (event.key === "Escape") {'
                " event.preventDefault();"
                f" {setter}(false);"
                " event.currentTarget.focus();"
                " }"
                " }}"
            )
            on_click = re.search(r"\bonClick\s*=", text[marker_match.end() : tag_end])
            insertion_point = (
                marker_match.end() + on_click.start() if on_click is not None else tag_end
            )
            updated = text[:insertion_point] + handler + text[insertion_point:]
            if updated != text:
                contents[path] = updated
                changed = True
            break
    return changed


def _repair_malformed_escape_injection(text: str, interaction_id: str) -> tuple[str, bool]:
    """Recover a checkpoint written by the pre-brace-aware host repair."""

    marker = f'data-interaction-id="{interaction_id}"'
    marker_start = text.find(marker)
    if marker_start < 0:
        return text, False
    tag_start = text.rfind("<", 0, marker_start)
    scan_start = text.find("onClick=", marker_start)
    if scan_start < 0:
        scan_start = marker_start
    line_end = text.find("\n", scan_start)
    if tag_start < 0:
        return text, False
    if line_end < 0:
        line_end = len(text)
    if line_end <= tag_start:
        return text, False
    prefix = text[tag_start:line_end]
    malformed = re.search(
        r"onClick=\{\(\)\s*=\s*onKeyDown=\{.*?\}\}>\s*(?P<original>[^\n{}]+)\}",
        prefix,
    )
    if malformed is None:
        return text, False
    original = malformed.group("original").strip()
    corrected_tag = (
        prefix[: malformed.start()] + f"onClick={{() => {original}}}" + prefix[malformed.end() :]
    )
    return text[:tag_start] + corrected_tag + text[line_end:], True


def _jsx_opening_tag_end(text: str, start: int) -> int:
    """Find a JSX opening-tag boundary without stopping inside ``{...}``."""

    brace_depth = 0
    quote = ""
    escaped = False
    for index in range(start, len(text)):
        character = text[index]
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = ""
            continue
        if character in {"'", '"', "`"}:
            quote = character
        elif character == "{":
            brace_depth += 1
        elif character == "}" and brace_depth:
            brace_depth -= 1
        elif character == ">" and brace_depth == 0:
            return index
    return -1


def _normalize_route_headings(files: list[Path], sections: Any) -> bool:
    changed = False
    for section in sections if isinstance(sections, list) else []:
        if not isinstance(section, dict):
            continue
        section_id = str(section.get("section_id", "")).strip()
        content = section.get("content", {})
        heading = str(content.get("heading", "")).strip() if isinstance(content, dict) else ""
        if not section_id or not heading:
            continue
        for path in files:
            text = path.read_text(encoding="utf-8")
            anchor = f'data-content-id="{section_id}"'
            anchor_start = text.find(anchor)
            if anchor_start < 0:
                continue
            next_anchor = text.find('data-content-id="', anchor_start + len(anchor))
            section_end = next_anchor if next_anchor >= 0 else len(text)
            segment = text[anchor_start:section_end]
            heading_texts = {
                _canonical_visible_text(match.group(2)) for match in _HEADING_RE.finditer(segment)
            }
            if _canonical_visible_text(heading) in heading_texts:
                continue
            match = _HEADING_RE.search(segment)
            escaped = html.escape(heading, quote=False)
            if match is not None:
                replacement = f"{match.group(1)}{escaped}{match.group(3)}"
                segment = segment[: match.start()] + replacement + segment[match.end() :]
            else:
                tag_end = text.find(">", anchor_start + len(anchor))
                if tag_end < 0 or tag_end >= section_end:
                    continue
                insertion = f'\n      <h2 data-approved-heading="{html.escape(section_id, quote=True)}">{escaped}</h2>'
                text = text[: tag_end + 1] + insertion + text[tag_end + 1 :]
                path.write_text(text, encoding="utf-8")
                changed = True
                continue
            text = text[:anchor_start] + segment + text[section_end:]
            path.write_text(text, encoding="utf-8")
            changed = True
    return changed


def _validate_imports(text: str, path: str, allowed_packages: set[str]) -> None:
    for imported in _IMPORT_RE.findall(text):
        if imported.startswith((".", "/", "@/")):
            continue
        if imported.startswith("node:") and path == "vite.config.ts":
            continue
        package = (
            imported
            if imported.startswith("@") and len(imported.split("/")) < 2
            else "/".join(imported.split("/")[:2])
            if imported.startswith("@")
            else imported.split("/", 1)[0]
        )
        if package not in allowed_packages:
            raise SourceValidationError(
                "SOURCE_UNDECLARED_IMPORT",
                f"The import '{package}' is not in the trusted dependency ledger.",
                file=path,
            )


def _diagnostic(code: str, message: str, work_unit_id: str, file: str) -> SourceDiagnostic:
    import hashlib

    fingerprint = hashlib.sha256(f"{code}:{file}:{message}".encode()).hexdigest()[:24]
    return SourceDiagnostic(
        diagnostic_id=f"diagnostic-{fingerprint}",
        group="source_contract",
        code=code,
        phase="source_generation",
        work_unit_id=work_unit_id,
        normalized_message=message,
        file=file,
        fingerprint=fingerprint,
    )
