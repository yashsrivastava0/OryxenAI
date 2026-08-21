"""Strict creative-direction operation preceding source planning."""

from __future__ import annotations

from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import (
    CreativeDirectionSetV2,
    CreativeDirectionSetV3,
)
from oryxenai.agents.code_generator.core.generation_prompt_builder import build_instructions
from oryxenai.agents.shared.contracts import ModelClient


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
    result = await model.generate_structured(
        operation="code_generator.direct",
        instructions=instructions,
        input_payload=operation_context,
        output_model=output_model,
        system_prompt=system,
        model_profile=profile_name,
        strict_schema=True,
    )
    parsed = getattr(result, "parsed_output", result)
    return output_model.model_validate(parsed), receipt, result
