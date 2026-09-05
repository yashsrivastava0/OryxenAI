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
from oryxenai.agents.code_generator.core.source_lexing import (
    static_jsx_attribute_values,
    strip_source_comments,
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
_CSS_DECLARATION_RE = re.compile(r"(?P<property>(?:--)?[A-Za-z][\w-]*)\s*:\s*(?P<value>[^;{}]+)")
_CSS_NUMBER_WORD = (
    r"zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
    r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand"
)
_CSS_SPELLED_LENGTH_RE = re.compile(
    rf"(?<![\w-])(?P<length>(?:{_CSS_NUMBER_WORD})(?:-?(?:{_CSS_NUMBER_WORD}))*"
    r"(?:vmin|vmax|dvh|dvw|svh|svw|lvh|lvw|rem|px|em|ex|ch|vh|vw|cm|mm|in|pt|pc))\b",
    re.IGNORECASE,
)
_CSS_CUSTOM_PROPERTY_DEFINITION_RE = re.compile(r"(?<![\w-])(?P<name>--[A-Za-z_][\w-]*)\s*:")
_CSS_CUSTOM_PROPERTY_USE_RE = re.compile(r"\bvar\(\s*(?P<name>--[A-Za-z_][\w-]*)")
_INLINE_CUSTOM_PROPERTY_DEFINITION_RE = re.compile(
    r"(?:[\"'](?P<object>--[A-Za-z_][\w-]*)[\"']\s*:|"
    r"\.setProperty\(\s*[\"'](?P<setter>--[A-Za-z_][\w-]*)[\"'])"
)
_ROUTE_FONT_FACE_RE = re.compile(r"@font-face\b", re.IGNORECASE)


def _approved_urls(public_text: set[str]) -> set[str]:
    """Extract the external URLs that appear verbatim in approved content."""

    urls: set[str] = set()
    for entry in public_text:
        for match in _APPROVED_URL_RE.finditer(entry or ""):
            urls.add(match.group(0).rstrip(".,;:"))
    return urls


def _jsx_opening_tag_contains_literal(source: str, literal: str) -> bool:
    """Match a literal JSX attribute on an opening tag, never in a comment."""

    attribute = re.fullmatch(
        r"\s*([A-Za-z_:][\w:.-]*)\s*=\s*([\"'])(.*?)\2\s*",
        literal,
        flags=re.DOTALL,
    )
    if attribute is None:
        return literal in source
    name, _, value = attribute.groups()
    return bool(
        re.search(
            rf"<[A-Za-z][^<>]*\b{re.escape(name)}\s*=\s*([\"'])"
            rf"{re.escape(value)}\1[^<>]*>",
            source,
            flags=re.DOTALL,
        )
    )


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
        if path.endswith(".css"):
            _validate_css_value_policy(change.complete_utf8_content, path)
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
    source_paths: list[str] | None = None,
) -> list[SourceDiagnostic]:
    scoped_paths = (
        {item.replace("\\", "/").strip("/") for item in source_paths}
        if source_paths is not None
        else None
    )
    total = 0
    diagnostics: list[SourceDiagnostic] = []
    for path in sorted(repo_dir.rglob("*")):
        if not path.is_file() or any(part in {"node_modules", "dist"} for part in path.parts):
            continue
        relative = path.relative_to(repo_dir).as_posix()
        if scoped_paths is not None and relative not in scoped_paths:
            continue
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
            if path.suffix.lower() == ".css":
                _validate_css_value_policy(text, relative)
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
    diagnostics.extend(
        _validate_route_css_contract(
            repo_dir,
            source_paths=scoped_paths,
            work_unit_id=work_unit_id,
        )
    )
    return diagnostics


