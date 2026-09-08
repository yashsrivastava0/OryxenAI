from __future__ import annotations

import pytest

from oryxenai.agents.code_generator.core.development_schemas import (
    QualityFindingV2,
    QualityReviewDraftV1,
    QualityScoreEvidenceV1,
)
from oryxenai.agents.code_generator.core.quality_review import (
    QualityReviewError,
    rebind_quality_review_receipt_source,
    stamp_quality_review_receipt,
    validate_quality_review_draft_evidence,
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


def test_low_visual_score_with_advisory_finding_remains_accepted() -> None:
    draft = _draft().model_copy(
        update={
            "composition_score": 2,
            "score_evidence": [
                item.model_copy(update={"score": 2})
                if item.dimension == "composition"
                else item
                for item in _draft().score_evidence
            ],
            "findings": [
                QualityFindingV2(
                    finding_id="finding-spacing",
                    severity="blocking",
                    owner_work_unit_id="foundation",
                    code="VISUAL_SPACING_VARIANCE",
                    file="src/design/generated-tokens.css",
                    line=1,
                    marker="marker",
                    evidence="Optional visual spacing differs from the reference composition.",
                    requested_outcome="Polish the spacing if desired.",
                )
            ],
        }
    )
    validated = validate_quality_review_draft_evidence(
        draft,
        assembled_source={"src/design/generated-tokens.css": "marker"},
        repairable_owner_ids={"foundation"},
    )
    receipt = stamp_quality_review_receipt(
        validated,
        source_manifest_hash="source",
        plan_hash="plan",
        realization_hash="realization",
        review_context_hash="context",
        response_id="response",
        quality_gate_version="quality-gate",
    )
    assert receipt.accepted is True
    assert receipt.findings[0].severity == "advisory"


def test_functional_quality_finding_still_blocks_low_or_high_scores() -> None:
    draft = _draft().model_copy(
        update={
            "findings": [
                QualityFindingV2(
                    finding_id="finding-navigation",
                    severity="advisory",
                    owner_work_unit_id="foundation",
                    code="NAVIGATION_BROKEN",
                    file="src/app/App.tsx",
                    line=1,
                    marker="marker",
                    evidence="A required navigation destination is missing.",
                    requested_outcome="Restore the required destination.",
                )
            ],
        }
    )
    validated = validate_quality_review_draft_evidence(
        draft,
        assembled_source={
            "src/app/App.tsx": "marker",
            "src/design/generated-tokens.css": "marker",
        },
        repairable_owner_ids={"foundation"},
    )
    receipt = stamp_quality_review_receipt(
        validated,
        source_manifest_hash="source",
        plan_hash="plan",
        realization_hash="realization",
        review_context_hash="context",
        response_id="response",
        quality_gate_version="quality-gate",
    )
    assert receipt.accepted is False
    assert receipt.findings[0].severity == "blocking"
