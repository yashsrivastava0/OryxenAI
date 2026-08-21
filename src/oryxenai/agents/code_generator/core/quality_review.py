"""Deterministic validation for hash-bound whole-site quality receipts."""

from __future__ import annotations

from oryxenai.agents.code_generator.core.development_schemas import QualityReviewReceiptV1


class QualityReviewError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def validate_quality_review_receipt(
    receipt: QualityReviewReceiptV1,
    *,
    source_hash: str,
    plan_hash: str,
    context_hash: str,
) -> QualityReviewReceiptV1:
    """Reject missing or stale review evidence before source promotion."""

    if receipt.source_hash != source_hash:
        raise QualityReviewError(
            "QUALITY_SOURCE_STALE", "The quality review is for a different source hash."
        )
    if receipt.plan_hash != plan_hash:
        raise QualityReviewError(
            "QUALITY_PLAN_STALE", "The quality review is for a different plan hash."
        )
    if receipt.context_hash != context_hash:
        raise QualityReviewError(
            "QUALITY_CONTEXT_STALE", "The quality review is for a different generation context."
        )
    if not receipt.accepted:
        raise QualityReviewError(
            "QUALITY_REVIEW_REJECTED", "The whole-site quality review was not accepted."
        )
    return receipt


__all__ = ["QualityReviewError", "validate_quality_review_receipt"]
