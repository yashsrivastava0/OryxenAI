"""Immutable, content-addressed artifacts for Code Generator workflow state."""

from __future__ import annotations

import hashlib
import json
import os
import zipfile
from collections.abc import Mapping
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from oryxenai.storage.artifacts import ArtifactReference, ArtifactStore


class CodeGeneratorArtifactReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_kind: str
    key: str
    sha256: str
    size_bytes: int = Field(ge=0)
    etag: str = ""
    expires_at: str
    manifest_hash: str = ""
    content_type: str = "application/octet-stream"


class CodeGeneratorArtifactRepository(Protocol):
    async def put(
        self,
        *,
        artifact_kind: str,
        data: bytes,
        expires_at: str,
        manifest: Mapping[str, Any] | None = None,
        content_type: str = "application/octet-stream",
    ) -> CodeGeneratorArtifactReference: ...

    async def get(self, reference: CodeGeneratorArtifactReference) -> bytes: ...

    async def head(
        self, reference: CodeGeneratorArtifactReference
    ) -> CodeGeneratorArtifactReference | None: ...


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _manifest_hash(manifest: Mapping[str, Any] | None) -> str:
    return hashlib.sha256(_canonical(dict(manifest or {}))).hexdigest()


def _validate_expiry(expires_at: str) -> None:
    try:
        value = datetime.fromisoformat(expires_at)
    except ValueError as exc:
        raise ValueError("artifact expiry is not a valid ISO timestamp") from exc
    if value.tzinfo is None:
        raise ValueError("artifact expiry must include a timezone")


def deterministic_bundle(files: Mapping[str, bytes]) -> tuple[bytes, dict[str, Any]]:
    """Build a reproducible ZIP plus its per-file hash manifest."""

    normalized: dict[str, bytes] = {}
    for name, data in files.items():
        path = Path(str(name).replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or not str(path):
            raise ValueError("artifact bundle contains an unsafe path")
        normalized[path.as_posix()] = bytes(data)
    manifest = {
        "schema_version": "code-generator-artifact-bundle-v1",
        "files": [
            {
                "path": name,
                "size_bytes": len(normalized[name]),
                "sha256": hashlib.sha256(normalized[name]).hexdigest(),
            }
            for name in sorted(normalized)
        ],
    }
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(normalized):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, normalized[name])
        archive.writestr(
            zipfile.ZipInfo("artifact-manifest.json", date_time=(1980, 1, 1, 0, 0, 0)),
            _canonical(manifest) + b"\n",
        )
    return output.getvalue(), manifest


