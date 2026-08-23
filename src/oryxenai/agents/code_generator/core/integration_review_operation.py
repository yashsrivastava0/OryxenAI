"""Read-only structured integration review for an assembled source checkpoint."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from oryxenai.agents.code_generator.core.development_schemas import (
    IntegrationReviewV1,
    QualityReviewDraftV1,
)
from oryxenai.agents.code_generator.core.generation_prompt_builder import build_instructions
from oryxenai.agents.shared.contracts import ModelClient
from oryxenai.agents.shared.providers.errors import ModelJsonInvalidError, ModelOutputTruncatedError


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
                f"semantic validation: {last_issue[:400]}"
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
            return output_model.model_validate(parsed), receipt, result
        except (ModelJsonInvalidError, ModelOutputTruncatedError, ValidationError) as exc:
            last_issue = str(exc)
            if attempt:
                raise
    raise RuntimeError("quality review validation failed")
