from __future__ import annotations

import hashlib
import json

import pytest

from oryxenai.agents.code_generator.core.development_schemas import (
    BuildManifest,
    BuildManifestEntry,
    CandidateArtifact,
    PendingPromotion,
)
from oryxenai.preview import promotion as promotion_module
from oryxenai.preview.promotion import PreviewPromoter, PromotionError
from oryxenai.storage.preview import MemoryPreviewStorage


@pytest.mark.asyncio
async def test_promotion_redelivery_reuses_immutable_receipt() -> None:
    storage = MemoryPreviewStorage()
    promoter = PreviewPromoter(storage)
    manifest = BuildManifest(
        candidate_identity_hash="identity-a",
        entry_paths=["index.html"],
        entries=[
            BuildManifestEntry(
                path="index.html",
                media_type="text/html",
                size_bytes=18,
                sha256="html-hash",
            )
        ],
        total_bytes=18,
    )
    candidate = CandidateArtifact(
        candidate_id="candidate-a",
        candidate_identity_hash="identity-a",
        build_hash="build-a",
        key="preview/candidates/candidate-a/build-a",
        sha256="artifact-hash",
        size_bytes=18,
        created_at="2026-08-14T00:00:00+00:00",
        expires_at="2026-08-17T00:00:00+00:00",
    )
    pending = PendingPromotion(
        promotion_id="promotion-a",
        candidate=candidate,
        verification_report_hash="report-hash",
        expected_revision=1,
        created_at="2026-08-14T00:00:00+00:00",
    )
    pointer = {
        "candidate_prefix": candidate.key,
        "manifest": manifest.model_dump(mode="json"),
    }

    first = await promoter.promote(
        run_id="run-a",
        host="preview-abcdefghijklmnop",
        pending=pending,
        candidate_pointer=pointer,
        verification_report_hash="report-hash",
    )
    second = await promoter.promote(
        run_id="run-a",
        host="preview-abcdefghijklmnop",
        pending=pending,
        candidate_pointer=pointer,
        verification_report_hash="report-hash",
    )

    assert second.receipt_hash == first.receipt_hash
    assert second.promoted_at == first.promoted_at
    assert second.pointer_etag == first.pointer_etag


@pytest.mark.asyncio
async def test_public_readback_allows_gateway_mount_rewrite_but_hashes_assets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    html = b"<html><head></head><body>verified</body></html>"
    javascript = b"console.log('verified')"
    manifest = BuildManifest(
        candidate_identity_hash="identity-a",
        entry_paths=["index.html", "assets/app.js"],
        entries=[
            BuildManifestEntry(
                path="index.html",
                media_type="text/html",
                size_bytes=len(html),
                sha256=hashlib.sha256(html).hexdigest(),
            ),
            BuildManifestEntry(
                path="assets/app.js",
                media_type="text/javascript",
                size_bytes=len(javascript),
                sha256=hashlib.sha256(javascript).hexdigest(),
            ),
        ],
        total_bytes=len(html) + len(javascript),
    )
    candidate = CandidateArtifact(
        candidate_id="candidate-a",
        candidate_identity_hash="identity-a",
        build_hash="build-a",
        key="preview/candidates/candidate-a/build-a",
        sha256="artifact-hash",
        size_bytes=manifest.total_bytes,
        route_paths=["/", "/about"],
        created_at="2026-08-14T00:00:00+00:00",
        expires_at="2026-08-17T00:00:00+00:00",
    )

    class _Response:
        def __init__(self, content: bytes, content_type: str) -> None:
            self.status_code = 200
            self.content = content
            self.headers = {"content-type": content_type}

    class _Client:
        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def get(self, url: str) -> _Response:
            if url.endswith("app.js"):
                return _Response(javascript, "text/javascript")
            # The gateway adds the nested preview-base metadata to every SPA
            # document response, including route fallbacks.
            return _Response(html + b'<meta name="oryxenai-preview-base">', "text/html")

    monkeypatch.setattr(promotion_module.httpx, "AsyncClient", lambda **_: _Client())
    receipt = await PreviewPromoter(
        MemoryPreviewStorage(),
        preview_base_url="https://preview.example/preview",
        require_readback=True,
    )._default_public_readback(
        "https://preview.example/preview",
        "preview-abcdefghijklmnop",
        candidate,
        manifest,
        "promotion-a",
    )

    assert len(receipt.entries) == 3
    assert any(item.kind == "root" for item in receipt.entries)
    assert any(item.kind == "javascript" for item in receipt.entries)


