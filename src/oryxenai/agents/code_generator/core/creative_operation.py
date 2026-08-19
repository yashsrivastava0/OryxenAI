"""Strict creative-direction operation preceding source planning."""

from __future__ import annotations

from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import CreativeDirectionSetV2
from oryxenai.agents.code_generator.core.generation_prompt_builder import build_instructions
from oryxenai.agents.shared.contracts import ModelClient


async def run_creative_direction_operation(
    model: ModelClient,
    *,
    context: dict[str, Any],
    profile_name: str,
) -> tuple[CreativeDirectionSetV2, Any, Any]:
    operation_context = {**context, "role_profile": profile_name}
    system, instructions, receipt = build_instructions(
        "director", operation_context, output_model=CreativeDirectionSetV2
    )
    result = await model.generate_structured(
        operation="code_generator.direct",
        instructions=instructions,
        input_payload=operation_context,
        output_model=CreativeDirectionSetV2,
        system_prompt=system,
        model_profile=profile_name,
        strict_schema=True,
    )
    parsed = getattr(result, "parsed_output", result)
    return CreativeDirectionSetV2.model_validate(parsed), receipt, result
