"""Translate the v4 source wire envelope into the internal workflow DTO."""

from __future__ import annotations

from oryxenai.agents.code_generator.core.development_schemas import (
    GenerationAccepted,
    GenerationCannotComplete,
    GenerationChanges,
    GenerationContextReceipt,
    GenerationRequests,
    GenerationResult,
    SourceGenerationEnvelopeV2,
)


def adapt_v4_generation_result(
    envelope: SourceGenerationEnvelopeV2,
    *,
    operation_id: str,
    context_receipt: GenerationContextReceipt,
) -> GenerationResult:
    """Adapt the mapping-free v4 envelope without weakening its evidence.

    The durable orchestration code still has a legacy internal result type for
    compatibility with the v3 workflow.  V4 model calls must nevertheless use
    ``SourceGenerationEnvelopeV2`` on the wire; this adapter is the sole
    boundary between those two representations.
    """

    if envelope.result == "changes":
        return GenerationResult(
            operation_id=operation_id,
            based_on_context_receipt=context_receipt.context_hash,
            mode="changes",
            changes=GenerationChanges(
                files=list(envelope.files),
                exported_signatures=list(envelope.exported_signatures),
                content_coverage=list(envelope.content_ids),
                criterion_coverage=list(envelope.criterion_ids),
                resource_usage=list(envelope.resource_slot_ids),
                interaction_coverage=list(envelope.interaction_ids),
            ),
        )
    if envelope.result == "requests":
        return GenerationResult(
            operation_id=operation_id,
            based_on_context_receipt=context_receipt.context_hash,
            mode="requests",
            requests=GenerationRequests(
                resource_requests=list(envelope.resource_requests),
                dependency_requests=list(envelope.dependency_requests),
            ),
        )
    if envelope.result == "accepted":
        return GenerationResult(
            operation_id=operation_id,
            based_on_context_receipt=context_receipt.context_hash,
            mode="accepted",
            accepted=GenerationAccepted(
                summary="The v4 source work unit was accepted.",
                verified_contracts=[
                    *envelope.content_ids,
                    *envelope.criterion_ids,
                    *envelope.resource_slot_ids,
                    *envelope.interaction_ids,
                ],
            ),
        )
    detail = envelope.failure_details[0]
    return GenerationResult(
        operation_id=operation_id,
        based_on_context_receipt=context_receipt.context_hash,
        mode="cannot_complete",
        cannot_complete=GenerationCannotComplete(
            code=detail.code,
            safe_reason=detail.message,
            missing_authority_or_capability=detail.next_action,
        ),
    )


__all__ = ["adapt_v4_generation_result"]
