"""Deterministic packaging, verification, storage, and local restoration."""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import zipfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, cast
from uuid import UUID, uuid4

from oryxenai.agents.build_preparation.schemas import (
    BuildPreparationSourceRef,
    MaterializationResult,
    PackageResult,
)
from oryxenai.storage.artifacts import (
    ArtifactStore,
    MemoryArtifactStore,
    create_artifact_store,
)


class PackageError(ValueError):
    """A safe, non-provider packaging failure."""

    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def _safe_segment(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return cleaned[:100] or fallback


def _safe_relative(path: str) -> str:
    normalized = path.replace("\\", "/")
    candidate = PurePosixPath(normalized)
    if (
        not normalized
        or candidate.is_absolute()
        or ".." in candidate.parts
        or any(part == "" for part in candidate.parts)
    ):
        raise PackageError(
            "BUILD_PACK_UNSAFE_PATH",
            "The build pack contains an unsafe relative path.",
            details={"path": path},
        )
    return str(candidate)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _read_tree(root: Path) -> list[tuple[str, bytes]]:
    if not root.is_dir():
        raise PackageError("BUILD_PACK_ROOT_MISSING", "The build-context staging tree is missing.")
    result: list[tuple[str, bytes]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            if path.is_symlink():
                raise PackageError(
                    "BUILD_PACK_SYMLINK_REJECTED",
                    "The build pack cannot contain symbolic links.",
                    details={"path": str(path)},
                )
            continue
        if path.is_symlink():
            raise PackageError(
                "BUILD_PACK_SYMLINK_REJECTED",
                "The build pack cannot contain symbolic links.",
                details={"path": str(path)},
            )
        relative = _safe_relative(path.relative_to(root).as_posix())
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise PackageError(
                "BUILD_PACK_READ_FAILED",
                "A build-pack file could not be read.",
                details={"path": relative},
            ) from exc
        result.append((relative, data))
    return result


def _write(root: Path, relative: str, data: bytes) -> None:
    path = root / _safe_relative(relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _manifest_files(entries: Iterable[tuple[str, bytes]]) -> list[dict[str, Any]]:
    return [
        {"path": path, "size_bytes": len(data), "sha256": _sha256(data)}
        for path, data in sorted(entries, key=lambda item: item[0])
    ]


def _zip_bytes(entries: Iterable[tuple[str, bytes]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, data in sorted(entries, key=lambda item: item[0]):
            info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return output.getvalue()


def verify_bundle_bytes(data: bytes, *, max_bytes: int) -> dict[str, Any]:
    """Verify ZIP safety, manifest coverage, and every listed file hash."""
    if len(data) > max_bytes:
        raise PackageError(
            "BUILD_PACK_TOO_LARGE",
            "The build pack exceeds the configured size limit.",
            details={"size_bytes": len(data), "max_bundle_bytes": max_bytes},
        )
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise PackageError(
            "BUILD_PACK_INVALID_ZIP", "The generated build pack is not a valid ZIP."
        ) from exc
    with archive:
        if archive.testzip() is not None:
            raise PackageError(
                "BUILD_PACK_CORRUPT_ZIP", "The generated build pack contains corrupt data."
            )
        names = archive.namelist()
        if len(names) != len(set(names)) or any(_safe_relative(name) != name for name in names):
            raise PackageError(
                "BUILD_PACK_UNSAFE_PATH", "The build pack contains duplicate or unsafe paths."
            )
        if "manifest.json" not in names:
            raise PackageError(
                "BUILD_PACK_MANIFEST_MISSING", "The build pack has no top-level manifest."
            )
        try:
            manifest = json.loads(archive.read("manifest.json"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PackageError(
                "BUILD_PACK_MANIFEST_INVALID", "The build-pack manifest is invalid."
            ) from exc
        listed = manifest.get("files") if isinstance(manifest, dict) else None
        if not isinstance(listed, list):
            raise PackageError(
                "BUILD_PACK_MANIFEST_INVALID", "The build-pack manifest has no file index."
            )
        listed_paths: set[str] = set()
        for entry in listed:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                raise PackageError(
                    "BUILD_PACK_MANIFEST_INVALID", "The build-pack file index is invalid."
                )
            path = _safe_relative(entry["path"])
            if path in listed_paths or path not in names or path == "manifest.json":
                raise PackageError(
                    "BUILD_PACK_MANIFEST_INVALID",
                    "The build-pack manifest has a dangling file entry.",
                )
            listed_paths.add(path)
            content = archive.read(path)
            if int(entry.get("size_bytes", -1)) != len(content) or entry.get("sha256") != _sha256(
                content
            ):
                raise PackageError(
                    "BUILD_PACK_FILE_HASH_MISMATCH",
                    "A build-pack file failed manifest verification.",
                    details={"path": path},
                )
        if listed_paths != set(names) - {"manifest.json"}:
            raise PackageError(
                "BUILD_PACK_MANIFEST_INVALID", "The build-pack manifest does not cover every file."
            )
        return cast(dict[str, Any], manifest)


def _mirror_path(output_dir: Path, run_id: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S")
    run_prefix = _safe_segment(run_id[:8], "run")
    base = output_dir / "build-preparation" / f"{timestamp}-{run_prefix}"
    candidate = base / "build-context"
    suffix = 0
    while candidate.exists():
        suffix += 1
        candidate = (base.parent / f"{base.name}-{suffix}") / "build-context"
    return candidate


def restore_verified_bundle(data: bytes, destination: Path, *, max_bytes: int) -> list[str]:
    """Extract verified ZIP bytes without trusting archive paths."""
    manifest = verify_bundle_bytes(data, max_bytes=max_bytes)
    destination.mkdir(parents=True, exist_ok=False)
    written: list[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        manifest_target = destination / "manifest.json"
        manifest_target.write_bytes(archive.read("manifest.json"))
        written.append("manifest.json")
        for entry in manifest["files"]:
            relative = _safe_relative(str(entry["path"]))
            target = destination / relative
            if destination not in target.parents:
                raise PackageError(
                    "BUILD_PACK_UNSAFE_PATH", "The mirror path escaped its destination."
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            content = archive.read(relative)
            target.write_bytes(content)
            written.append(relative)
    return written


async def package_and_store(
    *,
    staging_root: Path,
    output_dir: str | Path,
    run_id: str,
    portfolio_session_id: UUID,
    scope_hash: str,
    source_ref: BuildPreparationSourceRef,
    materialization: MaterializationResult,
    settings: Any,
    artifact_store: ArtifactStore | None = None,
    upload_enabled: bool = True,
    mirror_enabled: bool = True,
    expires_at: str | None = None,
) -> tuple[PackageResult, MaterializationResult]:
    """Build, verify, store, read back, and optionally mirror one pack."""
    if expires_at is None:
        now = datetime.now(UTC)
        ttl_days = max(1, int(settings.build_preparation.bundle_ttl_days))
        expires_at = (now + timedelta(days=ttl_days)).isoformat()
    existing_entries = _read_tree(staging_root)
    if any(path == "manifest.json" for path, _ in existing_entries):
        raise PackageError(
            "BUILD_PACK_DUPLICATE_MANIFEST",
            "The staging tree already contains a top-level manifest.",
        )
    base_files = _manifest_files(existing_entries)
    checksums = {entry["path"]: entry["sha256"] for entry in base_files}
    checksums_bytes = _json_bytes({"algorithm": "sha256", "files": checksums})
    _write(staging_root, "provenance/checksums.json", checksums_bytes)
    entries_with_checksums = _read_tree(staging_root)
    manifest = {
        "pack_version": "phase3",
        "run_id": run_id,
        "scope_hash": scope_hash,
        "source_ref": source_ref.model_dump(mode="json"),
        "expires_at": expires_at,
        "files": _manifest_files(entries_with_checksums),
    }
    _write(staging_root, "manifest.json", _json_bytes(manifest))
    final_entries = _read_tree(staging_root)
    total_size = sum(len(data) for _, data in final_entries)
    max_bundle_bytes = int(settings.build_preparation.max_bundle_bytes)
    if total_size > max_bundle_bytes:
        raise PackageError(
            "BUILD_PACK_TOO_LARGE",
            "The uncompressed build pack exceeds the configured size limit.",
            details={"size_bytes": total_size, "max_bundle_bytes": max_bundle_bytes},
        )
    archive_bytes = _zip_bytes(final_entries)
    verified_manifest = verify_bundle_bytes(archive_bytes, max_bytes=max_bundle_bytes)
    archive_hash = _sha256(archive_bytes)
    key_prefix = str(settings.artifact_storage.prefix or "temporary").strip("/")
    key = "/".join(
        part
        for part in (
            key_prefix,
            _safe_segment(str(portfolio_session_id), "session"),
            _safe_segment(source_ref.input_projection_hash[:32], "source"),
            f"{_safe_segment(run_id, 'run')}-{archive_hash[:24]}.zip",
        )
        if part
    )
    store = artifact_store
    if store is None:
        store = create_artifact_store(settings) if upload_enabled else MemoryArtifactStore()
    reference = await store.put_verified(
        key=key,
        data=archive_bytes,
        sha256=archive_hash,
        expires_at=expires_at,
    )
    restored_bytes = await store.get_verified(reference)
    if restored_bytes != archive_bytes:
        raise PackageError(
            "ARTIFACT_READBACK_MISMATCH", "Artifact read-back bytes differ from the generated pack."
        )
    verify_bundle_bytes(restored_bytes, max_bytes=max_bundle_bytes)

    mirror_root = ""
    mirror_relative_root = ""
    if mirror_enabled:
        destination = _mirror_path(Path(output_dir), run_id)
        restore_verified_bundle(restored_bytes, destination, max_bytes=max_bundle_bytes)
        mirror_root = str(destination)
        mirror_relative_root = (
            str(destination.relative_to(Path.cwd())).replace("\\", "/")
            if destination.is_relative_to(Path.cwd())
            else str(destination)
        )

    package = PackageResult(
        archive_sha256=archive_hash,
        archive_size_bytes=len(archive_bytes),
        file_count=len(verified_manifest["files"]) + 1,
        expires_at=expires_at,
        artifact=reference,
        mirror_root=mirror_root,
        mirror_relative_root=mirror_relative_root,
    )
    mirrored_materialization = materialization.model_copy(
        update={
            "root_path": mirror_root,
            "relative_root": mirror_relative_root,
        }
    )
    return package, mirrored_materialization


@contextmanager
def staging_directory(output_dir: str | Path = "output") -> Iterator[str]:
    """Create a disposable staging directory for one agent run."""
    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)
    staging = base / "build-preparation-staging" / str(uuid4())
    staging.mkdir(parents=True, exist_ok=False)
    try:
        yield str(staging)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