def _validate_route_css_contract(
    repo_dir: Path,
    *,
    source_paths: set[str] | None,
    work_unit_id: str,
) -> list[SourceDiagnostic]:
    """Reject route CSS that bypasses compiler-owned tokens or font bindings.

    Definitions are collected from the complete source tree even when a
    progressive work unit scopes validation to its own files. This lets a
    route batch use trusted generated tokens and literal runtime custom
    properties while still rejecting a misspelled or invented token in the
    emitted route CSS.
    """

    source_root = repo_dir / "src"
    if not source_root.is_dir():
        return []
    definitions: set[str] = set()
    route_css: dict[str, str] = {}
    for path in sorted(source_root.rglob("*")):
        if not path.is_file() or path.suffix.casefold() not in {".css", ".ts", ".tsx"}:
            continue
        if any(part in {"node_modules", "dist"} for part in path.parts):
            continue
        relative = path.relative_to(repo_dir).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if path.suffix.casefold() == ".css":
            clean = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
            definitions.update(
                match.group("name") for match in _CSS_CUSTOM_PROPERTY_DEFINITION_RE.finditer(clean)
            )
            if relative.startswith("src/routes/") and (
                source_paths is None or relative in source_paths
            ):
                route_css[relative] = clean
            continue
        clean = strip_source_comments(text)
        for match in _INLINE_CUSTOM_PROPERTY_DEFINITION_RE.finditer(clean):
            definitions.add(match.group("object") or match.group("setter"))

    diagnostics: list[SourceDiagnostic] = []
    for relative, css in sorted(route_css.items()):
        if _ROUTE_FONT_FACE_RE.search(css):
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_FONT_FACE_FORBIDDEN",
                    "Generated route CSS cannot declare @font-face; use the compiler-owned "
                    "local font faces emitted in src/design/generated-tokens.css.",
                    work_unit_id,
                    relative,
                )
            )
        used = {match.group("name") for match in _CSS_CUSTOM_PROPERTY_USE_RE.finditer(css)}
        for name in sorted(used - definitions):
            diagnostics.append(
                _diagnostic(
                    "SOURCE_CSS_CUSTOM_PROPERTY_UNBOUND",
                    f"Generated route CSS references undefined custom property {name}; "
                    "use an exact compiler-emitted token or define a literal runtime "
                    "custom property on the owning source element.",
                    work_unit_id,
                    relative,
                )
            )
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
    content_ids_by_section: dict[str, list[str]] | None = None,
    section_selectors_by_section: dict[str, str] | None = None,
    interaction_ids: list[str] | None = None,
    interaction_markers: dict[str, str] | None = None,
    interaction_contracts: dict[str, dict[str, Any]] | None = None,
    image_assets_by_slot: dict[str, dict[str, Any]] | None = None,
    distinctive_moves: list[dict[str, Any]] | None = None,
    motion_beats: list[dict[str, Any]] | None = None,
    h1_owner_section_id: str = "",
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

    contract_paths = [
        value
        for value in normalized_paths
        if Path(value).suffix.lower() in {".tsx", ".ts", ".css"} and "*" not in value
    ]
    contract_sources: dict[str, str] = {}
    for relative in contract_paths:
        try:
            contract_sources[relative] = (repo_dir / relative).resolve().read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    for relative, source in contract_sources.items():
        if not relative.endswith(".css"):
            continue
        try:
            _validate_css_value_policy(source, relative)
        except SourceValidationError as exc:
            diagnostics.append(_diagnostic(exc.code, exc.message, work_unit_id, relative))
    sources = {path: contract_sources.get(path, "") for path in source_paths}

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
        section_selector = (section_selectors_by_section or {}).get(section_id, f"#{section_id}")
        selector_matches = _literal_selector_positions(owner_text, section_selector)
        if selector_matches is not None and len(selector_matches) != 1:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_DOM_ID_INVALID",
                    "The section owner must implement its exact blueprint section selector "
                    f"once: {section_selector}",
                    work_unit_id,
                    owner_relative,
                )
            )
        for content_id in (content_ids_by_section or {}).get(section_id, []):
            if not re.search(
                rf"\bcontentValue\s*\(\s*[\"']{re.escape(content_id)}[\"']\s*\)",
                owner_text,
            ):
                message = (
                    f"The section owner must render its approved content key through "
                    f"a direct contentValue call: {content_id}"
                )
                near_miss = _near_miss_content_key(content_id, owner_text)
                if near_miss is not None:
                    # Live-discovered 2026-09-05: the model transcribed an
                    # opaque hash-like suffix with a one-character typo
                    # ("section-label-7cac7d3b" -> "section-label-7cacd3b")
                    # and repeated the exact same typo across every repair
                    # round, exhausting the budget on what was really a
                    # copy error, not a missing binding. Naming the actual
                    # near-miss call gives the repair model something
                    # concrete to correct instead of regenerating blind.
                    message += (
                        f'. A similarly-named call was found instead: contentValue("{near_miss}"). '
                        "Check for a transcription mistake in the literal suffix and correct it to "
                        "the exact required key above; do not invent a different one."
                    )
                diagnostics.append(
                    _diagnostic(
                        "SOURCE_ROUTE_BATCH_CONTENT_KEY_MISSING",
                        message,
                        work_unit_id,
                        owner_relative,
                    )
                )
    combined_source = "\n".join(contract_sources.values())
    h1_count = len(re.findall(r"<h1\b", combined_source, flags=re.IGNORECASE))
    if h1_owner_section_id in assigned:
        owner_paths = owners.get(h1_owner_section_id, [])
        owner_source = sources.get(owner_paths[0], "") if len(owner_paths) == 1 else ""
        owner_h1_count = len(re.findall(r"<h1\b", owner_source, flags=re.IGNORECASE))
        if h1_count != 1 or owner_h1_count != 1:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_H1_OWNERSHIP_INVALID",
                    "The canonical heading-owner section must render the route's single h1: "
                    f"{h1_owner_section_id}; observed batch h1 count={h1_count}, "
                    f"owner h1 count={owner_h1_count}.",
                    work_unit_id,
                    owner_paths[0] if len(owner_paths) == 1 else anchor_relative,
                )
            )
    elif h1_owner_section_id and h1_count:
        diagnostics.append(
            _diagnostic(
                "SOURCE_ROUTE_BATCH_H1_OWNERSHIP_INVALID",
                "Only the canonical heading-owner section may render an h1: "
                f"{h1_owner_section_id}; this batch renders {h1_count}.",
                work_unit_id,
                anchor_relative,
            )
        )
    for marker in source_markers or []:
        if marker and marker not in combined_source:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_MARKER_MISSING",
                    f"The route-batch anchor is missing its assigned source marker: {marker}",
                    work_unit_id,
                    anchor_relative,
                )
            )
    for interaction_id in interaction_ids or []:
        interaction = (interaction_contracts or {}).get(interaction_id, {})
        target_selector = str(interaction.get("target_selector", ""))
        interaction_relative = anchor_relative
        interaction_owner_matched = False
        for section_id, selector in (section_selectors_by_section or {}).items():
            if not selector or selector not in target_selector:
                continue
            owner_paths = owners.get(section_id, [])
            if len(owner_paths) == 1:
                interaction_relative = owner_paths[0]
                interaction_owner_matched = True
                break
        interaction_sources = (
            {interaction_relative: sources.get(interaction_relative, "")}
            if interaction_owner_matched
            else sources
        )
        located_tags = [
            (relative, tag)
            for relative, source in interaction_sources.items()
            for tag in re.findall(
                rf"<[^>]*\bdata-interaction-id\s*=\s*[\"']"
                rf"{re.escape(interaction_id)}[\"'][^>]*>",
                source,
                re.DOTALL,
            )
        ]
        tags = [tag for _, tag in located_tags]
        diagnostic_relative = located_tags[0][0] if located_tags else interaction_relative
        if not tags:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_INTERACTION_MISSING",
                    f"The section batch is missing its assigned literal interaction marker: "
                    f"{interaction_id}",
                    work_unit_id,
                    diagnostic_relative,
                )
            )
            continue
        literal_marker = (interaction_markers or {}).get(interaction_id, "")
        if literal_marker and not any(literal_marker in tag for tag in tags):
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_INTERACTION_MARKER_MISSING",
                    "The executable interaction target must carry its exact blueprint marker "
                    f"on the same JSX tag: {literal_marker}",
                    work_unit_id,
                    diagnostic_relative,
                )
            )
        if not any(re.search(r"\b(?:href|onClick|onKeyDown|onChange)\s*=", tag) for tag in tags):
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_INTERACTION_OUTCOME_MISSING",
                    f"The assigned interaction needs a JSX handler or navigation outcome: "
                    f"{interaction_id}",
                    work_unit_id,
                    diagnostic_relative,
                )
            )
        state_attribute = str(interaction.get("expected_state_attribute", ""))
        state_value = str(interaction.get("expected_state_value", ""))
        expected_navigation = str(interaction.get("expected_navigation", ""))
        state_assignments = (
            [
                match.group("value")
                for tag in tags
                for match in re.finditer(
                    rf"\b{re.escape(state_attribute)}\s*=\s*"
                    r"(?P<value>\{[^{}]+\}|[\"'][^\"']*[\"'])",
                    tag,
                )
            ]
            if state_attribute
            else []
        )
        if state_attribute and not state_assignments:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_INTERACTION_STATE_MISSING",
                    f"The assigned interaction target must expose its exact state attribute: "
                    f"{interaction_id} -> {state_attribute}={state_value}",
                    work_unit_id,
                    diagnostic_relative,
                )
            )
        elif state_value and not _interaction_state_value_matches(state_assignments, state_value):
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_INTERACTION_STATE_MISSING",
                    f"The assigned interaction must implement its expected state value: "
                    f"{interaction_id} -> {state_attribute}={state_value}",
                    work_unit_id,
                    diagnostic_relative,
                )
            )
        trigger = str(interaction.get("trigger", ""))
        navigation_casefolded = expected_navigation.casefold()
        no_navigation = (
            "no navigation" in navigation_casefolded or "remain on" in navigation_casefolded
        )
        navigation_literals = [
            item.rstrip(".,;)")
            for item in re.findall(
                r"https?://[^\s,;]+|(?:mailto|tel):[^\s,;]+|"
                r"#[A-Za-z_][\w-]*|/(?!/)[A-Za-z0-9][^\s,;]*",
                expected_navigation,
            )
        ]
        literal_navigation = expected_navigation.startswith(
            ("#", "/", "http://", "https://", "mailto:", "tel:")
        )
        navigation_invalid = False
        if no_navigation:
            navigation_invalid = any(re.search(r"\bhref\s*=", tag) for tag in tags)
        elif expected_navigation and (trigger in {"navigation", "download"} or literal_navigation):
            expected_values = navigation_literals or [expected_navigation]
            navigation_invalid = not any(
                expected in tag for expected in expected_values for tag in tags
            )
        if navigation_invalid:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_INTERACTION_NAVIGATION_MISSING",
                    f"The assigned interaction target must use its exact navigation outcome: "
                    f"{interaction_id} -> {expected_navigation}",
                    work_unit_id,
                    diagnostic_relative,
                )
            )

    for slot_id, asset in (image_assets_by_slot or {}).items():
        missing: list[str] = []
        resource_matches = list(
            re.finditer(
                rf"\bresourceId\s*=\s*([\"']){re.escape(slot_id)}\1",
                combined_source,
            )
        )
        local_image_tags: list[str] = []
        for match in resource_matches:
            start = combined_source.rfind("<LocalImage", 0, match.start())
            end = combined_source.find("/>", match.end())
            if start >= 0 and end >= 0 and ">" not in combined_source[start : match.start()]:
                local_image_tags.append(combined_source[start : end + 2])
        if not local_image_tags:
            missing.append(f'resourceId="{slot_id}"')
        if isinstance(asset, dict):
            element_marker = str(asset.get("element_marker", ""))
            if element_marker and not _jsx_opening_tag_contains_literal(
                combined_source, element_marker
            ):
                missing.append(element_marker)
            expected_props = {
                "sizes": str(asset.get("sizes", "100vw")),
                "loading": str(asset.get("loading", "lazy")),
                "fit": str(asset.get("fit", "cover")),
                "focalPosition": str(asset.get("focal_position", "center")),
            }
            for tag in local_image_tags:
                if re.search(r"\bsources\s*=", tag):
                    missing.append("sources prop must be omitted")
                for prop, prop_value in expected_props.items():
                    if not re.search(
                        rf"\b{re.escape(prop)}\s*=\s*([\"']){re.escape(prop_value)}\1",
                        tag,
                    ):
                        missing.append(f'{prop}="{prop_value}"')
                alt_policy = str(asset.get("alt_policy", "contextual_description"))
                if alt_policy == "decorative":
                    if not re.search(r"\balt\s*=\s*([\"'])\1", tag):
                        missing.append('alt=""')
                elif not re.search(r"\balt\s*=", tag) or re.search(r"\balt\s*=\s*([\"'])\1", tag):
                    missing.append("non-empty alt")
        if missing:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_IMAGE_BINDING_INVALID",
                    "The planned LocalImage binding must defer immutable sources to the "
                    f"trusted manifest and use exact presentation props for {slot_id}; "
                    "missing or mismatched: " + ", ".join(dict.fromkeys(missing[:6])),
                    work_unit_id,
                    anchor_relative,
                )
            )

    for move in distinctive_moves or []:
        move_id = str(move.get("move_id", ""))
        section_id = str(move.get("section_id", ""))
        owner_paths = owners.get(section_id, [])
        owner_relative = owner_paths[0] if len(owner_paths) == 1 else anchor_relative
        owner_source = sources.get(owner_relative, "")
        style_candidate = Path(owner_relative).with_suffix(".css").as_posix()
        style_relative = style_candidate if style_candidate in contract_sources else owner_relative
        style_source = (
            contract_sources.get(style_relative, "")
            if style_relative != owner_relative
            else owner_source
        )
        move_missing: list[str] = []
        runtime_marker = str(move.get("runtime_marker", ""))
        if runtime_marker and runtime_marker not in owner_source:
            move_missing.append(f"runtime marker {runtime_marker}")
        source_selector = str(move.get("source_selector", ""))
        declarations = _exact_selector_declarations(
            style_source,
            source_selector,
            runtime_marker=runtime_marker,
        )
        missing_properties = [
            str(item)
            for item in move.get("required_css_properties", [])
            if str(item).casefold() not in declarations
        ]
        if not declarations:
            move_missing.append(f"exact CSS selector {source_selector}")
        if missing_properties:
            move_missing.append("CSS properties " + ", ".join(missing_properties))
        if move_missing:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_DISTINCTIVE_MOVE_INVALID",
                    f"The assigned distinctive move {move_id} is missing executable evidence: "
                    + "; ".join(move_missing),
                    work_unit_id,
                    style_relative if declarations or missing_properties else owner_relative,
                )
            )

    for beat in motion_beats or []:
        motion_id = str(beat.get("motion_id", ""))
        motion_missing: list[str] = []
        css_repair_needed = False
        source_repair_needed = False
        motion_section_id = str(beat.get("section_id", ""))
        motion_owner_paths = owners.get(motion_section_id, [])
        motion_source_relative = (
            motion_owner_paths[0] if len(motion_owner_paths) == 1 else anchor_relative
        )
        motion_style_candidate = Path(motion_source_relative).with_suffix(".css").as_posix()
        motion_style_relative = (
            motion_style_candidate
            if motion_style_candidate in contract_sources
            else motion_source_relative
        )
        for label, value in (
            ("target marker", beat.get("target_marker")),
            ("target selector", beat.get("target_selector")),
        ):
            literal = str(value or "")
            if literal and literal not in combined_source:
                motion_missing.append(f"{label} {literal}")
                if label == "target marker":
                    source_repair_needed = True
                else:
                    css_repair_needed = True
        for expectation in beat.get("changed_properties", []):
            if not isinstance(expectation, dict):
                continue
            for label in ("property_name", "before_value", "after_value"):
                literal = str(expectation.get(label, ""))
                if literal and literal not in combined_source:
                    motion_missing.append(f"{label} {literal}")
                    css_repair_needed = True
        if "prefers-reduced-motion" not in combined_source:
            motion_missing.append("prefers-reduced-motion final state")
            css_repair_needed = True
        if str(beat.get("trigger", "")) == "viewport" and not re.search(
            r"\bIntersectionObserver\b|\banimation-timeline\s*:\s*view\s*\(|\bview-timeline\b",
            combined_source,
        ):
            motion_missing.append("viewport trigger implementation")
            source_repair_needed = True
        opacity_starts_hidden = any(
            isinstance(expectation, dict)
            and str(expectation.get("property_name", "")).strip() == "opacity"
            and str(expectation.get("before_value", "")).strip() == "0"
            for expectation in beat.get("changed_properties", [])
        )
        if str(beat.get("trigger", "")) == "viewport" and opacity_starts_hidden:
            target_selector = str(beat.get("target_selector", "")).strip()
            target_tail = target_selector.rsplit(" ", 1)[-1]
            if not _css_rule_contains(
                combined_source,
                selector_literals=[target_selector],
                property_name="opacity",
                property_value="1",
            ):
                motion_missing.append(f"default-visible {target_selector} opacity: 1")
                css_repair_needed = True
            if not _css_rule_contains(
                combined_source,
                selector_literals=['[data-motion-ready="true"]', target_tail],
                property_name="opacity",
                property_value="0",
            ):
                motion_missing.append('guarded [data-motion-ready="true"] opacity: 0')
                css_repair_needed = True
            if not re.search(
                r"setAttribute\(\s*[\"']data-motion-ready[\"']\s*,\s*[\"']true[\"']\s*\)",
                combined_source,
            ):
                motion_missing.append('setAttribute("data-motion-ready", "true")')
                source_repair_needed = True
        if motion_missing:
            repair_paths = list(dict.fromkeys([motion_source_relative, motion_style_relative]))
            diagnostic_relative = (
                motion_style_relative if css_repair_needed else motion_source_relative
            )
            owner_hint = ""
            if css_repair_needed and source_repair_needed and len(repair_paths) > 1:
                owner_hint = " Repair both motion-owner files: " + ", ".join(repair_paths) + "."
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_BATCH_MOTION_INVALID",
                    f"The assigned motion beat {motion_id} is missing executable evidence: "
                    + ", ".join(motion_missing[:6])
                    + owner_hint,
                    work_unit_id,
                    diagnostic_relative,
                )
            )
    return diagnostics


