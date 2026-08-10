"""Deployment-independent artifact storage.

Production uses one private S3-compatible store (Cloudflare R2 by default).
Tests inject MemoryArtifactStore; no persistent local production fallback is
provided because app and worker are separate instances.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class StoredArtifact:
    object_key: str
    etag: str
    sha256: str
    size_bytes: int
    expires_at: datetime
    content_type: str = "application/zip"


class ArtifactStore(Protocol):
    async def put(
        self, object_key: str, path: Path, *, expires_at: datetime, metadata: dict[str, str]
    ) -> StoredArtifact: ...
    async def head(self, object_key: str) -> StoredArtifact | None: ...
    async def download(self, object_key: str, destination: Path) -> StoredArtifact: ...
    async def delete(self, object_key: str) -> None: ...


class ArtifactStoreError(RuntimeError):
    pass


class MemoryArtifactStore:
    """Deterministic fake used by unit/API tests."""

    def __init__(self, *, lifecycle: bool = True) -> None:
        self.objects: dict[str, tuple[bytes, StoredArtifact, dict[str, str]]] = {}
        self.lifecycle = lifecycle

    async def put(
        self, object_key: str, path: Path, *, expires_at: datetime, metadata: dict[str, str]
    ) -> StoredArtifact:
        data = path.read_bytes()
        if not self.lifecycle:
            raise ArtifactStoreError("artifact lifecycle is not configured")
        digest = hashlib.sha256(data).hexdigest()
        artifact = StoredArtifact(object_key, digest[:16], digest, len(data), expires_at)
        self.objects[object_key] = (data, artifact, dict(metadata))
        return artifact

    async def head(self, object_key: str) -> StoredArtifact | None:
        item = self.objects.get(object_key)
        if item is None:
            return None
        _, artifact, _ = item
        if datetime.now(UTC) >= artifact.expires_at:
            self.objects.pop(object_key, None)
            return None
        return artifact

    async def download(self, object_key: str, destination: Path) -> StoredArtifact:
        item = self.objects.get(object_key)
        if item is None:
            raise ArtifactStoreError("artifact not found")
        data, artifact, _ = item
        if datetime.now(UTC) >= artifact.expires_at:
            self.objects.pop(object_key, None)
            raise ArtifactStoreError("artifact expired")
        destination.write_bytes(data)
        return artifact

    async def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


_MEMORY_STORE = MemoryArtifactStore()


def memory_artifact_store() -> MemoryArtifactStore:
    """Return the process-local fake used only by tests/dev fixtures."""
    return _MEMORY_STORE


class R2ArtifactStore:
    def __init__(
        self,
        *,
        endpoint_url: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str = "auto",
        require_lifecycle: bool = True,
        default_ttl_days: int = 3,
    ) -> None:
        try:
            import boto3  # type: ignore[import-untyped]
            from botocore.config import Config  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ArtifactStoreError("boto3 is required for R2 artifact storage") from exc
        if not endpoint_url or not bucket or not access_key or not secret_key:
            raise ArtifactStoreError("R2 artifact storage is not configured")
        self.bucket = bucket
        self.require_lifecycle = require_lifecycle
        self.default_ttl = timedelta(days=max(default_ttl_days, 1))
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(
                retries={"max_attempts": 3, "mode": "standard"}, connect_timeout=15, read_timeout=30
            ),
        )

    async def put(
        self, object_key: str, path: Path, *, expires_at: datetime, metadata: dict[str, str]
    ) -> StoredArtifact:
        return await asyncio.to_thread(self._put_sync, object_key, path, expires_at, metadata)

    def _put_sync(
        self, object_key: str, path: Path, expires_at: datetime, metadata: dict[str, str]
    ) -> StoredArtifact:
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        try:
            self._client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=data,
                ContentType="application/zip",
                CacheControl="no-store",
                Metadata={**metadata, "bundle-sha256": digest},
                IfNoneMatch="*",
            )
            response = self._client.head_object(Bucket=self.bucket, Key=object_key)
        except Exception as exc:
            raise ArtifactStoreError("R2 artifact upload failed") from exc
        expiration = response.get("Expiration")
        if not expiration and self.require_lifecycle:
            from contextlib import suppress

            with suppress(Exception):
                self._client.delete_object(Bucket=self.bucket, Key=object_key)
            raise ArtifactStoreError("R2 lifecycle expiration was not returned for the artifact")
        expires = _parse_expiration(expiration, expires_at) if expiration else expires_at
        if expires < expires_at - timedelta(minutes=5):
            raise ArtifactStoreError("R2 lifecycle expiry is earlier than configured TTL")
        return StoredArtifact(
            object_key,
            str(response.get("ETag", "")).strip('"'),
            digest,
            len(data),
            min(expires, expires_at),
        )

    async def head(self, object_key: str) -> StoredArtifact | None:
        return await asyncio.to_thread(self._head_sync, object_key)

    def _head_sync(self, object_key: str) -> StoredArtifact | None:
        try:
            response = self._client.head_object(Bucket=self.bucket, Key=object_key)
        except Exception as exc:
            if "404" in str(exc) or "Not Found" in str(exc):
                return None
            raise ArtifactStoreError("R2 artifact verification failed") from exc
        digest = str((response.get("Metadata") or {}).get("bundle-sha256", ""))
        if not digest:
            raise ArtifactStoreError("R2 artifact metadata is incomplete")
        expiration = response.get("Expiration")
        expires = (
            _parse_expiration(expiration, datetime.now(UTC) + self.default_ttl)
            if expiration
            else datetime.now(UTC) + self.default_ttl
        )
        return StoredArtifact(
            object_key,
            str(response.get("ETag", "")).strip('"'),
            digest,
            int(response.get("ContentLength", 0)),
            expires,
        )

    async def download(self, object_key: str, destination: Path) -> StoredArtifact:
        return await asyncio.to_thread(self._download_sync, object_key, destination)

    def _download_sync(self, object_key: str, destination: Path) -> StoredArtifact:
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=object_key)
            data = response["Body"].read()
        except Exception as exc:
            raise ArtifactStoreError("R2 artifact download failed") from exc
        destination.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        metadata = response.get("Metadata") or {}
        if metadata.get("bundle-sha256") != digest:
            raise ArtifactStoreError("downloaded artifact hash does not match metadata")
        expires = _parse_expiration(
            response.get("Expiration"), datetime.now(UTC) + self.default_ttl
        )
        return StoredArtifact(
            object_key, str(response.get("ETag", "")).strip('"'), digest, len(data), expires
        )

    async def delete(self, object_key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self.bucket, Key=object_key)


def _parse_expiration(value: object, fallback: datetime) -> datetime:
    if not isinstance(value, str):
        return fallback
    # S3 commonly returns `expiry-date="...", rule-id="..."`.
    raw = value.split("expiry-date=", 1)[-1].split(",", 1)[0].strip().strip('"')
    try:
        return datetime.strptime(raw, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=UTC)
    except ValueError:
        return fallback


def build_r2_store(config: object, *, ttl_days: int = 3) -> ArtifactStore:
    endpoint_url = str(getattr(config, "endpoint_url", "") or "")
    bucket = str(getattr(config, "bucket", "") or "")
    access_env = str(getattr(config, "access_key_env", "R2_ACCESS_KEY_ID"))
    secret_env = str(getattr(config, "secret_key_env", "R2_SECRET_ACCESS_KEY"))
    return R2ArtifactStore(
        endpoint_url=endpoint_url,
        bucket=bucket,
        access_key=os.environ.get(access_env, ""),
        secret_key=os.environ.get(secret_env, ""),
        region=str(getattr(config, "region", "auto") or "auto"),
        require_lifecycle=bool(getattr(config, "require_lifecycle", True)),
        default_ttl_days=ttl_days,
    )
