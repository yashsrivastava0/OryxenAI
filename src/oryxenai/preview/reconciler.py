"""Idempotent recovery helpers for pending standalone preview promotions."""

from __future__ import annotations

from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import BuildManifest, PendingPromotion
from oryxenai.preview.promotion import PreviewPromoter
from oryxenai.storage.preview import PreviewStorage


async def reconcile_pending_promotion(
    *,
    storage: PreviewStorage,
    run_id: str,
    host: str,
    pending: PendingPromotion,
    manifest: BuildManifest,
    preview_base_url: str,
) -> Any:
    """Resume the receipt/pointer boundary without inventing new bytes."""

    promoter = PreviewPromoter(storage, preview_base_url=preview_base_url)
    pointer = {
        "candidate_prefix": pending.candidate.key,
        "manifest": manifest.model_dump(mode="json"),
    }
    return await promoter.promote(
        run_id=run_id,
        host=host,
        pending=pending,
        candidate_pointer=pointer,
        verification_report_hash=pending.verification_report_hash,
    )