def _selector_matches_scoped(candidate: str, expected: str) -> bool:
    """A candidate CSS selector satisfies an expected selector when it is
    that exact selector, or that exact selector nested under an ancestor
    descendant/child scope (e.g. "#hero [data-region-id=...]") -- a common,
    harmless section-scoping pattern that still targets the same rendered
    element as the bare expected selector would (confirmed live 2026-09-05:
    a model consistently, reasonably scoped distinctive-move CSS this way
    across 3 repair rounds; the prior exact-string check rejected all three
    identically, exhausting the repair budget on a false positive)."""

    normalized_candidate = " ".join(candidate.split())
    normalized_expected = " ".join(expected.split())
    return normalized_candidate == normalized_expected or normalized_candidate.endswith(
        " " + normalized_expected
    )


def _exact_selector_declarations(
    source: str,
    selector: str,
    *,
    runtime_marker: str = "",
) -> set[str]:
    if not selector.strip():
        return set()
    accepted_selectors = [selector.strip()]
    if runtime_marker.strip():
        # The marker is already required as a literal attribute on the source
        # element. Qualifying that exact selector with the same attribute does
        # not weaken section/element scope; it names the same executable node.
        accepted_selectors.append(f"{selector.strip()}[{runtime_marker.strip()}]")
    bodies: list[str] = []
    for match in re.finditer(r"(?P<selectors>[^{}]+)\{(?P<body>[^{}]*)\}", source, re.DOTALL):
        selectors = [item.strip() for item in match.group("selectors").split(",")]
        if any(
            _selector_matches_scoped(candidate, expected)
            for candidate in selectors
            for expected in accepted_selectors
        ):
            bodies.append(match.group("body"))
    return {
        match.group(1).casefold()
        for body in bodies
        for match in re.finditer(r"(?:^|;)\s*([a-z-]+)\s*:", body, re.IGNORECASE)
    }


