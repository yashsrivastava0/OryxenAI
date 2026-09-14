"""Pure extraction of validated model ``cannot_complete`` responses."""

from __future__ import annotations

from dataclasses import dataclass

from oryxenai.agents.code_generator.core.development_schemas import GenerationResult


@dataclass(frozen=True, slots=True)
class SemanticSourceDecline:
    """Safe, caller-neutral description of an honest source-operation decline."""

    code: str
    safe_reason: str
    missing_authority_or_capability: str = ""


def extract_semantic_source_decline(
    result: GenerationResult,
) -> SemanticSourceDecline | None:
    """Return a normalized decline without choosing a caller retry policy.

    Generation, integration polish, and final verification have different
    authority and budgets.  They share only this interpretation boundary;
    each caller remains responsible for deciding whether to replace, repair,
    re-review, or stop.
    """

    if result.mode != "cannot_complete":
        return None
    detail = result.cannot_complete
    if detail is None:
        # GenerationResult validation normally makes this unreachable, but a
        # total pure function keeps call sites fail-closed if a legacy object
        # is ever reconstructed without the tagged payload.
        return SemanticSourceDecline(
            code="GENERATION_FAILURE_UNSPECIFIED",
            safe_reason="The source operation could not complete safely.",
        )
    return SemanticSourceDecline(
        code=detail.code,
        safe_reason=detail.safe_reason,
        missing_authority_or_capability=detail.missing_authority_or_capability,
    )
