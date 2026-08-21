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

from pydantic import ValidationError

from oryxenai.agents.code_generator.core.development_planner import validate_site_plan
from oryxenai.agents.code_generator.core.development_schemas import (
    ExperienceBlueprintV3,
    SitePlan,
)
from oryxenai.agents.code_generator.core.generation_prompt_builder import build_instructions
from oryxenai.agents.code_generator.core.work_graph_compiler import compile_site_plan
from oryxenai.agents.shared.contracts import ModelClient
from oryxenai.agents.shared.providers.errors import (
    ModelJsonInvalidError,
    ModelOutputTruncatedError,
)

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

    prompt_version = str(receipt.prompt_versions.get("operation", ""))
    last_issue = ""
    result: Any = None
    plan: SitePlan | None = None
    for attempt in range(2):
        call_instructions = instructions
        if last_issue:
            call_instructions += (
                "\n\nThe previous planner response did not satisfy the local SitePlan "
                "schema or semantic validator. Return a complete replacement object "
                "and correct this safe validator summary: "
                f"{last_issue}. Do not omit required fields, use null for required "
                "values, or include commentary."
            )
        try:
            result = await planner.generate_structured(
                operation=PLANNER_OPERATION,
                instructions=call_instructions,
                input_payload=context,
                output_model=SitePlan,
                system_prompt=system_prompt,
                model_profile=profile_name,
                strict_schema=True,
            )
        except (ModelJsonInvalidError, ModelOutputTruncatedError) as exc:
            last_issue = _safe_planner_issue(exc)
            if attempt == 0:
                continue
            raise PlannerOperationError("PLANNER_OUTPUT_INVALID", last_issue) from exc

        parsed = getattr(result, "parsed_output", result)
        try:
            plan = SitePlan.model_validate(parsed)
        except ValidationError as exc:
            last_issue = _safe_validation_summary(exc)
            if attempt == 0:
                continue
            raise PlannerOperationError("PLANNER_OUTPUT_INVALID", last_issue) from exc
        if plan is None:
            raise PlannerOperationError(
                "PLANNER_OUTPUT_INVALID",
                last_issue or "The planner output failed SitePlan schema validation.",
            )
        if projections is not None:
            try:
                plan = compile_site_plan(
                    plan,
                    projections,
                    max_sections_per_unit=max_sections_per_unit,
                    design_neutral=require_blueprint
                    and isinstance(plan.experience_blueprint, ExperienceBlueprintV3),
                )
                if require_blueprint and plan.experience_blueprint is not None:
                    concepts = context.get("creative_direction", {}).get("candidates", [])
                    concept_ids = {
                        str(item.get("concept_id", ""))
                        for item in concepts
                        if isinstance(item, dict)
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
            except PlannerOperationError as exc:
                last_issue = _safe_semantic_issue(exc)
                if attempt == 0:
                    continue
                raise
            except Exception as exc:
                semantic_error = PlannerOperationError(
                    str(getattr(exc, "code", "") or "PLANNER_PLAN_INVALID"),
                    "The planner output failed semantic SitePlan validation.",
                )
                last_issue = _safe_semantic_issue(semantic_error)
                if attempt == 0:
                    continue
                raise semantic_error from exc
        else:
            plan = _canonicalize_work_graph(plan)
        return plan, prompt_version, receipt, result
    raise PlannerOperationError(
        "PLANNER_OUTPUT_INVALID",
        last_issue or "The planner output failed SitePlan validation.",
    )


def _safe_planner_issue(exc: Exception) -> str:
    message = str(exc).strip()
    return message[:400] or "The planner response could not be parsed."


def _safe_validation_summary(exc: ValidationError) -> str:
    entries: list[str] = []
    for error in exc.errors(include_url=False)[:8]:
        location = ".".join(str(part) for part in error.get("loc", ())) or "root"
        message = str(error.get("msg", "invalid value"))[:160]
        entries.append(f"{location}: {message}")
    return "; ".join(entries)[:500] or "The planner output failed SitePlan schema validation."


def _safe_semantic_issue(exc: PlannerOperationError) -> str:
    code = str(exc.code or "PLANNER_PLAN_INVALID")[:120]
    message = str(exc.message or "The planner output failed semantic SitePlan validation.")
    return f"{code}: {message[:320]}"