def _css_rule_contains(
    source: str,
    *,
    selector_literals: list[str],
    property_name: str,
    property_value: str,
) -> bool:
    declaration = re.compile(
        rf"(?:^|;)\s*{re.escape(property_name)}\s*:\s*{re.escape(property_value)}\s*(?:;|$)",
        re.IGNORECASE,
    )
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", source):
        selector, body = match.groups()
        if all(literal in selector for literal in selector_literals) and declaration.search(body):
            return True
    return False


def _interaction_state_value_matches(assignments: list[str], expected: str) -> bool:
    """Interpret boolean state ranges without requiring their prose verbatim."""

    normalized = " ".join(expected.casefold().replace("/", " or ").split())
    if normalized in {"boolean", "true or false", "false or true"}:
        return any(
            assignment.startswith("{") or assignment.strip("\"'").casefold() in {"true", "false"}
            for assignment in assignments
        )
    return any(expected in assignment for assignment in assignments)


def _validate_css_value_policy(source: str, path: str) -> None:
    """Reject a narrow class of readable-but-invalid generated CSS values.

    CSS parsers and production bundlers preserve unknown declaration values,
    so a model typo such as ``max-width: fiftych`` builds successfully and is
    silently ignored by the browser. Restrict this check to spelled-out number
    words joined to CSS length units; keywords, custom properties, selectors,
    comments, and ordinary numeric lengths remain untouched.
    """

    scannable = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    for declaration in _CSS_DECLARATION_RE.finditer(scannable):
        property_name = declaration.group("property")
        if property_name.startswith("--") or property_name.casefold() == "content":
            continue
        invalid = _CSS_SPELLED_LENGTH_RE.search(declaration.group("value"))
        if invalid is None:
            continue
        raise SourceValidationError(
            "SOURCE_CSS_INVALID_LENGTH",
            f"CSS declaration {property_name!r} uses the invalid spelled-out length "
            f"{invalid.group('length')!r}; use a numeric CSS length such as 50ch or "
            "an admitted design token.",
            file=path,
        )