class LocalFsCodeGeneratorArtifactRepository:
    """Local development store with immutable hash-addressed paths."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def _paths(self, reference: CodeGeneratorArtifactReference) -> tuple[Path, Path]:
        safe_kind = reference.artifact_kind.replace("/", "-").replace("\\", "-")
        target = (self.root / safe_kind / reference.sha256[:2] / reference.sha256).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError("artifact path escapes the configured root")
        return target, target.with_suffix(target.suffix + ".json")

    async def put(
        self,
        *,
        artifact_kind: str,
        data: bytes,
        expires_at: str,
        manifest: Mapping[str, Any] | None = None,
        content_type: str = "application/octet-stream",
    ) -> CodeGeneratorArtifactReference:
        if not artifact_kind.strip():
            raise ValueError("artifact kind is required")
        _validate_expiry(expires_at)
        payload = bytes(data)
        digest = hashlib.sha256(payload).hexdigest()
        reference = CodeGeneratorArtifactReference(
            artifact_kind=artifact_kind,
            key=f"{artifact_kind}/{digest[:2]}/{digest}",
            sha256=digest,
            size_bytes=len(payload),
            etag=digest,
            expires_at=expires_at,
            manifest_hash=_manifest_hash(manifest),
            content_type=content_type,
        )
        target, metadata_path = self._paths(reference)
        target.parent.mkdir(parents=True, exist_ok=True)
        metadata = reference.model_dump(mode="json") | {"manifest": dict(manifest or {})}
        if target.exists():
            existing = await self.head(reference)
            if existing is None or existing != reference:
                raise ValueError("immutable artifact key contains conflicting metadata")
            if target.read_bytes() != payload:
                raise ValueError("immutable artifact key contains different bytes")
            return existing
        temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        temporary.write_bytes(payload)
        os.replace(temporary, target)
        metadata_path.write_bytes(_canonical(metadata) + b"\n")
        return reference

    async def head(
        self, reference: CodeGeneratorArtifactReference
    ) -> CodeGeneratorArtifactReference | None:
        target, metadata_path = self._paths(reference)
        if not target.is_file() or not metadata_path.is_file():
            return None
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            actual = CodeGeneratorArtifactReference.model_validate(
                {key: value for key, value in metadata.items() if key != "manifest"}
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            return None
        if actual != reference:
            return None
        if target.stat().st_size != reference.size_bytes:
            return None
        return actual

    async def get(self, reference: CodeGeneratorArtifactReference) -> bytes:
        target, metadata_path = self._paths(reference)
        if not target.is_file() or not metadata_path.is_file():
            raise FileNotFoundError("immutable Code Generator artifact is unavailable")
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            found = CodeGeneratorArtifactReference.model_validate(
                {key: value for key, value in metadata.items() if key != "manifest"}
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError("immutable Code Generator artifact metadata is invalid") from exc
        if found != reference:
            raise ValueError("immutable Code Generator artifact metadata changed")
        data = target.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != reference.sha256 or len(data) != reference.size_bytes:
            raise ValueError("Code Generator artifact failed hash or size verification")
        return data


class R2S3CodeGeneratorArtifactRepository:
    """Adapter that keeps the workflow contract independent of S3/R2."""

    def __init__(self, store: ArtifactStore, *, prefix: str = "code-generator") -> None:
        self.store = store
        self.prefix = prefix.strip("/")

    @staticmethod
    def _to_reference(
        artifact_kind: str, reference: ArtifactReference, manifest_hash: str = ""
    ) -> CodeGeneratorArtifactReference:
        return CodeGeneratorArtifactReference(
            artifact_kind=artifact_kind,
            key=reference.key,
            sha256=reference.sha256,
            size_bytes=reference.size_bytes,
            etag=reference.etag,
            expires_at=reference.expires_at,
            manifest_hash=manifest_hash,
            content_type=reference.content_type,
        )

    async def put(
        self,
        *,
        artifact_kind: str,
        data: bytes,
        expires_at: str,
        manifest: Mapping[str, Any] | None = None,
        content_type: str = "application/octet-stream",
    ) -> CodeGeneratorArtifactReference:
        digest = hashlib.sha256(data).hexdigest()
        key = f"{self.prefix}/{artifact_kind}/{digest[:2]}/{digest}"
        reference = await self.store.put_verified(
            key=key,
            data=data,
            sha256=digest,
            expires_at=expires_at,
            content_type=content_type,
        )
        return self._to_reference(artifact_kind, reference, _manifest_hash(manifest))

    async def get(self, reference: CodeGeneratorArtifactReference) -> bytes:
        return await self.store.get_verified(
            ArtifactReference(
                provider="r2_s3",
                key=reference.key,
                sha256=reference.sha256,
                size_bytes=reference.size_bytes,
                expires_at=reference.expires_at,
                etag=reference.etag,
                content_type=reference.content_type,
            )
        )

    async def head(
        self, reference: CodeGeneratorArtifactReference
    ) -> CodeGeneratorArtifactReference | None:
        found = await self.store.head(
            ArtifactReference(
                provider="r2_s3",
                key=reference.key,
                sha256=reference.sha256,
                size_bytes=reference.size_bytes,
                expires_at=reference.expires_at,
                etag=reference.etag,
                content_type=reference.content_type,
            )
        )
        return (
            None
            if found is None
            else self._to_reference(reference.artifact_kind, found, reference.manifest_hash)
        )


LocalFileCodeGeneratorArtifactRepository = LocalFsCodeGeneratorArtifactRepository
R2S3ArtifactRepository = R2S3CodeGeneratorArtifactRepository
