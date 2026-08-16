from __future__ import annotations

import pytest

from oryxenai.storage.preview import MemoryPreviewStorage, PreviewStorageError


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