def validate_route_composer_contract(
    repo_dir: Path,
    relative_paths: list[str],
    *,
    section_selectors_by_section: dict[str, str],
    work_unit_id: str,
) -> list[SourceDiagnostic]:
    """Require the V4 composer to supply complete section navigation."""

    route_paths = [
        value.replace("\\", "/")
        for value in relative_paths
        if value.endswith("index.tsx") and "*" not in value
    ]
    if not route_paths or len(section_selectors_by_section) < 2:
        return []
    route_path = route_paths[0]
    try:
        source = (repo_dir / route_path).resolve().read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    missing: list[str] = []
    if not re.search(r"<nav\b", source):
        missing.append("<nav>")
    if not re.search(r"<RouteShell\b[\s\S]*?\bnavigation\s*=", source):
        missing.append("RouteShell navigation prop")
    for section_id, selector in section_selectors_by_section.items():
        if not re.fullmatch(r"#[A-Za-z_][\w-]*", selector):
            continue
        if not re.search(rf"\bhref\s*=\s*[\"']{re.escape(selector)}[\"']", source):
            missing.append(f'{section_id} href="{selector}"')
    if not missing:
        return []
    return [
        _diagnostic(
            "SOURCE_ROUTE_COMPOSER_NAVIGATION_MISSING",
            "The route composer must pass a compact navigation landmark with every "
            "approved literal section href; missing: " + ", ".join(missing),
            work_unit_id,
            route_path,
        )
    ]


