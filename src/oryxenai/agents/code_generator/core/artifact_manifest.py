"""Deterministic production-artifact manifests and candidate archives."""

from __future__ import annotations

import hashlib
import io
import mimetypes
import posixpath
import re
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import (
    BuildManifest,
    BuildManifestEntry,
)


class ArtifactValidationError(ValueError):
    def __init__(self, code: str, message: str, *, path: str = "") -> None:
        self.code = code
        self.message = message
        self.path = path
        super().__init__(message)


_HTML_REFERENCE_RE = re.compile(r"(?:src|href)\s*=\s*[\"']([^\"'#?]+)", re.IGNORECASE)
_CSS_REFERENCE_RE = re.compile(r"url\(\s*[\"']?([^\"')?#]+)", re.IGNORECASE)
_MODULE_REFERENCE_RE = re.compile(
    r"(?:\bimport\s*\(\s*|\bimport\s+|\bexport\s+[^;]*?\s+from\s*)[\"']([^\"'#?]+)",
    re.IGNORECASE,
)
_REMOTE_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.IGNORECASE)


def _safe_relative(path: str) -> str:
    normalized = path.replace("\\", "/").lstrip("/")
    candidate = PurePosixPath(normalized)
    if (
        not normalized
        or candidate.is_absolute()
        or ".." in candidate.parts
        or any(part.startswith(".") for part in candidate.parts)
    ):
        raise ArtifactValidationError(
            "BUILD_ARTIFACT_PATH_UNSAFE", "The build contains an unsafe path.", path=path
        )
    return candidate.as_posix()


def _references(data: bytes, path: str) -> list[str]:
    if not path.endswith((".html", ".css", ".js", ".mjs", ".css")):
        return []
    text = data.decode("utf-8", errors="replace")
    values: list[str] = []
    references: list[str] = []
    if path.endswith((".html", ".htm")):
        references.extend(_HTML_REFERENCE_RE.findall(text))
    if path.endswith(".css"):
        references.extend(_CSS_REFERENCE_RE.findall(text))
    if path.endswith((".js", ".mjs")):
        references.extend(_MODULE_REFERENCE_RE.findall(text))
    for value in references:
        if not value or value.startswith(("data:", "#")) or _REMOTE_RE.match(value):
            if value and _REMOTE_RE.match(value):
                raise ArtifactValidationError(
                    "BUILD_REMOTE_REFERENCE",
                    "The production artifact contains a remote reference.",
                    path=path,
                )
            continue
        values.append(value)
    return sorted(set(values))


def build_manifest(
    dist_dir: Path,
    *,
    candidate_identity_hash: str,
    max_total_bytes: int,
    reject_source_maps: bool = True,
) -> BuildManifest:
    if not dist_dir.is_dir():
        raise ArtifactValidationError(
            "BUILD_DIST_MISSING", "The production dist directory is unavailable."
        )
    files = [path for path in sorted(dist_dir.rglob("*")) if path.is_file()]
    if not files or not (dist_dir / "index.html").is_file():
        raise ArtifactValidationError(
            "BUILD_ENTRY_MISSING", "The production artifact has no index.html entry."
        )
    entries: list[BuildManifestEntry] = []
    total = 0
    known: set[str] = set()
    for path in files:
        relative = _safe_relative(path.relative_to(dist_dir).as_posix())
        if reject_source_maps and relative.endswith(".map"):
            raise ArtifactValidationError(
                "BUILD_SOURCE_MAP_FORBIDDEN",
                "Source maps are not part of the promoted artifact.",
                path=relative,
            )
        data = path.read_bytes()
        total += len(data)
        if total > max_total_bytes:
            raise ArtifactValidationError(
                "BUILD_ARTIFACT_TOO_LARGE",
                "The production artifact exceeds its configured size limit.",
                path=relative,
            )
        if relative in known:
            raise ArtifactValidationError(
                "BUILD_ARTIFACT_DUPLICATE",
                "The production artifact contains a duplicate path.",
                path=relative,
            )
        known.add(relative)
        references = _references(data, relative)
        entries.append(
            BuildManifestEntry(
                path=relative,
                media_type=mimetypes.guess_type(relative)[0] or "application/octet-stream",
                size_bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
                references=references,
            )
        )
    _verify_references(entries, known)
    return BuildManifest(
        candidate_identity_hash=candidate_identity_hash,
        entry_paths=["index.html"],
        entries=entries,
        total_bytes=total,
    )


def _verify_references(entries: list[BuildManifestEntry], known: set[str]) -> None:
    for entry in entries:
        base = PurePosixPath(entry.path).parent
        for reference in entry.references:
            normalized = reference.lstrip("/")
            if reference.startswith("/"):
                target = _safe_relative(normalized)
            else:
                target_value = posixpath.normpath((base / normalized).as_posix())
                if target_value == ".." or target_value.startswith("../"):
                    raise ArtifactValidationError(
                        "BUILD_ARTIFACT_PATH_UNSAFE",
                        "A production-artifact reference escapes the build root.",
                        path=f"{entry.path} -> {reference}",
                    )
                target = _safe_relative(target_value)
            if target not in known and target != "index.html":
                raise ArtifactValidationError(
                    "BUILD_REFERENCE_MISSING",
                    "The production artifact references a missing local file.",
                    path=f"{entry.path} -> {reference}",
                )


def candidate_zip(dist_dir: Path, manifest: BuildManifest) -> bytes:
    """Create a reproducible archive containing only the promoted dist tree."""

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for entry in manifest.entries:
            path = dist_dir / entry.path
            info = zipfile.ZipInfo(entry.path, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    return output.getvalue()


def manifest_payload(manifest: BuildManifest) -> dict[str, Any]:
    return manifest.model_dump(mode="json")
