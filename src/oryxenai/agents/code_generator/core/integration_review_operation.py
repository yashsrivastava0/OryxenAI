"""Read-only structured integration review for an assembled source checkpoint."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from oryxenai.agents.code_generator.core.development_schemas import (
    IntegrationReviewV1,
    QualityReviewDraftV1,
)
from oryxenai.agents.code_generator.core.generation_prompt_builder import build_instructions
from oryxenai.agents.code_generator.core.quality_review import (
    QualityReviewError,
    validate_quality_review_draft_evidence,
)
from oryxenai.agents.shared.contracts import ModelClient
from oryxenai.agents.shared.providers.errors import ModelJsonInvalidError, ModelOutputTruncatedError


def _semantic_retry_feedback(exc: Exception) -> str:
    if not isinstance(exc, QualityReviewError):
        return str(exc)
    rejected = str(exc.details.get("rejected_marker", ""))
    suggested = str(exc.details.get("suggested_marker", ""))
    if not rejected:
        return str(exc)
    correction = f"The rejected marker was {rejected!r}."
    if suggested:
        correction += (
            f" For that same evidence record, use this exact literal from the named "
            f"source file: {suggested!r}."
        )
    return f"{correction} Validation error: {exc}"


async def run_integration_review_operation(
    model: ModelClient,
    *,
    context: dict[str, Any],
    profile_name: str,
    output_version: str = "legacy",
) -> tuple[IntegrationReviewV1 | QualityReviewDraftV1, Any, Any]:
    operation_context = {**context, "role_profile": profile_name}
    output_model = QualityReviewDraftV1 if output_version == "v4" else IntegrationReviewV1
    system, instructions, receipt = build_instructions(
        "integration_review", operation_context, output_model=output_model
    )
    last_issue = ""
    result: Any = None
    for attempt in range(2):
        call_instructions = instructions
        if last_issue:
            call_instructions += (
                "\n\nReturn a complete replacement review. The prior response failed local "
                f"semantic validation: {last_issue[:1200]}"
            )
        try:
            result = await model.generate_structured(
                operation="code_generator.review_integration",
                instructions=call_instructions,
                input_payload=operation_context,
                output_model=output_model,
                system_prompt=system,
                model_profile=profile_name,
                strict_schema=True,
            )
            parsed = getattr(result, "parsed_output", result)
            review = output_model.model_validate(parsed)
            if isinstance(review, QualityReviewDraftV1):
                source = operation_context.get("assembled_source", {})
                work_graph = operation_context.get("work_graph", {})
                units = work_graph.get("units", []) if isinstance(work_graph, dict) else []
                repairable_owner_ids = {
                    str(unit.get("unit_id", ""))
                    for unit in units
                    if isinstance(unit, dict)
                    and str(unit.get("unit_id", ""))
                    and not bool(unit.get("terminal", False))
                }
                review = validate_quality_review_draft_evidence(
                    review,
                    assembled_source=(
                        {str(key): str(value) for key, value in source.items()}
                        if isinstance(source, dict)
                        else {}
                    ),
                    repairable_owner_ids=repairable_owner_ids or None,
                )
            return review, receipt, result
        except (
            ModelJsonInvalidError,
            ModelOutputTruncatedError,
            QualityReviewError,
            ValidationError,
        ) as exc:
            last_issue = _semantic_retry_feedback(exc)
            if attempt:
                raise
    raise RuntimeError("quality review validation failed")