def _literal_selector_positions(source: str, selector: str) -> list[int] | None:
    """Locate selectors whose JSX evidence can be proven without a CSS parser.

    The runtime verifier remains authoritative for compound selectors. This
    bounded source check handles the simple IDs, static attributes, and static
    classes emitted by the V4 planner so a batch cannot checkpoint a known
    selector mismatch.
    """

    value = selector.strip()
    id_match = re.fullmatch(r"#([A-Za-z_][\w-]*)", value)
    if id_match:
        return [
            position
            for position, attribute_value in static_jsx_attribute_values(source, "id")
            if attribute_value == id_match.group(1)
        ]
    attribute_match = re.fullmatch(
        r"\[\s*([A-Za-z_:][\w:.-]*)\s*=\s*([\"'])(.*?)\2\s*\]",
        value,
    )
    if attribute_match:
        name, _, expected = attribute_match.groups()
        return [
            position
            for position, attribute_value in static_jsx_attribute_values(source, name)
            if attribute_value == expected
        ]
    class_match = re.fullmatch(r"\.([A-Za-z_][\w-]*)", value)
    if class_match:
        expected = class_match.group(1)
        return [
            position
            for name in ("class", "className")
            for position, attribute_value in static_jsx_attribute_values(source, name)
            if expected in attribute_value.split()
        ]
    return None


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


