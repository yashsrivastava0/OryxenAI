from __future__ import annotations

import hashlib
import json

import httpx
import pytest
from httpx import ASGITransport

from oryxenai.preview.gateway import (
    _rewrite_preview_html_urls,
    create_candidate_app,
    create_preview_app,
)
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
    app = create_preview_app(storage, embed_origins=["https://app.example"])
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/preview/preview-abcdefghijklmnop/projects")
        missing = await client.get("/preview/preview-abcdefghijklmnop/assets/missing.js")
    assert response.status_code == 200
    assert response.text == html.decode()
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors https://app.example" in response.headers["content-security-policy"]
    assert "127.0.0.1:8000" not in response.headers["content-security-policy"]
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_gateway_has_gateway_specific_health_endpoints() -> None:
    app = create_preview_app(MemoryPreviewStorage())
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        live = await client.get("/health/live")
        ready = await client.get("/health/ready")
    assert live.status_code == 200
    assert ready.status_code == 200
    assert live.json()["service"] == "preview-gateway"


@pytest.mark.asyncio
async def test_gateway_injects_mount_metadata_for_nested_asset_urls() -> None:
    storage = MemoryPreviewStorage()
    html = b"<!doctype html><html><head><title>Portfolio</title></head><body><div id='root'></div></body></html>"
    await storage.put_immutable(
        key="preview/candidates/candidate-b/build-b/dist/index.html",
        data=html,
        content_type="text/html",
    )
    receipt = b'{"build_hash":"build-b","candidate_id":"candidate-b","candidate_identity_hash":"identity-b"}\n'
    receipt_ref = await storage.put_immutable(
        key="preview/receipts/promotion-b.json", data=receipt, content_type="application/json"
    )
    pointer = {
        "receipt_key": "preview/receipts/promotion-b.json",
        "receipt_hash": receipt_ref.sha256,
        "candidate_prefix": "preview/candidates/candidate-b/build-b",
        "build_hash": "build-b",
        "candidate_id": "candidate-b",
        "candidate_identity_hash": "identity-b",
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
        key="preview/hosts/preview-bbbbbbbbbbbbbbbb/active.json",
        data=(json.dumps(pointer, separators=(",", ":")) + "\n").encode(),
        content_type="application/json",
        expected_etag=None,
    )
    app = create_preview_app(storage)
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/preview/preview-bbbbbbbbbbbbbbbb/")
    assert response.status_code == 200
    assert (
        'name="oryxenai-preview-base" content="/preview/preview-bbbbbbbbbbbbbbbb/"' in response.text
    )
    assert (
        '<script src="/preview/preview-bbbbbbbbbbbbbbbb/__oryxenai/preview-bridge.js" defer></script>'
        in response.text
    )


@pytest.mark.asyncio
async def test_active_gateway_rewrites_assets_for_nested_spa_routes() -> None:
    storage = MemoryPreviewStorage()
    html = (
        b"<!doctype html><html><head>"
        b'<script type="module" src="./assets/app.js"></script>'
        b'<link rel="stylesheet" href="/assets/app.css">'
        b"</head><body><main>active</main></body></html>"
    )
    javascript = b"console.log('active')"
    stylesheet = b"main { color: red; }"
    prefix = "preview/candidates/candidate-active/build-active"
    for path, data, content_type in (
        ("index.html", html, "text/html"),
        ("assets/app.js", javascript, "text/javascript"),
        ("assets/app.css", stylesheet, "text/css"),
    ):
        await storage.put_immutable(
            key=f"{prefix}/dist/{path}", data=data, content_type=content_type
        )
    receipt = json.dumps(
        {
            "run_id": "run-active",
            "build_hash": "build-active",
            "candidate_id": "candidate-active",
            "candidate_identity_hash": "identity-active",
        },
        separators=(",", ":"),
    ).encode()
    receipt_ref = await storage.put_immutable(
        key="preview/receipts/active.json", data=receipt, content_type="application/json"
    )
    manifest_entries = [
        {
            "path": path,
            "sha256": hashlib.sha256(data).hexdigest(),
            "media_type": content_type,
        }
        for path, data, content_type in (
            ("index.html", html, "text/html"),
            ("assets/app.js", javascript, "text/javascript"),
            ("assets/app.css", stylesheet, "text/css"),
        )
    ]
    pointer = {
        "receipt_key": "preview/receipts/active.json",
        "receipt_hash": receipt_ref.sha256,
        "candidate_prefix": prefix,
        "build_hash": "build-active",
        "candidate_id": "candidate-active",
        "candidate_identity_hash": "identity-active",
        "manifest": {"entries": manifest_entries},
    }
    host = "preview-cccccccccccccccc"
    await storage.put_conditional(
        key=f"preview/hosts/{host}/active.json",
        data=(json.dumps(pointer, separators=(",", ":")) + "\n").encode(),
        content_type="application/json",
        expected_etag=None,
    )
    app = create_preview_app(storage)
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        nested = await client.get(f"/preview/{host}/work/project")
        script = await client.get(f"/preview/{host}/assets/app.js")
        bridge = await client.get(f"/preview/{host}/__oryxenai/preview-bridge.js")
        missing = await client.get(f"/preview/{host}/assets/missing.js")
    assert nested.status_code == 200
    assert f'src="/preview/{host}/assets/app.js"' in nested.text
    assert 'href="/preview/preview-cccccccccccccccc/assets/app.css"' in nested.text
    assert script.status_code == 200
    assert script.text == "console.log('active')"
    assert bridge.status_code == 200
    assert '"preview:init"' in bridge.text
    assert "preview:ready" in bridge.text
    assert bridge.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert missing.status_code == 404


