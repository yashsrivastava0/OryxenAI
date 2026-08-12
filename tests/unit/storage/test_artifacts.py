from __future__ import annotations

import hashlib
import io
from typing import Any

import pytest
from botocore.exceptions import ClientError

from oryxenai.core.settings import Settings
from oryxenai.storage.artifacts import S3ArtifactStore


class _FakeS3:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, dict[str, str]]] = {}

    def put_object(self, **kwargs: Any) -> dict[str, str]:
        self.objects[kwargs["Key"]] = (kwargs["Body"], kwargs["Metadata"])
        return {"ETag": '"fake-etag"'}

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        data, metadata = self.objects[Key]
        return {
            "Metadata": metadata,
            "ContentLength": len(data),
            "ContentType": "application/zip",
            "ETag": '"fake-etag"',
        }

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        data, _metadata = self.objects[Key]
        return {"Body": io.BytesIO(data)}


@pytest.mark.asyncio
async def test_s3_compatible_store_uploads_and_reads_back_verified_bytes(monkeypatch) -> None:
    fake = _FakeS3()
    monkeypatch.setenv("TEST_R2_ACCESS", "access")
    monkeypatch.setenv("TEST_R2_SECRET", "secret")
    settings = Settings()
    settings.artifact_storage.provider = "r2_s3"
    settings.artifact_storage.endpoint_url = "https://example.invalid"
    settings.artifact_storage.bucket = "test-bucket"
    settings.artifact_storage.access_key_env = "TEST_R2_ACCESS"
    settings.artifact_storage.secret_key_env = "TEST_R2_SECRET"  # noqa: S105 - env-var name
    monkeypatch.setattr(
        "oryxenai.storage.artifacts.boto3.client",
        lambda *args, **kwargs: fake,
    )

    store = S3ArtifactStore(settings)
    data = b"verified zip bytes"
    reference = await store.put_verified(
        key="temporary/test.zip",
        data=data,
        sha256=hashlib.sha256(data).hexdigest(),
        expires_at="2099-01-01T00:00:00+00:00",
    )

    assert reference.provider == "r2_s3"
    assert reference.size_bytes == len(data)
    assert await store.get_verified(reference) == data
    head = await store.head(reference)
    assert head is not None
    assert head.sha256 == reference.sha256