def _jsx_literal_children(text: str) -> list[str]:
    """Return probable visible JSX text without treating TS generics as tags.

    A raw ``>...<`` regex cannot distinguish ``useRef<HTMLElement>`` from an
    opening JSX element and can consequently classify an entire hook body as
    visible portfolio copy. Require a JSX-like tag start and ignore angle
    brackets attached to an identifier, then remove balanced child
    expressions before applying the prose policy.
    """

    values: list[str] = []
    index = 0
    while index < len(text):
        start = text.find("<", index)
        if start < 0:
            break
        fragment = text.startswith(("<>", "</>"), start)
        tag = re.match(r"</?[A-Za-z][\w:.-]*(?=[\s/>])", text[start:])
        if not fragment and tag is None:
            index = start + 1
            continue
        closing = text.startswith("</", start)
        if not closing and not fragment and start > 0 and re.match(r"[\w$.]", text[start - 1]):
            index = start + 1
            continue
        end = start + 1 if fragment else _jsx_opening_tag_end(text, start)
        if end < 0:
            break
        opening = text[start : end + 1]
        if not closing and not opening[:-1].rstrip().endswith("/"):
            next_tag = text.find("<", end + 1)
            child = text[end + 1 : next_tag if next_tag >= 0 else len(text)]
            visible: list[str] = []
            brace_depth = 0
            quote = ""
            escaped = False
            for character in child:
                if brace_depth:
                    if quote:
                        if escaped:
                            escaped = False
                        elif character == "\\":
                            escaped = True
                        elif character == quote:
                            quote = ""
                    elif character in {"'", '"', "`"}:
                        quote = character
                    elif character == "{":
                        brace_depth += 1
                    elif character == "}":
                        brace_depth -= 1
                    continue
                if character == "{":
                    brace_depth = 1
                    continue
                visible.append(character)
            literal = "".join(visible)
            if literal.strip():
                values.append(literal)
        index = end + 1
    return values


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
        for value in _jsx_literal_children(text):
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
                    "Route source contains copy not present in the approved public contract: "
                    f"{clean[:160]!r}",
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


_CONTENT_KEY_HASH_SUFFIX_RE = re.compile(r"^(?P<prefix>.*-)(?P<suffix>[0-9a-f]{6,10})$")


def _near_miss_content_key(content_id: str, owner_text: str) -> str | None:
    """Find a contentValue(...) call in owner_text sharing content_id's
    prefix but not its exact opaque hash suffix -- catches the model
    transcribing a hash-like identifier with a typo rather than genuinely
    omitting the binding, so the repair diagnostic can name the actual
    mistake instead of just "missing"."""

    match = _CONTENT_KEY_HASH_SUFFIX_RE.match(content_id)
    if match is None:
        return None
    prefix = match.group("prefix")
    pattern = re.compile(
        rf"contentValue\s*\(\s*[\"']({re.escape(prefix)}[0-9a-f]{{6,10}})[\"']\s*\)"
    )
    for candidate in pattern.finditer(owner_text):
        found = candidate.group(1)
        if found != content_id:
            return found
    return None


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
