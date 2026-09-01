"""Deterministic validation for hash-bound whole-site quality receipts."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import (
    QualityReviewDraftV1,
    QualityReviewReceiptV1,
    QualityReviewReceiptV2,
)


class QualityReviewError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def _nearby_unique_marker(source: str, reported_line: int) -> str:
    """Select an exact, bounded source literal near an approximate model line."""

    lines = source.splitlines()
    indexes = sorted(range(len(lines)), key=lambda index: (abs(index + 1 - reported_line), index))
    for index in indexes:
        line = lines[index].strip()
        if len(line) < 3 or line in {"{", "}"}:
            continue
        candidates = [line] if len(line) <= 400 else [line[:400], line[-400:]]
        for candidate in candidates:
            if source.count(candidate) == 1:
                return candidate
    return ""


def validate_quality_review_draft_evidence(
    draft: QualityReviewDraftV1,
    *,
    assembled_source: dict[str, str],
    repairable_owner_ids: set[str] | None = None,
) -> QualityReviewDraftV1:
    """Require every V4 review claim to point at exact assembled source.

    The provider is allowed to assess quality, but it cannot create evidence
    paths, line numbers, or markers. A score below the acceptance floor also
    needs a blocking finding on the same owner/file so the bounded polish pass
    receives an actionable defect for that dimension.
    """

    def validate_record(record: Any, *, label: str) -> Any:
        path = str(record.file).replace("\\", "/").strip("/")
        source = assembled_source.get(path)
        if source is None:
            raise QualityReviewError(
                "QUALITY_EVIDENCE_FILE_INVALID",
                f"{label} references a file outside the assembled source: {path}",
            )
        marker = str(record.marker)
        reported_line = int(record.line)
        positions: list[int] = []
        start = 0
        while marker and (position := source.find(marker, start)) >= 0:
            positions.append(position)
            start = position + max(1, len(marker))
        if not positions:
            raise QualityReviewError(
                "QUALITY_EVIDENCE_MARKER_INVALID",
                f"{label} marker does not occur in its source file: {path}",
                details={
                    "label": label,
                    "file": path,
                    "rejected_marker": marker,
                    "reported_line": reported_line,
                    "suggested_marker": _nearby_unique_marker(source, reported_line),
                },
            )
        marker_lines = {source.count("\n", 0, position) + 1 for position in positions}
        if reported_line in marker_lines:
            canonical_line = reported_line
        else:
            nearest_distance = min(abs(line - reported_line) for line in marker_lines)
            nearest_lines = sorted(
                line for line in marker_lines if abs(line - reported_line) == nearest_distance
            )
            if len(nearest_lines) != 1:
                raise QualityReviewError(
                    "QUALITY_EVIDENCE_LINE_AMBIGUOUS",
                    f"{label} uses a repeated literal marker in {path}, and its approximate "
                    f"line is equally close to {nearest_lines}.",
                )
            canonical_line = nearest_lines[0]
        if path == record.file and canonical_line == int(record.line):
            return record
        return record.model_copy(update={"file": path, "line": canonical_line})

    score_evidence = [
        validate_record(evidence, label=f"{evidence.dimension} score evidence")
        for evidence in draft.score_evidence
    ]
    findings = [
        validate_record(finding, label=f"finding {finding.finding_id}")
        for finding in draft.findings
    ]
    canonical = draft.model_copy(update={"score_evidence": score_evidence, "findings": findings})

    blocking = [item for item in canonical.findings if item.severity == "blocking"]
    if repairable_owner_ids is not None:
        for finding in blocking:
            owner = finding.owner_work_unit_id
            composer_alias = (
                f"{owner[: -len('-composer')]}-compose" if owner.endswith("-composer") else ""
            )
            if owner not in repairable_owner_ids and composer_alias not in repairable_owner_ids:
                raise QualityReviewError(
                    "QUALITY_FINDING_OWNER_INVALID",
                    f"Blocking finding {finding.finding_id} targets non-repairable owner {owner}.",
                )
    for evidence in canonical.score_evidence:
        if evidence.score >= 4:
            continue
        if not any(
            finding.owner_work_unit_id == evidence.owner_work_unit_id
            and finding.file.replace("\\", "/").strip("/")
            == evidence.file.replace("\\", "/").strip("/")
            for finding in blocking
        ):
            raise QualityReviewError(
                "QUALITY_SCORE_FINDING_MISSING",
                f"The {evidence.dimension} score is below four but has no blocking "
                "finding on the same owned source file.",
            )
    return canonical


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
    "validate_quality_review_draft_evidence",
    "validate_quality_review_receipt",
]
