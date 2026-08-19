"""Shared structured planner operation for Code Generator.

One implementation of the planner's structured model call, used by both the
durable ``code_generator.plan`` job and the registry-compatible
``CodeGeneratorAgent``: trusted prompt files (``prompts/system.md`` +
``prompts/planner.md``), one canonical JSON untrusted context, strict
structured output against ``SitePlan``, and (when upstream projections are
supplied) full semantic plan validation.
"""

from __future__ import annotations

from typing import Any

from oryxenai.agents.code_generator.core.development_planner import validate_site_plan
from oryxenai.agents.code_generator.core.development_schemas import SitePlan
from oryxenai.agents.code_generator.core.generation_prompt_builder import build_instructions
from oryxenai.agents.code_generator.core.work_graph_compiler import compile_site_plan
from oryxenai.agents.shared.contracts import ModelClient

PLANNER_OPERATION = "code_generator.plan"


def _canonicalize_work_graph(plan: SitePlan) -> SitePlan:
    """Apply the fully-determined WorkGraph invariants before validation.

    The terminal integration unit must depend on every other unit by rule;
    filling that list mechanically is a canonicalization, not a content
    change, so a planner that enumerates the dependencies incompletely is
    corrected instead of rejected.
    """

    terminal = [
        unit for unit in plan.work_graph.units if unit.terminal and unit.kind == "integration"
    ]
    if len(terminal) != 1:
        return plan
    unit = terminal[0]
    others = sorted(
        {other.unit_id for other in plan.work_graph.units if other.unit_id != unit.unit_id}
    )
    if sorted(set(unit.depends_on)) == others:
        return plan
    updated = unit.model_copy(update={"depends_on": others})
    units = [
        updated if candidate.unit_id == unit.unit_id else candidate
        for candidate in plan.work_graph.units
    ]
    return plan.model_copy(
        update={"work_graph": plan.work_graph.model_copy(update={"units": units})}
    )


class PlannerOperationError(ValueError):
    """A safe, code-carrying failure of the structured planner call."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


async def run_planner_operation(
    planner: ModelClient,
    *,
    context: dict[str, Any],
    profile_name: str,
    projections: dict[str, Any] | None = None,
    max_work_units: int = 64,
    max_sections_per_unit: int = 3,
    require_blueprint: bool = False,
) -> tuple[SitePlan, str, Any, Any]:
    """Run the structured planner call.

    Returns ``(plan, prompt_version, prompt_receipt, model_result)`` where
    ``prompt_receipt`` is the ``GenerationContextReceipt`` and ``model_result``
    is the transport's ``StructuredModelResult`` (usage/response identity).

    ``projections`` (the admitted pack projections) additionally enables the
    deep semantic validation the durable workflow requires; without it the
    plan is only schema-validated, which is the contract for the generic
    agent-run harness.
    """

    try:
        system_prompt, instructions, receipt = build_instructions(
            "planner", context, output_model=SitePlan
        )
    except Exception as exc:  # missing/unreadable prompt or schema failure
        raise PlannerOperationError(
            "PLANNER_PROMPT_UNAVAILABLE",
            "The trusted planner prompt set could not be assembled.",
        ) from exc

    result = await planner.generate_structured(
        operation=PLANNER_OPERATION,
        instructions=instructions,
        input_payload=context,
        output_model=SitePlan,
        system_prompt=system_prompt,
        model_profile=profile_name,
        strict_schema=True,
    )
    prompt_version = str(receipt.prompt_versions.get("operation", ""))
    parsed = getattr(result, "parsed_output", result)
    try:
        plan = SitePlan.model_validate(parsed)
    except Exception as exc:
        raise PlannerOperationError(
            "PLANNER_OUTPUT_INVALID",
            "The planner output failed SitePlan schema validation.",
        ) from exc
    if projections is not None:
        try:
            plan = compile_site_plan(
                plan,
                projections,
                max_sections_per_unit=max_sections_per_unit,
            )
            if require_blueprint and plan.experience_blueprint is not None:
                concepts = context.get("creative_direction", {}).get("candidates", [])
                concept_ids = {
                    str(item.get("concept_id", "")) for item in concepts if isinstance(item, dict)
                }
                if plan.experience_blueprint.selected_concept_id not in concept_ids:
                    raise PlannerOperationError(
                        "PLAN_CREATIVE_CONCEPT_UNKNOWN",
                        "The experience blueprint selected an unknown creative concept.",
                    )
            plan = validate_site_plan(
                plan,
                projections,
                max_work_units=max_work_units,
                require_blueprint=require_blueprint,
            )
        except Exception as exc:
            raise PlannerOperationError(
                str(getattr(exc, "code", "") or "PLANNER_PLAN_INVALID"),
                "The planner output failed semantic SitePlan validation.",
            ) from exc
    else:
        plan = _canonicalize_work_graph(plan)
    return plan, prompt_version, receipt, result
