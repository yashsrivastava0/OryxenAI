"""Immutable candidate and conditional preview-pointer storage."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol, cast

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]


class PreviewStorageError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class PreviewObject:
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
        raise PreviewStorageError("PREVIEW_KEY_UNSAFE", "The preview object key is unsafe.")
    return path.as_posix()


def _object(data: bytes, *, key: str, content_type: str) -> PreviewObject:
    digest = hashlib.sha256(data).hexdigest()
    return PreviewObject(
        key=key, sha256=digest, size_bytes=len(data), content_type=content_type, etag=digest
    )


class PreviewStorage(Protocol):
    async def put_immutable(self, *, key: str, data: bytes, content_type: str) -> PreviewObject: ...

    async def get(self, key: str) -> tuple[PreviewObject, bytes] | None: ...

    async def head(self, key: str) -> PreviewObject | None: ...

    async def put_conditional(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
        expected_etag: str | None,
    ) -> PreviewObject: ...

    async def delete(self, key: str) -> None: ...


class MemoryPreviewStorage:
    def __init__(self) -> None:
        self._objects: dict[str, tuple[PreviewObject, bytes]] = {}
        self._lock = asyncio.Lock()

    async def put_immutable(self, *, key: str, data: bytes, content_type: str) -> PreviewObject:
        key = _safe_key(key)
        reference = _object(data, key=key, content_type=content_type)
        async with self._lock:
            existing = self._objects.get(key)
            if existing is not None:
                if existing[0].sha256 != reference.sha256 or existing[1] != data:
                    raise PreviewStorageError(
                        "PREVIEW_IMMUTABLE_CONFLICT",
                        "The immutable preview key contains different bytes.",
                    )
                return existing[0]
            self._objects[key] = (reference, bytes(data))
        return reference

    async def get(self, key: str) -> tuple[PreviewObject, bytes] | None:
        existing = self._objects.get(_safe_key(key))
        return (existing[0], bytes(existing[1])) if existing is not None else None

    async def head(self, key: str) -> PreviewObject | None:
        existing = self._objects.get(_safe_key(key))
        return existing[0] if existing is not None else None

    async def put_conditional(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
        expected_etag: str | None,
    ) -> PreviewObject:
        key = _safe_key(key)
        async with self._lock:
            existing = self._objects.get(key)
            if expected_etag is None and existing is not None:
                raise PreviewStorageError(
                    "PREVIEW_CONDITION_FAILED", "The preview pointer already exists."
                )
            if expected_etag is not None and (
                existing is None or existing[0].etag != expected_etag
            ):
                raise PreviewStorageError(
                    "PREVIEW_CONDITION_FAILED", "The preview pointer changed concurrently."
                )
            reference = _object(data, key=key, content_type=content_type)
            self._objects[key] = (reference, bytes(data))
            return reference

    async def delete(self, key: str) -> None:
        self._objects.pop(_safe_key(key), None)


class LocalPreviewStorage:
    """Filesystem implementation used by local development and CI."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.metadata_root = self.root / ".metadata"
        self._lock = asyncio.Lock()

    def _path(self, key: str) -> Path:
        safe = _safe_key(key)
        path = (self.root / safe).resolve()
        if not path.is_relative_to(self.root) or path == self.metadata_root:
            raise PreviewStorageError(
                "PREVIEW_PATH_UNSAFE", "The preview path escaped its storage root."
            )
        return path

    def _metadata(self, key: str) -> Path:
        token = hashlib.sha256(_safe_key(key).encode()).hexdigest()
        return self.metadata_root / f"{token}.json"

    async def put_immutable(self, *, key: str, data: bytes, content_type: str) -> PreviewObject:
        key = _safe_key(key)
        async with self._lock:
            existing = await self.get(key)
            if existing is not None:
                if existing[0].sha256 != hashlib.sha256(data).hexdigest() or existing[1] != data:
                    raise PreviewStorageError(
                        "PREVIEW_IMMUTABLE_CONFLICT",
                        "The immutable preview key contains different bytes.",
                    )
                return existing[0]
            path = self._path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.metadata_root.mkdir(parents=True, exist_ok=True)
            _atomic_write_bytes(path, data)
            reference = _object(data, key=key, content_type=content_type)
            self._metadata(key).write_text(
                json.dumps(asdict(reference), sort_keys=True) + "\n", encoding="utf-8"
            )
            return reference

    async def get(self, key: str) -> tuple[PreviewObject, bytes] | None:
        key = _safe_key(key)
        path = self._path(key)
        metadata = self._metadata(key)
        if not path.is_file() or not metadata.is_file():
            return None
        try:
            payload = json.loads(metadata.read_text(encoding="utf-8"))
            data = path.read_bytes()
            reference = PreviewObject(
                key=str(payload["key"]),
                sha256=str(payload["sha256"]),
                size_bytes=int(payload["size_bytes"]),
                content_type=str(payload["content_type"]),
                etag=str(payload["etag"]),
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise PreviewStorageError(
                "PREVIEW_METADATA_INVALID", "Preview object metadata is invalid."
            ) from exc
        if (
            hashlib.sha256(data).hexdigest() != reference.sha256
            or len(data) != reference.size_bytes
        ):
            raise PreviewStorageError(
                "PREVIEW_HASH_MISMATCH", "Preview object read-back verification failed."
            )
        return reference, data

    async def head(self, key: str) -> PreviewObject | None:
        result = await self.get(key)
        return result[0] if result else None

    async def put_conditional(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
        expected_etag: str | None,
    ) -> PreviewObject:
        key = _safe_key(key)
        async with self._lock:
            existing = await self.get(key)
            if expected_etag is None and existing is not None:
                raise PreviewStorageError(
                    "PREVIEW_CONDITION_FAILED", "The preview pointer already exists."
                )
            if expected_etag is not None and (
                existing is None or existing[0].etag != expected_etag
            ):
                raise PreviewStorageError(
                    "PREVIEW_CONDITION_FAILED", "The preview pointer changed concurrently."
                )
            path = self._path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.metadata_root.mkdir(parents=True, exist_ok=True)
            reference = _object(data, key=key, content_type=content_type)
            _atomic_write_bytes(path, data)
            self._metadata(key).write_text(
                json.dumps(asdict(reference), sort_keys=True) + "\n", encoding="utf-8"
            )
            return reference

    async def delete(self, key: str) -> None:
        path = self._path(key)
        metadata = self._metadata(key)
        if path.exists():
            path.unlink()
        if metadata.exists():
            metadata.unlink()


class S3PreviewStorage:
    """S3-compatible storage for hosted, restart-safe previews.

    Logical keys remain stable for the gateway while the physical object key
    can be scoped below a configured bucket prefix. R2, AWS S3, and compatible
    providers therefore share one implementation.
    """

    def __init__(
        self,
        *,
        provider: str,
        endpoint_url: str,
        bucket: str,
        region: str,
        prefix: str,
        access_key_env: str,
        secret_key_env: str,
    ) -> None:
        if not endpoint_url or not bucket:
            raise PreviewStorageError(
                "PREVIEW_STORAGE_NOT_CONFIGURED",
                "Preview storage needs an endpoint and bucket.",
            )
        access_key = os.getenv(access_key_env, "")
        secret_key = os.getenv(secret_key_env, "")
        if not access_key or not secret_key:
            raise PreviewStorageError(
                "PREVIEW_STORAGE_CREDENTIALS_MISSING",
                "Preview storage credentials are not configured.",
            )
        self._provider = provider
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
    def _etag(value: object) -> str:
        return str(value or "").strip('"')

    @staticmethod
    def _not_found(exc: ClientError) -> bool:
        return str(exc.response.get("Error", {}).get("Code", "")) in {
            "404",
            "NoSuchKey",
            "NotFound",
        }

    @classmethod
    def _reference_from_head(cls, key: str, response: Mapping[str, Any]) -> PreviewObject:
        metadata = response.get("Metadata", {})
        sha256 = str(metadata.get("sha256", ""))
        if not sha256:
            raise PreviewStorageError(
                "PREVIEW_METADATA_INVALID",
                "The preview object has no integrity metadata.",
            )
        return PreviewObject(
            key=key,
            sha256=sha256,
            size_bytes=int(response.get("ContentLength", 0) or 0),
            content_type=str(response.get("ContentType", "application/octet-stream")),
            etag=cls._etag(response.get("ETag")),
        )

    async def put_immutable(self, *, key: str, data: bytes, content_type: str) -> PreviewObject:
        key = _safe_key(key)
        digest = hashlib.sha256(data).hexdigest()
        existing = await self.head(key)
        if existing is not None:
            if existing.sha256 != digest or existing.size_bytes != len(data):
                raise PreviewStorageError(
                    "PREVIEW_IMMUTABLE_CONFLICT",
                    "The immutable preview key contains different bytes.",
                )
            return existing

        def put() -> Mapping[str, Any]:
            return cast(
                Mapping[str, Any],
                self._client.put_object(
                    Bucket=self._bucket,
                    Key=self._physical_key(key),
                    Body=data,
                    ContentType=content_type,
                    Metadata={"sha256": digest},
                    IfNoneMatch="*",
                ),
            )

        try:
            await asyncio.to_thread(put)
        except ClientError as exc:
            if str(exc.response.get("Error", {}).get("Code", "")) in {
                "412",
                "PreconditionFailed",
            }:
                existing = await self.head(key)
                if existing is not None and existing.sha256 == digest:
                    return existing
                raise PreviewStorageError(
                    "PREVIEW_IMMUTABLE_CONFLICT",
                    "The immutable preview key contains different bytes.",
                ) from exc
            raise PreviewStorageError(
                "PREVIEW_UPLOAD_FAILED", "The preview object could not be uploaded."
            ) from exc
        except Exception as exc:
            raise PreviewStorageError(
                "PREVIEW_UPLOAD_FAILED", "The preview object could not be uploaded."
            ) from exc
        verified = await self.head(key)
        if verified is None or verified.sha256 != digest or verified.size_bytes != len(data):
            raise PreviewStorageError(
                "PREVIEW_UPLOAD_VERIFY_FAILED",
                "The uploaded preview failed integrity verification.",
            )
        return verified

    async def get(self, key: str) -> tuple[PreviewObject, bytes] | None:
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
            raise PreviewStorageError(
                "PREVIEW_READ_FAILED", "The preview object could not be read."
            ) from exc
        except Exception as exc:
            raise PreviewStorageError(
                "PREVIEW_READ_FAILED", "The preview object could not be read."
            ) from exc
        reference = self._reference_from_head(key, response)
        if (
            hashlib.sha256(data).hexdigest() != reference.sha256
            or len(data) != reference.size_bytes
        ):
            raise PreviewStorageError(
                "PREVIEW_HASH_MISMATCH", "Preview object read-back verification failed."
            )
        return reference, data

    async def head(self, key: str) -> PreviewObject | None:
        key = _safe_key(key)

        def inspect() -> Mapping[str, Any]:
            return cast(
                Mapping[str, Any],
                self._client.head_object(Bucket=self._bucket, Key=self._physical_key(key)),
            )

        try:
            response = await asyncio.to_thread(inspect)
        except ClientError as exc:
            if self._not_found(exc):
                return None
            raise PreviewStorageError(
                "PREVIEW_HEAD_FAILED", "Preview storage could not inspect the object."
            ) from exc
        except Exception as exc:
            raise PreviewStorageError(
                "PREVIEW_HEAD_FAILED", "Preview storage could not inspect the object."
            ) from exc
        return self._reference_from_head(key, response)

    async def put_conditional(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
        expected_etag: str | None,
    ) -> PreviewObject:
        key = _safe_key(key)
        digest = hashlib.sha256(data).hexdigest()
        existing = await self.head(key)
        if expected_etag is None and existing is not None:
            raise PreviewStorageError(
                "PREVIEW_CONDITION_FAILED", "The preview pointer already exists."
            )
        if expected_etag is not None and (existing is None or existing.etag != expected_etag):
            raise PreviewStorageError(
                "PREVIEW_CONDITION_FAILED", "The preview pointer changed concurrently."
            )

        kwargs: dict[str, Any] = {
            "Bucket": self._bucket,
            "Key": self._physical_key(key),
            "Body": data,
            "ContentType": content_type,
            "Metadata": {"sha256": digest},
        }
        if expected_etag is None:
            kwargs["IfNoneMatch"] = "*"
        else:
            kwargs["IfMatch"] = expected_etag

        try:
            await asyncio.to_thread(lambda: self._client.put_object(**kwargs))
        except ClientError as exc:
            if str(exc.response.get("Error", {}).get("Code", "")) in {
                "409",
                "412",
                "ConditionalRequestConflict",
                "PreconditionFailed",
            }:
                raise PreviewStorageError(
                    "PREVIEW_CONDITION_FAILED", "The preview pointer changed concurrently."
                ) from exc
            raise PreviewStorageError(
                "PREVIEW_UPLOAD_FAILED", "The preview pointer could not be written."
            ) from exc
        except Exception as exc:
            raise PreviewStorageError(
                "PREVIEW_UPLOAD_FAILED", "The preview pointer could not be written."
            ) from exc
        verified = await self.head(key)
        if verified is None or verified.sha256 != digest:
            raise PreviewStorageError(
                "PREVIEW_UPLOAD_VERIFY_FAILED",
                "The preview pointer failed integrity verification.",
            )
        return verified

    async def delete(self, key: str) -> None:
        key = _safe_key(key)
        try:
            await asyncio.to_thread(
                lambda: self._client.delete_object(Bucket=self._bucket, Key=self._physical_key(key))
            )
        except Exception as exc:
            raise PreviewStorageError(
                "PREVIEW_DELETE_FAILED", "The preview object could not be deleted."
            ) from exc


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    # Same-process writes can still hit transient Windows locks (antivirus
    # scanning the freshly written partial); retry the swap briefly.
    partial = path.with_name(f".{path.name}.partial")
    partial.write_bytes(data)
    for attempt in range(6):
        try:
            os.replace(partial, path)
            return
        except PermissionError:
            time.sleep(0.3 * (attempt + 1))
    os.replace(partial, path)


def _repository_root() -> Path:
    # Anchor relative roots at the repository (pyproject.toml) instead of the
    # process cwd, so the API, worker, and preview gateway always share one
    # storage root regardless of where they were started from.
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src").is_dir():
            return parent
    return Path.cwd()


def create_preview_storage(settings: object) -> PreviewStorage:
    config = getattr(settings, "code_generator_verification", None)
    provider = str(getattr(config, "preview_storage_provider", "local_fs") or "local_fs")
    if provider == "memory":
        return MemoryPreviewStorage()
    root_value = str(getattr(config, "preview_root", ".workspace/code-generator-preview"))
    root = Path(root_value)
    if not root.is_absolute():
        root = _repository_root() / root
    if provider == "local_fs":
        return LocalPreviewStorage(root)
    if provider in {"artifact_storage", "r2_s3", "s3"}:
        artifact = getattr(settings, "artifact_storage", None)
        source = artifact if provider == "artifact_storage" else config
        return S3PreviewStorage(
            provider=str(
                getattr(source, "provider", "r2_s3") if provider == "artifact_storage" else provider
            ),
            endpoint_url=str(getattr(source, "endpoint_url", "") or ""),
            bucket=str(getattr(source, "bucket", "") or ""),
            region=str(getattr(source, "region", "auto") or "auto"),
            prefix=str(getattr(config, "preview_storage_prefix", "preview") or "preview"),
            access_key_env=str(
                getattr(source, "access_key_env", "R2_ACCESS_KEY_ID") or "R2_ACCESS_KEY_ID"
            ),
            secret_key_env=str(
                getattr(source, "secret_key_env", "R2_SECRET_ACCESS_KEY") or "R2_SECRET_ACCESS_KEY"
            ),
        )
    raise PreviewStorageError(
        "PREVIEW_STORAGE_PROVIDER_UNSUPPORTED",
        "The configured preview storage provider is unsupported.",
    )
