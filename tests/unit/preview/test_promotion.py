from __future__ import annotations

import pytest

from oryxenai.agents.code_generator.core.development_schemas import (
    BuildManifest,
    BuildManifestEntry,
    CandidateArtifact,
    PendingPromotion,
)
from oryxenai.preview.promotion import PreviewPromoter
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
