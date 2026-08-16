from __future__ import annotations

import hashlib
import json

import httpx
import pytest
from httpx import ASGITransport

from oryxenai.preview.gateway import create_preview_app
from oryxenai.storage.preview import MemoryPreviewStorage


@pytest.mark.asyncio
async def test_gateway_serves_active_spa_and_returns_asset_404() -> None:
    storage = MemoryPreviewStorage()
    html = b"<main>verified</main>"
    await storage.put_immutable(
        key="preview/candidates/candidate-a/build-a/dist/index.html",
        data=html,
        content_type="text/html",
    )
    receipt = b'{"build_hash":"build-a","candidate_id":"candidate-a","candidate_identity_hash":"identity-a"}\n'
    receipt_ref = await storage.put_immutable(
        key="preview/receipts/promotion-a.json",
        data=receipt,
        content_type="application/json",
    )
    pointer = {
        "receipt_key": "preview/receipts/promotion-a.json",
        "receipt_hash": receipt_ref.sha256,
        "candidate_prefix": "preview/candidates/candidate-a/build-a",
        "build_hash": "build-a",
        "candidate_id": "candidate-a",
        "candidate_identity_hash": "identity-a",
        "manifest": {
            "entries": [
                {
                    "path": "index.html",
                    "sha256": hashlib.sha256(html).hexdigest(),
                    "media_type": "text/html",
                }
            ]
        },
    }
    await storage.put_conditional(
        key="preview/hosts/preview-abcdefghijklmnop/active.json",
        data=(json.dumps(pointer, separators=(",", ":")) + "\n").encode(),
        content_type="application/json",
        expected_etag=None,
    )
    app = create_preview_app(storage)
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/preview/preview-abcdefghijklmnop/projects")
        missing = await client.get("/preview/preview-abcdefghijklmnop/assets/missing.js")
    assert response.status_code == 200
    assert response.text == html.decode()
    assert response.headers["content-security-policy"]
    assert missing.status_code == 404
