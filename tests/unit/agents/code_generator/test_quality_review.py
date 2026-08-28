from __future__ import annotations

import pytest

from oryxenai.agents.code_generator.core.development_schemas import (
    QualityReviewDraftV1,
    QualityScoreEvidenceV1,
)
from oryxenai.agents.code_generator.core.quality_review import (
    QualityReviewError,
    rebind_quality_review_receipt_source,
    stamp_quality_review_receipt,
    validate_quality_review_receipt,
)


def _draft() -> QualityReviewDraftV1:
    return QualityReviewDraftV1(
        hierarchy_score=4,
        composition_score=4,
        typography_score=4,
        resource_fit_score=4,
        motion_score=4,
        score_evidence=[
            QualityScoreEvidenceV1(
                dimension=dimension,
                score=4,
                owner_work_unit_id="foundation",
                file="src/design/generated-tokens.css",
                line=1,
                marker="marker",
                evidence="evidence",
            )
            for dimension in ("hierarchy", "composition", "typography", "resource_fit", "motion")
        ],
        review_summary="The reviewed source satisfies the bounded quality contract.",
    )


def test_rebind_quality_review_receipt_source_recomputes_host_hash() -> None:
    receipt = stamp_quality_review_receipt(
        _draft(),
        source_manifest_hash="source-before",
        plan_hash="plan",
        realization_hash="realization",
        review_context_hash="context",
        response_id="response",
        quality_gate_version="quality-gate",
    )

    rebound = rebind_quality_review_receipt_source(
        receipt,
        source_manifest_hash="source-after",
    )

    assert rebound.source_manifest_hash == "source-after"
    assert rebound.receipt_hash != receipt.receipt_hash
    validate_quality_review_receipt(
        rebound,
        source_manifest_hash="source-after",
        plan_hash="plan",
        realization_hash="realization",
        review_context_hash="context",
        quality_gate_version="quality-gate",
    )
    with pytest.raises(QualityReviewError, match="different source hash"):
        validate_quality_review_receipt(
            receipt,
            source_manifest_hash="source-after",
            plan_hash="plan",
            realization_hash="realization",
            review_context_hash="context",
            quality_gate_version="quality-gate",
        )
