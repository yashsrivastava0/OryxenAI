"""Deterministic validation for hash-bound whole-site quality receipts."""

from __future__ import annotations

import hashlib
import json

from oryxenai.agents.code_generator.core.development_schemas import (
    QualityReviewDraftV1,
    QualityReviewReceiptV1,
    QualityReviewReceiptV2,
)


class QualityReviewError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def validate_quality_review_receipt(
    receipt: QualityReviewReceiptV2 | QualityReviewReceiptV1,
    *,
    source_manifest_hash: str = "",
    plan_hash: str = "",
    realization_hash: str = "",
    review_context_hash: str = "",
    quality_gate_version: str = "",
    # Compatibility aliases used by the pre-v4 development harness.  They
    # are intentionally accepted only on the legacy receipt branch below.
    source_hash: str = "",
    context_hash: str = "",
) -> QualityReviewReceiptV2 | QualityReviewReceiptV1:
    """Reject missing or stale review evidence before source promotion."""

    if isinstance(receipt, QualityReviewReceiptV1):
        expected_source = source_hash or source_manifest_hash
        if not expected_source or not plan_hash or not context_hash:
            raise QualityReviewError(
                "QUALITY_BINDING_MISSING",
                "The legacy quality review is missing a complete source, plan, and context binding.",
            )
        if expected_source and receipt.source_hash != expected_source:
            raise QualityReviewError(
                "QUALITY_SOURCE_STALE", "The quality review is for a different source hash."
            )
        if plan_hash and receipt.plan_hash != plan_hash:
            raise QualityReviewError(
                "QUALITY_PLAN_STALE", "The quality review is for a different plan hash."
            )
        if context_hash and receipt.context_hash != context_hash:
            raise QualityReviewError(
                "QUALITY_CONTEXT_STALE", "The quality review is for a different context hash."
            )
        if not receipt.accepted:
            raise QualityReviewError(
                "QUALITY_REVIEW_REJECTED", "The whole-site quality review was not accepted."
            )
        return receipt
    if receipt.source_manifest_hash != source_manifest_hash:
        raise QualityReviewError(
            "QUALITY_SOURCE_STALE", "The quality review is for a different source hash."
        )
    if receipt.plan_hash != plan_hash:
        raise QualityReviewError(
            "QUALITY_PLAN_STALE", "The quality review is for a different plan hash."
        )
    if receipt.realization_hash != realization_hash:
        raise QualityReviewError(
            "QUALITY_REALIZATION_STALE",
            "The quality review is for a different design-realization contract.",
        )
    if review_context_hash and receipt.review_context_hash != review_context_hash:
        raise QualityReviewError(
            "QUALITY_CONTEXT_STALE", "The quality review is for a different review context."
        )
    if receipt.quality_gate_version != quality_gate_version:
        raise QualityReviewError(
            "QUALITY_GATE_STALE", "The quality review used a different quality-gate version."
        )
    if not receipt.accepted:
        raise QualityReviewError(
            "QUALITY_REVIEW_REJECTED", "The whole-site quality review was not accepted."
        )
    return receipt


def stamp_quality_review_receipt(
    draft: QualityReviewDraftV1,
    *,
    source_manifest_hash: str,
    plan_hash: str,
    realization_hash: str,
    review_context_hash: str,
    response_id: str,
    quality_gate_version: str,
) -> QualityReviewReceiptV2:
    """Compute acceptance and bind the provider draft to immutable host evidence."""

    accepted = min(
        draft.hierarchy_score,
        draft.composition_score,
        draft.typography_score,
        draft.resource_fit_score,
        draft.motion_score,
    ) >= 4 and not any(item.severity == "blocking" for item in draft.findings)
    return QualityReviewReceiptV2(
        source_manifest_hash=source_manifest_hash,
        plan_hash=plan_hash,
        realization_hash=realization_hash,
        review_context_hash=review_context_hash,
        response_id=response_id,
        review_hash=hashlib.sha256(
            json.dumps(
                draft.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode()
        ).hexdigest(),
        quality_gate_version=quality_gate_version,
        hierarchy_score=draft.hierarchy_score,
        composition_score=draft.composition_score,
        typography_score=draft.typography_score,
        resource_fit_score=draft.resource_fit_score,
        motion_score=draft.motion_score,
        score_evidence=list(draft.score_evidence),
        findings=list(draft.findings),
        advisory_observations=list(draft.advisory_observations),
        accepted=accepted,
    )


def rebind_quality_review_receipt_source(
    receipt: QualityReviewReceiptV2,
    *,
    source_manifest_hash: str,
) -> QualityReviewReceiptV2:
    """Re-stamp a receipt after a deterministic host-only source rewrite.

    A host normalization may change the source manifest without changing the
    reviewed creative output.  Rebinding is deliberately limited to the
    source hash and recomputes the receipt hash through the same schema
    validator; the model's findings, scores, and review identity remain
    unchanged.
    """

    payload = receipt.model_dump(mode="json")
    payload["source_manifest_hash"] = source_manifest_hash
    payload["receipt_hash"] = ""
    return QualityReviewReceiptV2.model_validate(payload)


__all__ = [
    "QualityReviewError",
    "rebind_quality_review_receipt_source",
    "stamp_quality_review_receipt",
    "validate_quality_review_receipt",
]
