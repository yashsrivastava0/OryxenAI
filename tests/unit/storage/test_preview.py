from __future__ import annotations

import hashlib

import botocore.exceptions
import pytest

from oryxenai.storage import preview as preview_module
from oryxenai.storage.preview import MemoryPreviewStorage, PreviewStorageError, S3PreviewStorage


@pytest.mark.asyncio
async def test_preview_storage_is_immutable_and_conditional() -> None:
    storage = MemoryPreviewStorage()
    first = await storage.put_immutable(
        key="preview/candidate/index.html", data=b"one", content_type="text/html"
    )
    assert first.etag
    assert (
        await storage.put_immutable(
            key="preview/candidate/index.html", data=b"one", content_type="text/html"
        )
        == first
    )
    with pytest.raises(PreviewStorageError, match="different bytes"):
        await storage.put_immutable(
            key="preview/candidate/index.html", data=b"two", content_type="text/html"
        )
    pointer = await storage.put_conditional(
        key="preview/hosts/preview-abcdefghijklmnop/active.json",
        data=b"{}",
        content_type="application/json",
        expected_etag=None,
    )
    with pytest.raises(PreviewStorageError, match="changed concurrently"):
        await storage.put_conditional(
            key="preview/hosts/preview-abcdefghijklmnop/active.json",
            data=b'{"new":true}',
            content_type="application/json",
            expected_etag="wrong",
        )
    updated = await storage.put_conditional(
        key="preview/hosts/preview-abcdefghijklmnop/active.json",
        data=b'{"new":true}',
        content_type="application/json",
        expected_etag=pointer.etag,
    )
    assert updated.etag != pointer.etag


class _FakeBody:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def close(self) -> None:
        return None


class _FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, dict[str, object]] = {}

    @staticmethod
    def _error(code: str) -> botocore.exceptions.ClientError:
        return botocore.exceptions.ClientError({"Error": {"Code": code}}, "PreviewObject")

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        del Bucket
        item = self.objects.get(Key)
        if item is None:
            raise self._error("404")
        return {
            "Metadata": item["metadata"],
            "ContentLength": len(item["data"]),
            "ContentType": item["content_type"],
            "ETag": item["etag"],
        }

    def put_object(self, **kwargs: object) -> dict[str, str]:
        key = str(kwargs["Key"])
        existing = self.objects.get(key)
        if kwargs.get("IfNoneMatch") == "*" and existing is not None:
            raise self._error("412")
        if kwargs.get("IfMatch") and (existing is None or existing["etag"] != kwargs["IfMatch"]):
            raise self._error("412")
        data = bytes(kwargs["Body"])
        etag = hashlib.md5(data).hexdigest()  # noqa: S324 - test-only S3 ETag
        self.objects[key] = {
            "data": data,
            "metadata": kwargs["Metadata"],
            "content_type": kwargs["ContentType"],
            "etag": f'"{etag}"',
        }
        return {"ETag": f'"{etag}"'}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        del Bucket
        item = self.objects.get(Key)
        if item is None:
            raise self._error("NoSuchKey")
        return {
            "Metadata": item["metadata"],
            "ContentLength": len(item["data"]),
            "ContentType": item["content_type"],
            "ETag": item["etag"],
            "Body": _FakeBody(item["data"]),
        }

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        del Bucket
        self.objects.pop(Key, None)


@pytest.mark.asyncio
async def test_s3_preview_storage_scopes_keys_and_verifies_bytes(monkeypatch) -> None:
    fake = _FakeS3Client()
    monkeypatch.setenv("TEST_PREVIEW_ACCESS", "access")
    monkeypatch.setenv("TEST_PREVIEW_SECRET", "secret")
    monkeypatch.setattr(preview_module.boto3, "client", lambda *_args, **_kwargs: fake)
    storage = S3PreviewStorage(
        provider="r2_s3",
        endpoint_url="https://example.invalid",
        bucket="preview-bucket",
        region="auto",
        prefix="hosted",
        access_key_env="TEST_PREVIEW_ACCESS",
        secret_key_env="TEST_PREVIEW_SECRET",  # noqa: S106 - test-only env name
    )

    stored = await storage.put_immutable(
        key="preview/candidate/index.html", data=b"<main>ok</main>", content_type="text/html"
    )
    assert stored.key == "preview/candidate/index.html"
    assert "hosted/preview/candidate/index.html" in fake.objects
    assert (await storage.get(stored.key))[1] == b"<main>ok</main>"

    pointer = await storage.put_conditional(
        key="preview/hosts/preview-abcdefghijklmnop/active.json",
        data=b"one",
        content_type="application/json",
        expected_etag=None,
    )
    with pytest.raises(PreviewStorageError, match="changed concurrently"):
        await storage.put_conditional(
            key=pointer.key,
            data=b"two",
            content_type="application/json",
            expected_etag="stale",
        )
