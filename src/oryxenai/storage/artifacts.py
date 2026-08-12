"""Verified, immutable artifact storage for temporary build packs.

The application only needs a tiny object-store boundary here.  Tests use the
in-memory implementation; production uses the configured S3-compatible
endpoint (Cloudflare R2 in the local/deployment configuration).  Neither
implementation logs credentials or exposes them in returned metadata.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol, cast

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict


class ArtifactReference(BaseModel):
    """Safe metadata persisted with a verified temporary artifact."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    bucket: str = ""
    key: str
    sha256: str
    size_bytes: int
    content_type: str = "application/zip"
    expires_at: str
    etag: str = ""


class ArtifactStorageError(Exception):
    """A safe storage error suitable for durable-job retry handling."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}
        super().__init__(message)


class ArtifactStore(Protocol):
    """Minimal store contract used by the Build Preparation packager."""

    async def put_verified(
        self,
        *,
        key: str,
        data: bytes,
        sha256: str,
        expires_at: str,
        content_type: str = "application/zip",
    ) -> ArtifactReference: ...

    async def get_verified(self, reference: ArtifactReference) -> bytes: ...

    async def head(self, reference: ArtifactReference) -> ArtifactReference | None: ...


def _validate_payload(data: bytes, sha256: str) -> None:
    actual = hashlib.sha256(data).hexdigest()
    if actual != sha256:
        raise ArtifactStorageError(
            "ARTIFACT_LOCAL_HASH_MISMATCH",
            "The build pack hash changed before storage.",
            retryable=False,
            details={"expected_sha256": sha256, "actual_sha256": actual},
        )


def _validate_reference(reference: ArtifactReference, data: bytes) -> None:
    actual = hashlib.sha256(data).hexdigest()
    if actual != reference.sha256 or len(data) != reference.size_bytes:
        raise ArtifactStorageError(
            "ARTIFACT_HASH_MISMATCH",
            "Stored build pack failed hash or size verification.",
            details={
                "expected_sha256": reference.sha256,
                "actual_sha256": actual,
                "expected_size_bytes": reference.size_bytes,
                "actual_size_bytes": len(data),
            },
        )


def _parse_expires(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ArtifactStorageError(
            "ARTIFACT_EXPIRY_INVALID",
            "The build pack expiry timestamp is invalid.",
            retryable=False,
        ) from exc
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class MemoryArtifactStore:
    """Deterministic store used by tests and explicitly offline harness runs."""

    def __init__(self) -> None:
        self._objects: dict[str, tuple[ArtifactReference, bytes]] = {}

    async def put_verified(
        self,
        *,
        key: str,
        data: bytes,
        sha256: str,
        expires_at: str,
        content_type: str = "application/zip",
    ) -> ArtifactReference:
        _validate_payload(data, sha256)
        existing = self._objects.get(key)
        if existing is not None:
            reference, stored = existing
            if reference.sha256 != sha256 or stored != data:
                raise ArtifactStorageError(
                    "ARTIFACT_IMMUTABLE_CONFLICT",
                    "An immutable artifact key already contains different bytes.",
                    retryable=False,
                    details={"key": key},
                )
            return reference
        reference = ArtifactReference(
            provider="memory",
            key=key,
            sha256=sha256,
            size_bytes=len(data),
            content_type=content_type,
            expires_at=expires_at,
        )
        self._objects[key] = (reference, bytes(data))
        return reference

    async def get_verified(self, reference: ArtifactReference) -> bytes:
        stored = self._objects.get(reference.key)
        if stored is None:
            raise ArtifactStorageError(
                "ARTIFACT_NOT_FOUND", "The build pack was not found in artifact storage."
            )
        actual_reference, data = stored
        _validate_reference(reference, data)
        if actual_reference.sha256 != reference.sha256:
            raise ArtifactStorageError(
                "ARTIFACT_HASH_MISMATCH", "Artifact metadata does not match the requested pack."
            )
        return bytes(data)

    async def head(self, reference: ArtifactReference) -> ArtifactReference | None:
        stored = self._objects.get(reference.key)
        return stored[0] if stored is not None else None


class S3ArtifactStore:
    """S3-compatible implementation for the configured R2 bucket."""

    def __init__(self, settings: Any) -> None:
        config = settings.artifact_storage
        if not config.endpoint_url or not config.bucket:
            raise ArtifactStorageError(
                "ARTIFACT_STORAGE_NOT_CONFIGURED",
                "Artifact storage is not configured with an endpoint and bucket.",
                retryable=False,
            )
        access_key = os.getenv(config.access_key_env, "")
        secret_key = os.getenv(config.secret_key_env, "")
        if not access_key or not secret_key:
            raise ArtifactStorageError(
                "ARTIFACT_STORAGE_CREDENTIALS_MISSING",
                "Artifact storage credentials are not configured.",
                retryable=False,
            )
        self._bucket = str(config.bucket)
        self._provider = str(config.provider)
        self._client = boto3.client(
            "s3",
            endpoint_url=str(config.endpoint_url),
            region_name=str(config.region),
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    async def put_verified(
        self,
        *,
        key: str,
        data: bytes,
        sha256: str,
        expires_at: str,
        content_type: str = "application/zip",
    ) -> ArtifactReference:
        _validate_payload(data, sha256)
        existing = await self.head(
            ArtifactReference(
                provider=self._provider,
                bucket=self._bucket,
                key=key,
                sha256=sha256,
                size_bytes=len(data),
                expires_at=expires_at,
                content_type=content_type,
            )
        )
        if existing is not None:
            if existing.sha256 != sha256 or existing.size_bytes != len(data):
                raise ArtifactStorageError(
                    "ARTIFACT_IMMUTABLE_CONFLICT",
                    "An immutable artifact key already contains different bytes.",
                    retryable=False,
                    details={"key": key},
                )
            return existing

        metadata = {"sha256": sha256, "expires_at": expires_at}

        def put() -> dict[str, Any]:
            return cast(
                dict[str, Any],
                self._client.put_object(
                    Bucket=self._bucket,
                    Key=key,
                    Body=data,
                    ContentType=content_type,
                    Metadata=metadata,
                ),
            )

        try:
            response = await asyncio.to_thread(put)
        except Exception as exc:
            raise ArtifactStorageError(
                "ARTIFACT_UPLOAD_FAILED", "The build pack could not be uploaded."
            ) from exc
        reference = ArtifactReference(
            provider=self._provider,
            bucket=self._bucket,
            key=key,
            sha256=sha256,
            size_bytes=len(data),
            content_type=content_type,
            expires_at=expires_at,
            etag=str(response.get("ETag", "")).strip('"'),
        )
        verified = await self.head(reference)
        if verified is None or verified.sha256 != sha256 or verified.size_bytes != len(data):
            raise ArtifactStorageError(
                "ARTIFACT_UPLOAD_VERIFY_FAILED",
                "The uploaded build pack failed metadata verification.",
                details={"key": key},
            )
        return verified

    async def get_verified(self, reference: ArtifactReference) -> bytes:
        def get() -> bytes:
            response = self._client.get_object(Bucket=self._bucket, Key=reference.key)
            body = response["Body"]
            try:
                return cast(bytes, body.read())
            finally:
                body.close()

        try:
            data = await asyncio.to_thread(get)
        except ClientError as exc:
            raise ArtifactStorageError(
                "ARTIFACT_NOT_FOUND", "The uploaded build pack could not be read back."
            ) from exc
        except Exception as exc:
            raise ArtifactStorageError(
                "ARTIFACT_READ_FAILED", "The uploaded build pack could not be read back."
            ) from exc
        _validate_reference(reference, data)
        return data

    async def head(self, reference: ArtifactReference) -> ArtifactReference | None:
        def head() -> Mapping[str, Any]:
            return cast(
                Mapping[str, Any],
                self._client.head_object(Bucket=self._bucket, Key=reference.key),
            )

        try:
            response = await asyncio.to_thread(head)
        except ClientError as exc:
            error = exc.response.get("Error", {})
            if str(error.get("Code", "")) in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise ArtifactStorageError(
                "ARTIFACT_HEAD_FAILED", "Artifact storage could not inspect the build pack."
            ) from exc
        except Exception as exc:
            raise ArtifactStorageError(
                "ARTIFACT_HEAD_FAILED", "Artifact storage could not inspect the build pack."
            ) from exc
        metadata = response.get("Metadata", {})
        stored_hash = str(metadata.get("sha256", ""))
        stored_expiry = str(metadata.get("expires_at", reference.expires_at))
        return ArtifactReference(
            provider=self._provider,
            bucket=self._bucket,
            key=reference.key,
            sha256=stored_hash or reference.sha256,
            size_bytes=int(response.get("ContentLength", 0) or 0),
            content_type=str(response.get("ContentType", reference.content_type)),
            expires_at=stored_expiry,
            etag=str(response.get("ETag", "")).strip('"'),
        )


def create_artifact_store(settings: Any) -> ArtifactStore:
    provider = str(getattr(settings.artifact_storage, "provider", "") or "")
    if provider == "memory":
        return MemoryArtifactStore()
    if provider in {"r2_s3", "s3"}:
        return S3ArtifactStore(settings)
    raise ArtifactStorageError(
        "ARTIFACT_STORAGE_PROVIDER_UNSUPPORTED",
        "The configured artifact storage provider is unsupported.",
        retryable=False,
        details={"provider": provider},
    )


def is_expired(reference: ArtifactReference, *, now: datetime | None = None) -> bool:
    return _parse_expires(reference.expires_at) <= (now or datetime.now(UTC))
