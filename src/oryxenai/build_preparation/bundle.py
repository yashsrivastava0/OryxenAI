"""Deterministic bundle creation and safe extraction."""

from __future__ import annotations

import hashlib
import json
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

from oryxenai.build_preparation.fingerprints import canonical_json
from oryxenai.build_preparation.schemas import (
    ExperienceBlueprint,
    PageBuildPacket,
    PortfolioBuildContext,
    ResourceManifest,
)


class BundleIntegrityError(ValueError):
    pass


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def _safe_member(name: str) -> str:
    normalized = PurePosixPath(name)
    if normalized.is_absolute() or ".." in normalized.parts or "" in normalized.parts:
        raise BundleIntegrityError("bundle contains an unsafe path")
    if "\\" in name or not name:
        raise BundleIntegrityError("bundle contains an invalid path")
    return str(normalized)


def create_bundle(
    blueprint: ExperienceBlueprint,
    manifest: ResourceManifest,
    context: PortfolioBuildContext,
    packets: list[PageBuildPacket],
    *,
    target_contract: dict[str, Any] | None = None,
    resource_files: dict[str, bytes] | None = None,
    max_bundle_bytes: int = 64 * 1024 * 1024,
    workspace_dir: Path | None = None,
) -> tuple[Path, str, int]:
    """Create a deterministic ZIP in a temporary directory.

    The caller owns the returned temporary directory and must delete it after
    upload. Resource file keys are already validated pack-relative paths.
    """
    if workspace_dir is None:
        temp_dir = Path(tempfile.mkdtemp(prefix="oryxenai-build-pack-"))
    else:
        temp_dir = workspace_dir / f"oryxenai-build-pack-{uuid4().hex}"
        temp_dir.mkdir(parents=True, exist_ok=True)
    root = temp_dir / "payload"
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "experience-blueprint.json", blueprint.model_dump(mode="json"))
    _write_json(root / "resource-manifest.json", manifest.model_dump(mode="json"))
    _write_json(root / "portfolio-build-context.json", context.model_dump(mode="json"))
    _write_json(
        root / "bundle.json",
        {
            "schema_version": "1",
            "blueprint_hash": blueprint.blueprint_hash,
            "manifest_hash": manifest.manifest_hash,
            "context_hash": context.context_hash,
            "target_contract": target_contract or {},
            "packet_ids": [packet.packet_id for packet in packets],
        },
    )
    for packet in packets:
        _write_json(root / "pages" / f"{packet.packet_id}.json", packet.model_dump(mode="json"))
    for relative, data in (resource_files or {}).items():
        safe = _safe_member(relative)
        path = root / safe
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    checksums: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            checksums[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    _write_json(root / "provenance" / "checksums.json", checksums)

    zip_path = temp_dir / "bundle.zip"
    with zipfile.ZipFile(
        zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, path.read_bytes())
    size = zip_path.stat().st_size
    if size > max_bundle_bytes:
        raise BundleIntegrityError("build preparation bundle exceeds the configured size limit")
    return zip_path, hashlib.sha256(zip_path.read_bytes()).hexdigest(), size


def verify_zip_file(path: Path, *, max_bytes: int = 64 * 1024 * 1024) -> dict[str, str]:
    if not path.is_file() or path.stat().st_size > max_bytes:
        raise BundleIntegrityError("bundle is missing or too large")
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > 512:
            raise BundleIntegrityError("bundle contains too many entries")
        checksums: dict[str, str] = {}
        for info in infos:
            name = _safe_member(info.filename)
            if name in checksums:
                raise BundleIntegrityError("bundle contains duplicate entries")
            mode = info.external_attr >> 16
            if info.is_dir() or stat.S_IFMT(mode) == stat.S_IFLNK:
                raise BundleIntegrityError("bundle contains a directory or symlink entry")
            if info.file_size > max_bytes or (
                info.compress_size and info.file_size / info.compress_size > 1000
            ):
                raise BundleIntegrityError("bundle entry exceeds safe extraction limits")
            checksums[name] = hashlib.sha256(archive.read(info)).hexdigest()
        if "provenance/checksums.json" not in checksums:
            raise BundleIntegrityError("bundle checksum index is missing")
        try:
            declared = json.loads(archive.read("provenance/checksums.json").decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BundleIntegrityError("bundle checksum index is malformed") from exc
        if not isinstance(declared, dict) or any(
            not isinstance(name, str) or not isinstance(digest, str)
            for name, digest in declared.items()
        ):
            raise BundleIntegrityError("bundle checksum index is malformed")
        for name, digest in declared.items():
            if name not in checksums or checksums[name] != digest:
                raise BundleIntegrityError("bundle checksum verification failed")
        return checksums


def extract_verified(path: Path, destination: Path) -> None:
    verify_zip_file(path)
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            name = _safe_member(info.filename)
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
