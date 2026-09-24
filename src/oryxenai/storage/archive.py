"""Read and remove previously stored output during account cleanup."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol, cast

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]


class ArchiveStorageError(ValueError):
    """A safe failure while inspecting or removing a stored object."""


@dataclass(frozen=True, slots=True)
class ArchiveObject:
    key: str
    sha256: str
    size_bytes: int
    content_type: str
    etag: str


def _safe_key(key: str) -> str:
    normalized = key.replace("\\", "/").strip("/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or ".." in path.parts
        or any(part.startswith(".") for part in path.parts)
    ):
        raise ArchiveStorageError("ARCHIVE_KEY_UNSAFE", "The stored-object key is unsafe.")
    return path.as_posix()


class ArchiveStorage(Protocol):
    async def get(self, key: str) -> tuple[ArchiveObject, bytes] | None: ...

    async def head(self, key: str) -> ArchiveObject | None: ...

    async def delete(self, key: str) -> None: ...

    async def list_prefix(
        self, prefix: str, *, limit: int = 100, continuation: str | None = None
    ) -> tuple[list[str], str | None]: ...


class MemoryArchiveStorage:
    """No-op archive store for tests and in-memory configurations."""

    async def get(self, key: str) -> tuple[ArchiveObject, bytes] | None:
        _safe_key(key)
        return None

    async def head(self, key: str) -> ArchiveObject | None:
        _safe_key(key)
        return None

    async def delete(self, key: str) -> None:
        _safe_key(key)

    async def list_prefix(
        self, prefix: str, *, limit: int = 100, continuation: str | None = None
    ) -> tuple[list[str], str | None]:
        _safe_key(prefix)
        return [], None


class LocalArchiveStorage:
    """Filesystem reader for previously written files and integrity metadata."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.metadata_root = self.root / ".metadata"

    def _path(self, key: str) -> Path:
        path = (self.root / _safe_key(key)).resolve()
        if not path.is_relative_to(self.root) or path == self.metadata_root:
            raise ArchiveStorageError("ARCHIVE_PATH_UNSAFE", "The stored-object path is unsafe.")
        return path

    def _metadata(self, key: str) -> Path:
        token = hashlib.sha256(_safe_key(key).encode()).hexdigest()
        return self.metadata_root / f"{token}.json"

    async def get(self, key: str) -> tuple[ArchiveObject, bytes] | None:
        key = _safe_key(key)
        path = self._path(key)
        metadata = self._metadata(key)
        if not path.is_file() or not metadata.is_file():
            return None
        try:
            payload = json.loads(metadata.read_text(encoding="utf-8"))
            data = path.read_bytes()
            reference = ArchiveObject(
                key=str(payload["key"]),
                sha256=str(payload["sha256"]),
                size_bytes=int(payload["size_bytes"]),
                content_type=str(payload["content_type"]),
                etag=str(payload["etag"]),
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ArchiveStorageError(
                "ARCHIVE_METADATA_INVALID", "Stored-object metadata is invalid."
            ) from exc
        if (
            hashlib.sha256(data).hexdigest() != reference.sha256
            or len(data) != reference.size_bytes
        ):
            raise ArchiveStorageError(
                "ARCHIVE_HASH_MISMATCH", "Stored-object integrity verification failed."
            )
        return reference, data

    async def head(self, key: str) -> ArchiveObject | None:
        result = await self.get(key)
        return result[0] if result else None

    async def delete(self, key: str) -> None:
        path = self._path(key)
        metadata = self._metadata(key)
        try:
            if path.exists():
                path.unlink()
            if metadata.exists():
                metadata.unlink()
        except OSError as exc:
            raise ArchiveStorageError(
                "ARCHIVE_DELETE_FAILED", "The stored object could not be removed."
            ) from exc

    async def list_prefix(
        self, prefix: str, *, limit: int = 100, continuation: str | None = None
    ) -> tuple[list[str], str | None]:
        prefix = _safe_key(prefix).rstrip("/") + "/"
        root = (self.root / prefix).resolve()
        if not root.is_relative_to(self.root) or not root.is_dir():
            return [], None
        keys = sorted(
            path.relative_to(self.root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and not path.is_relative_to(self.metadata_root)
        )
        start = 0
        if continuation:
            start = next(
                (index + 1 for index, key in enumerate(keys) if key == continuation), len(keys)
            )
        selected = keys[start : start + max(1, min(limit, 100))]
        next_key = selected[-1] if start + len(selected) < len(keys) else None
        return selected, next_key


class S3ArchiveStorage:
    """Read-only S3-compatible access plus deletion for archived objects."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        bucket: str,
        region: str,
        prefix: str,
        access_key_env: str,
        secret_key_env: str,
    ) -> None:
        if not endpoint_url or not bucket:
            raise ArchiveStorageError(
                "ARCHIVE_STORAGE_NOT_CONFIGURED", "Archive storage needs an endpoint and bucket."
            )
        access_key = os.getenv(access_key_env, "")
        secret_key = os.getenv(secret_key_env, "")
        if not access_key or not secret_key:
            raise ArchiveStorageError(
                "ARCHIVE_STORAGE_CREDENTIALS_MISSING", "Archive storage credentials are missing."
            )
        self._bucket = bucket
        self._prefix = prefix.strip("/")
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def _physical_key(self, key: str) -> str:
        safe = _safe_key(key)
        if self._prefix and (safe == self._prefix or safe.startswith(f"{self._prefix}/")):
            return safe
        return f"{self._prefix}/{safe}" if self._prefix else safe

    @staticmethod
    def _not_found(exc: ClientError) -> bool:
        return str(exc.response.get("Error", {}).get("Code", "")) in {
            "404",
            "NoSuchKey",
            "NotFound",
        }

    @staticmethod
    def _reference(key: str, response: Mapping[str, Any]) -> ArchiveObject:
        metadata = response.get("Metadata", {})
        digest = str(metadata.get("sha256", ""))
        if not digest:
            raise ArchiveStorageError(
                "ARCHIVE_METADATA_INVALID", "The stored object has no integrity metadata."
            )
        return ArchiveObject(
            key=key,
            sha256=digest,
            size_bytes=int(response.get("ContentLength", 0) or 0),
            content_type=str(response.get("ContentType", "application/octet-stream")),
            etag=str(response.get("ETag", "")).strip('"'),
        )

    async def get(self, key: str) -> tuple[ArchiveObject, bytes] | None:
        key = _safe_key(key)

        def fetch() -> tuple[Mapping[str, Any], bytes]:
            response = self._client.get_object(Bucket=self._bucket, Key=self._physical_key(key))
            body = response["Body"]
            try:
                return cast(Mapping[str, Any], response), cast(bytes, body.read())
            finally:
                body.close()

        try:
            response, data = await asyncio.to_thread(fetch)
        except ClientError as exc:
            if self._not_found(exc):
                return None
            raise ArchiveStorageError(
                "ARCHIVE_READ_FAILED", "The stored object could not be read."
            ) from exc
        except Exception as exc:
            raise ArchiveStorageError(
                "ARCHIVE_READ_FAILED", "The stored object could not be read."
            ) from exc
        reference = self._reference(key, response)
        if (
            hashlib.sha256(data).hexdigest() != reference.sha256
            or len(data) != reference.size_bytes
        ):
            raise ArchiveStorageError(
                "ARCHIVE_HASH_MISMATCH", "Stored-object integrity verification failed."
            )
        return reference, data

    async def head(self, key: str) -> ArchiveObject | None:
        key = _safe_key(key)
        try:
            response = await asyncio.to_thread(
                lambda: self._client.head_object(Bucket=self._bucket, Key=self._physical_key(key))
            )
        except ClientError as exc:
            if self._not_found(exc):
                return None
            raise ArchiveStorageError(
                "ARCHIVE_HEAD_FAILED", "Stored-object metadata is unavailable."
            ) from exc
        except Exception as exc:
            raise ArchiveStorageError(
                "ARCHIVE_HEAD_FAILED", "Stored-object metadata is unavailable."
            ) from exc
        return self._reference(key, cast(Mapping[str, Any], response))

    async def delete(self, key: str) -> None:
        key = _safe_key(key)
        try:
            await asyncio.to_thread(
                lambda: self._client.delete_object(Bucket=self._bucket, Key=self._physical_key(key))
            )
        except Exception as exc:
            raise ArchiveStorageError(
                "ARCHIVE_DELETE_FAILED", "The stored object could not be removed."
            ) from exc

    async def list_prefix(
        self, prefix: str, *, limit: int = 100, continuation: str | None = None
    ) -> tuple[list[str], str | None]:
        prefix = _safe_key(prefix).rstrip("/") + "/"
        kwargs: dict[str, Any] = {
            "Bucket": self._bucket,
            "Prefix": self._physical_key(prefix),
            "MaxKeys": max(1, min(limit, 100)),
        }
        if continuation:
            if len(continuation) > 2048 or any(
                ord(char) < 32 or ord(char) == 127 for char in continuation
            ):
                raise ArchiveStorageError(
                    "ARCHIVE_CONTINUATION_UNSAFE", "The pagination token is unsafe."
                )
            kwargs["ContinuationToken"] = continuation
        try:
            response = await asyncio.to_thread(lambda: self._client.list_objects_v2(**kwargs))
        except Exception as exc:
            raise ArchiveStorageError(
                "ARCHIVE_LIST_FAILED", "The stored-object prefix could not be listed."
            ) from exc
        physical_prefix = f"{self._prefix}/" if self._prefix else ""
        keys = [
            str(item["Key"])[len(physical_prefix) :]
            for item in response.get("Contents", [])
            if isinstance(item, Mapping)
            and "Key" in item
            and str(item["Key"]).startswith(physical_prefix)
        ]
        token = response.get("NextContinuationToken") if response.get("IsTruncated") else None
        return keys, str(token) if token else None


def _repository_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src").is_dir():
            return parent
    return Path.cwd()


def create_archive_storage(settings: object) -> ArchiveStorage:
    config = getattr(settings, "archive_storage", None)
    provider = str(getattr(config, "provider", "local_fs") or "local_fs")
    if provider == "memory":
        return MemoryArchiveStorage()
    if provider == "local_fs":
        root_value = str(getattr(config, "root", ".workspace/archive-storage"))
        root = Path(root_value)
        if not root.is_absolute():
            root = _repository_root() / root
        return LocalArchiveStorage(root)
    source = (
        getattr(settings, "artifact_storage", None) if provider == "artifact_storage" else config
    )
    if provider in {"artifact_storage", "r2_s3", "s3"}:
        return S3ArchiveStorage(
            endpoint_url=str(getattr(source, "endpoint_url", "") or ""),
            bucket=str(getattr(source, "bucket", "") or ""),
            region=str(getattr(source, "region", "auto") or "auto"),
            prefix=str(getattr(config, "prefix", "preview") or "preview"),
            access_key_env=str(
                getattr(source, "access_key_env", "R2_ACCESS_KEY_ID") or "R2_ACCESS_KEY_ID"
            ),
            secret_key_env=str(
                getattr(source, "secret_key_env", "R2_SECRET_ACCESS_KEY") or "R2_SECRET_ACCESS_KEY"
            ),
        )
    raise ArchiveStorageError(
        "ARCHIVE_STORAGE_PROVIDER_UNSUPPORTED", "The configured archive store is unsupported."
    )
