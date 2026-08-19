"""Read-only structured integration review for an assembled source checkpoint."""

from __future__ import annotations

from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import IntegrationReviewV1
from oryxenai.agents.code_generator.core.generation_prompt_builder import build_instructions
from oryxenai.agents.shared.contracts import ModelClient


async def run_integration_review_operation(
    model: ModelClient,
    *,
    context: dict[str, Any],
    profile_name: str,
) -> tuple[IntegrationReviewV1, Any, Any]:
    operation_context = {**context, "role_profile": profile_name}
    system, instructions, receipt = build_instructions(
        "integration_review", operation_context, output_model=IntegrationReviewV1
    )
    result = await model.generate_structured(
        operation="code_generator.review_integration",
        instructions=instructions,
        input_payload=operation_context,
        output_model=IntegrationReviewV1,
        system_prompt=system,
        model_profile=profile_name,
        strict_schema=True,
    )
    parsed = getattr(result, "parsed_output", result)
    return IntegrationReviewV1.model_validate(parsed), receipt, result