def test_gateway_rewrites_entry_assets_to_the_mount_root() -> None:
    html = (
        b'<script type="module" src="./assets/app.js"></script>'
        b'<link rel="stylesheet" href="/assets/app.css">'
        b'<link rel="modulepreload" href="assets/chunk.js">'
        b'<img srcset="./assets/image-480.webp 480w, /assets/image.webp 1280w">'
    )
    rewritten = _rewrite_preview_html_urls(html, "/preview/host-abcdefghijklmnop/").decode()
    assert 'src="/preview/host-abcdefghijklmnop/assets/app.js"' in rewritten
    assert 'href="/preview/host-abcdefghijklmnop/assets/app.css"' in rewritten
    assert 'href="/preview/host-abcdefghijklmnop/assets/chunk.js"' in rewritten
    assert (
        'srcset="/preview/host-abcdefghijklmnop/assets/image-480.webp 480w, '
        '/preview/host-abcdefghijklmnop/assets/image.webp 1280w"'
    ) in rewritten


def test_gateway_keeps_external_and_fragment_urls_unchanged() -> None:
    html = (
        b'<script src="https://cdn.example/app.js"></script>'
        b'<img src="data:image/svg+xml;base64,abc">'
        b'<link href="#local">'
    )
    assert _rewrite_preview_html_urls(html, "/preview/host/") == html


@pytest.mark.asyncio
async def test_candidate_gateway_serves_assets_under_the_exact_nested_mount(tmp_path) -> None:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(
        "<!doctype html><html><head>"
        "<script type='module' src='./assets/app.js'></script>"
        "</head><body><div id='root'></div></body></html>",
        encoding="utf-8",
    )
    (dist / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    header_value = "verify-token"
    app = create_candidate_app(
        dist,
        token=header_value,
        mount_prefix="/preview/host-abcdefghijklmnop/",
    )
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers = {"X-Preview-Verify-Token": header_value}
        page = await client.get("/preview/host-abcdefghijklmnop/", headers=headers)
        nested = await client.get("/preview/host-abcdefghijklmnop/work/project", headers=headers)
        asset = await client.get("/preview/host-abcdefghijklmnop/assets/app.js", headers=headers)
    assert page.status_code == 200
    assert 'content="/preview/host-abcdefghijklmnop/"' in page.text
    assert nested.status_code == 200
    assert "src='/preview/host-abcdefghijklmnop/assets/app.js'" in nested.text
    assert asset.status_code == 200
    assert asset.text == "console.log('ok')"


@pytest.mark.asyncio
async def test_public_candidate_gateway_requires_capability_and_supports_nested_routes() -> None:
    storage = MemoryPreviewStorage()
    token = "A" * 32
    candidate_id = "candidate-test"
    build_hash = "a" * 64
    html = (
        b"<!doctype html><html><head>"
        b'<script type="module" src="./assets/app.js"></script>'
        b"</head><body>candidate</body></html>"
    )
    javascript = b"console.log('candidate')"
    manifest = {
        "schema_version": "preview-build-manifest-v1",
        "candidate_identity_hash": "identity-test",
        "entry_paths": ["index.html", "assets/app.js"],
        "entries": [
            {
                "path": "index.html",
                "media_type": "text/html",
                "size_bytes": len(html),
                "sha256": hashlib.sha256(html).hexdigest(),
            },
            {
                "path": "assets/app.js",
                "media_type": "text/javascript",
                "size_bytes": len(javascript),
                "sha256": hashlib.sha256(javascript).hexdigest(),
            },
        ],
        "total_bytes": len(html) + len(javascript),
    }
    prefix = f"preview/candidates/{candidate_id}/{build_hash}"
    await storage.put_immutable(
        key=f"{prefix}/dist/index.html", data=html, content_type="text/html"
    )
    await storage.put_immutable(
        key=f"{prefix}/dist/assets/app.js", data=javascript, content_type="text/javascript"
    )
    manifest_bytes = (
        json.dumps(
            {
                "schema_version": "preview-candidate-manifest-v1",
                "candidate_id": candidate_id,
                "candidate_identity_hash": "identity-test",
                "build_hash": build_hash,
                "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                "expires_at": "2099-01-01T00:00:00+00:00",
                "manifest": manifest,
            },
            separators=(",", ":"),
        )
        + "\n"
    ).encode()
    await storage.put_immutable(
        key=f"{prefix}/manifest.json", data=manifest_bytes, content_type="application/json"
    )
    app = create_preview_app(
        storage,
        route_prefix="/candidate-preview",
        embed_origins=["https://app.example"],
    )
    base = f"/candidate-preview/candidate/{token}/{candidate_id}/{build_hash}"
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        page = await client.get(f"{base}/")
        nested = await client.get(f"{base}/about")
        asset = await client.get(f"{base}/assets/app.js")
        denied = await client.get(
            f"/candidate-preview/candidate/{'B' * 32}/{candidate_id}/{build_hash}/"
        )
    assert page.status_code == 200
    assert 'content="/candidate-preview/candidate/' in page.text
    assert nested.status_code == 200
    assert f'src="{base}/assets/app.js"' in nested.text
    assert asset.status_code == 200
    assert asset.text == "console.log('candidate')"
    assert denied.status_code == 404
