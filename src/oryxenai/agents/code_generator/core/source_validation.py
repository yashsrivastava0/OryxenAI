"""Trusted source-change and generated-repository policy validation."""

from __future__ import annotations

import html
import re
import unicodedata
from contextlib import suppress
from pathlib import Path, PurePosixPath, PureWindowsPath

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
    return unicodedata.normalize("NFKC", visible).casefold()


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
