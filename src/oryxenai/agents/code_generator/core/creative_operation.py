"""Strict creative-direction operation preceding source planning."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from oryxenai.agents.code_generator.core.development_schemas import (
    CreativeDirectionSetV2,
    CreativeDirectionSetV3,
)
from oryxenai.agents.code_generator.core.generation_prompt_builder import build_instructions
from oryxenai.agents.shared.contracts import ModelClient
from oryxenai.agents.shared.providers.errors import ModelJsonInvalidError, ModelOutputTruncatedError


async def run_creative_direction_operation(
    model: ModelClient,
    *,
    context: dict[str, Any],
    profile_name: str,
    output_version: str = "v2",
) -> tuple[CreativeDirectionSetV2 | CreativeDirectionSetV3, Any, Any]:
    output_model = CreativeDirectionSetV3 if output_version == "v3" else CreativeDirectionSetV2
    operation_context = {**context, "role_profile": profile_name}
    system, instructions, receipt = build_instructions(
        "director", operation_context, output_model=output_model
    )
    last_issue = ""
    result: Any = None
    for attempt in range(2):
        attempt_instructions = instructions
        if last_issue:
            attempt_instructions += (
                "\n\nReturn a complete replacement. The prior response failed the local "
                f"creative-direction validator: {last_issue[:400]}"
            )
        try:
            result = await model.generate_structured(
                operation="code_generator.direct",
                instructions=attempt_instructions,
                input_payload=operation_context,
                output_model=output_model,
                system_prompt=system,
                model_profile=profile_name,
                strict_schema=True,
            )
            parsed = getattr(result, "parsed_output", result)
            return output_model.model_validate(parsed), receipt, result
        except (ModelJsonInvalidError, ModelOutputTruncatedError, ValidationError) as exc:
            last_issue = str(exc).strip() or type(exc).__name__
            if attempt:
                raise
    raise RuntimeError("creative direction validation failed")