@pytest.mark.asyncio
async def test_public_readback_failure_restores_previous_active_pointer() -> None:
    storage = MemoryPreviewStorage()
    html = b"<html><head></head><body>candidate</body></html>"
    manifest = BuildManifest(
        candidate_identity_hash="identity-new",
        entry_paths=["index.html"],
        entries=[
            BuildManifestEntry(
                path="index.html",
                media_type="text/html",
                size_bytes=len(html),
                sha256=hashlib.sha256(html).hexdigest(),
            )
        ],
        total_bytes=len(html),
    )
    candidate = CandidateArtifact(
        candidate_id="candidate-new",
        candidate_identity_hash="identity-new",
        build_hash="build-new",
        key="preview/candidates/candidate-new/build-new",
        sha256="artifact-new",
        size_bytes=len(html),
        route_paths=["/"],
        created_at="2026-08-14T00:00:00+00:00",
        expires_at="2026-08-17T00:00:00+00:00",
    )
    await storage.put_immutable(
        key=f"{candidate.key}/dist/index.html", data=html, content_type="text/html"
    )
    host = "preview-abcdefghijklmnop"
    previous_pointer = {
        "schema_version": "code-generator-active-preview-v1",
        "candidate_id": "candidate-old",
        "candidate_prefix": "preview/candidates/candidate-old/build-old",
    }
    await storage.put_conditional(
        key=f"preview/hosts/{host}/active.json",
        data=(json.dumps(previous_pointer) + "\n").encode(),
        content_type="application/json",
        expected_etag=None,
    )

    async def fail_readback(*_args: object) -> object:
        raise RuntimeError("gateway unavailable")

    promoter = PreviewPromoter(storage, require_readback=True, public_readback=fail_readback)
    pending = await promoter.create_pending(
        run_id="run-new",
        host=host,
        artifact=candidate,
        verification_report_hash="report-new",
        expected_revision=2,
    )
    pointer = {
        "candidate_prefix": candidate.key,
        "manifest": manifest.model_dump(mode="json"),
    }

    with pytest.raises(PromotionError) as exc_info:
        await promoter.promote(
            run_id="run-new",
            host=host,
            pending=pending,
            candidate_pointer=pointer,
            verification_report_hash="report-new",
        )

    assert exc_info.value.code == "PREVIEW_PUBLIC_READBACK_FAILED"
    restored = await storage.get(f"preview/hosts/{host}/active.json")
    assert restored is not None
    assert json.loads(restored[1]) == previous_pointer


@pytest.mark.asyncio
async def test_store_candidate_reads_back_every_immutable_object(tmp_path) -> None:
    html = b"<html>verified</html>"
    javascript = b"console.log('verified')"
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_bytes(html)
    (dist / "assets" / "app.js").write_bytes(javascript)
    manifest = BuildManifest(
        candidate_identity_hash="identity-a",
        entry_paths=["index.html", "assets/app.js"],
        entries=[
            BuildManifestEntry(
                path="index.html",
                media_type="text/html",
                size_bytes=len(html),
                sha256=hashlib.sha256(html).hexdigest(),
            ),
            BuildManifestEntry(
                path="assets/app.js",
                media_type="text/javascript",
                size_bytes=len(javascript),
                sha256=hashlib.sha256(javascript).hexdigest(),
            ),
        ],
        total_bytes=len(html) + len(javascript),
    )

    class CountingStorage(MemoryPreviewStorage):
        def __init__(self) -> None:
            super().__init__()
            self.reads: list[str] = []

        async def get(self, key: str):
            self.reads.append(key)
            return await super().get(key)

    storage = CountingStorage()
    identity = type("Identity", (), {"identity_hash": "identity-a"})()
    await PreviewPromoter(storage).store_candidate(
        candidate_id="candidate-a",
        host="preview-abcdefghijklmnop",
        identity=identity,
        manifest=manifest,
        dist_dir=dist,
        verification_report={"status": "passed"},
    )

    assert "preview/candidates/candidate-a/" in storage.reads[0]
    assert len([key for key in storage.reads if "/dist/" in key]) == 2
    assert len([key for key in storage.reads if key.startswith("preview/verification/")]) == 1
