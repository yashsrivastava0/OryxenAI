"""Shared structured planner operation for Code Generator.

One implementation of the planner's structured model call, used by both the
durable ``code_generator.plan`` job and the registry-compatible
``CodeGeneratorAgent``: trusted prompt files, one canonical JSON untrusted
context, strict V4 blueprint output for active V4 runs, and (when upstream
projections are supplied) full host-side plan validation.  The legacy
``SitePlan`` output remains an explicit compatibility mode for older runs.
"""

from __future__ import annotations

import math
from typing import Any

from pydantic import ValidationError

from oryxenai.agents.code_generator.core.blueprint_compiler import compile_blueprint_site_plan
from oryxenai.agents.code_generator.core.development_planner import (
    validate_site_plan,
    validate_v4_blueprint_identities,
)
from oryxenai.agents.code_generator.core.development_schemas import (
    ExperienceBlueprintV3,
    ExperienceBlueprintV4,
    SitePlan,
)
from oryxenai.agents.code_generator.core.generation_prompt_builder import (
    PLANNER_FOUNDATION_KEY_ORDER,
    build_instructions,
)
from oryxenai.agents.code_generator.core.pipeline_contract import uses_blueprint
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
    pipeline_contract_version: str = "code-generator-v3",
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

    # v5 keeps the proven V4 blueprint shape while adding a fresh durable
    # queue namespace/release fence.  Keep the schema choice capability-based
    # rather than making the new queue version accidentally fall back to the
    # legacy unconstrained SitePlan.
    uses_v4 = uses_blueprint(pipeline_contract_version)
    output_model = ExperienceBlueprintV4 if uses_v4 else SitePlan
    prompt_operation = "planner_v4" if uses_v4 else "planner_legacy"
    try:
        system_prompt, instructions, receipt = build_instructions(
            prompt_operation, context, output_model=output_model
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
                "\n\nThe previous planner response did not satisfy the local v4 blueprint "
                if uses_v4
                else "\n\nThe previous planner response did not satisfy the local SitePlan "
            ) + (
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
                output_model=output_model,
                system_prompt=system_prompt,
                model_profile=profile_name,
                strict_schema=True,
                request_context={"key_order": PLANNER_FOUNDATION_KEY_ORDER},
            )
        except (ModelJsonInvalidError, ModelOutputTruncatedError) as exc:
            last_issue = _safe_planner_issue(exc)
            if attempt == 0:
                continue
            raise PlannerOperationError("PLANNER_OUTPUT_INVALID", last_issue) from exc

        parsed = getattr(result, "parsed_output", result)
        if uses_v4:
            # Providers occasionally return visually sensible but contract-
            # invalid ranges such as ``0.8..0.9`` for a distinctive move.
            # The executable contract intentionally requires a measurable
            # departure from neutral and a useful range.  Normalize only
            # numeric ranges here (before Pydantic validation), keeping the
            # provider's direction and all selectors/theses intact.  This is
            # the same host-owned canonicalization principle used for IDs and
            # selectors, and prevents an otherwise complete generation from
            # being rejected on a cosmetic numeric boundary.
            parsed = _canonicalize_v4_distinctive_move_ratios(parsed)
            parsed = _canonicalize_v4_typography_bindings(parsed, projections)
        try:
            if uses_v4:
                blueprint = ExperienceBlueprintV4.model_validate(parsed)
                validate_v4_blueprint_identities(blueprint, context)
                if projections is None:
                    raise PlannerOperationError(
                        "PLANNER_PROJECTIONS_REQUIRED",
                        "V4 blueprint compilation requires admitted pack projections.",
                    )
                plan = compile_blueprint_site_plan(
                    blueprint,
                    projections,
                    max_sections_per_unit=max_sections_per_unit,
                )
            else:
                plan = SitePlan.model_validate(parsed)
        except (ValidationError, ValueError) as exc:
            last_issue = (
                _safe_validation_summary(exc)
                if isinstance(exc, ValidationError)
                else str(exc)[:500]
            )
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
                if not uses_v4:
                    plan = compile_site_plan(
                        plan,
                        projections,
                        max_sections_per_unit=max_sections_per_unit,
                        design_neutral=require_blueprint
                        and isinstance(
                            plan.experience_blueprint,
                            (ExperienceBlueprintV3, ExperienceBlueprintV4),
                        ),
                    )
                if require_blueprint and plan.experience_blueprint is not None:
                    direction = context.get("creative_direction", {})
                    concepts = direction.get("candidates", direction.get("concepts", []))
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
                code = str(getattr(exc, "code", "") or "PLANNER_PLAN_INVALID")
                message = str(
                    getattr(exc, "message", "")
                    or str(exc).strip()
                    or "The planner output failed semantic SitePlan validation."
                )
                semantic_error = PlannerOperationError(
                    code,
                    message,
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


def _canonicalize_v4_distinctive_move_ratios(parsed: Any) -> Any:
    """Make provider-authored distinctive ranges satisfy the executable floor.

    ``DistinctiveMoveV4`` deliberately rejects neutral or very narrow ranges,
    but model providers are prone to rounding a useful visual relationship to
    two nearby values.  A bounded, deterministic widening is safer than
    spending another model call: it preserves the original direction, keeps
    values inside the schema's ``[-2, 2]`` bounds, and leaves already-valid
    ranges byte-for-byte unchanged.  Non-mapping values are returned as-is so
    normal schema errors remain visible to the caller.
    """

    if not isinstance(parsed, dict):
        return parsed
    raw_moves = parsed.get("distinctive_moves")
    if not isinstance(raw_moves, list):
        return parsed

    changed = False
    moves: list[Any] = []
    for raw_move in raw_moves:
        if not isinstance(raw_move, dict):
            moves.append(raw_move)
            continue
        relationship = str(raw_move.get("relationship", ""))
        if relationship == "sticky_within_section":
            moves.append(raw_move)
            continue
        minimum = raw_move.get("minimum_ratio")
        maximum = raw_move.get("maximum_ratio")
        if (
            minimum is None
            or maximum is None
            or isinstance(minimum, bool)
            or isinstance(maximum, bool)
        ):
            moves.append(raw_move)
            continue
        try:
            lower = float(minimum)
            upper = float(maximum)
        except (TypeError, ValueError):
            moves.append(raw_move)
            continue
        if not math.isfinite(lower) or not math.isfinite(upper):
            moves.append(raw_move)
            continue

        lower = max(-2.0, min(2.0, lower))
        upper = max(-2.0, min(2.0, upper))
        if lower > upper:
            lower, upper = upper, lower

        # Keep a provider's intended side of neutral where possible.  If it
        # straddles neutral without enough deviation, use the side indicated
        # by its midpoint so runtime verification still has a coherent target.
        midpoint = (lower + upper) / 2.0
        if upper <= 1.0:
            lower = min(lower, 0.8)
            upper = max(upper, lower + 0.15)
        elif lower >= 1.0:
            upper = max(upper, 1.2)
            lower = min(lower, upper - 0.15)
        else:
            if midpoint < 1.0:
                lower = min(lower, 0.8)
                upper = max(upper, lower + 0.15)
            else:
                upper = max(upper, 1.2)
                lower = min(lower, upper - 0.15)

        lower = max(-2.0, min(2.0, lower))
        upper = max(-2.0, min(2.0, upper))
        if upper - lower < 0.15:
            if upper < 2.0:
                upper = min(2.0, lower + 0.15)
            else:
                lower = max(-2.0, upper - 0.15)

        if lower != minimum or upper != maximum:
            updated = dict(raw_move)
            updated["minimum_ratio"] = round(lower, 4)
            updated["maximum_ratio"] = round(upper, 4)
            moves.append(updated)
            changed = True
        else:
            moves.append(raw_move)

    if not changed:
        return parsed
    result = dict(parsed)
    result["distinctive_moves"] = moves
    return result


def _canonicalize_v4_typography_bindings(parsed: Any, projections: dict[str, Any] | None) -> Any:
    """Bind font roles to host-owned paths and admitted font metadata.

    Build Preparation supplies font URLs, while acquisition materializes those
    files later. The planner nevertheless has to echo local file identities so
    the blueprint can be validated. Once the brief compiler has assigned
    deterministic intended paths, normalize guessed paths/family/weights to
    that binding without placing bytes or remote URLs in planner output.
    """

    if not isinstance(parsed, dict) or not isinstance(projections, dict):
        return parsed
    tokens = parsed.get("tokens")
    if not isinstance(tokens, dict):
        return parsed
    raw_roles = tokens.get("typography_roles")
    if not isinstance(raw_roles, list):
        return parsed
    execution = projections.get("execution/contract.json")
    if not isinstance(execution, dict):
        return parsed

    font_slots: dict[str, dict[str, Any]] = {}
    for raw_slot in execution.get("slots", []):
        if not isinstance(raw_slot, dict):
            continue
        resolution_value = raw_slot.get("resolution")
        resolution = resolution_value if isinstance(resolution_value, dict) else {}
        category = str(raw_slot.get("category", "")).casefold()
        if (
            "font" not in category
            and "typograph" not in category
            and not str(resolution.get("font_family", "")).strip()
        ):
            continue
        slot_id = str(raw_slot.get("resource_slot_id", "")).strip()
        if slot_id:
            font_slots[slot_id] = raw_slot
    if not font_slots:
        return parsed

    changed = False
    roles: list[Any] = []
    fallback_slot = next(iter(font_slots)) if len(font_slots) == 1 else ""
    for raw_role in raw_roles:
        if not isinstance(raw_role, dict):
            roles.append(raw_role)
            continue
        slot_id = str(raw_role.get("approved_font_slot", "")).strip()
        if slot_id not in font_slots and fallback_slot:
            slot_id = fallback_slot
        slot = font_slots.get(slot_id)
        if slot is None:
            roles.append(raw_role)
            continue
        resolution_value = slot.get("resolution")
        resolution = resolution_value if isinstance(resolution_value, dict) else {}
        local_paths = [str(item) for item in resolution.get("local_paths", []) if str(item)]
        if not local_paths:
            roles.append(raw_role)
            continue

        available_weights = [
            int(item)
            for item in resolution.get("font_weights", [])
            if str(item).isdigit() and 100 <= int(item) <= 1000 and int(item) % 100 == 0
        ]
        updated = dict(raw_role)
        updated["approved_font_slot"] = slot_id
        updated["local_files"] = local_paths
        family = str(resolution.get("font_family", "")).strip()
        if family:
            updated["family"] = family
        if available_weights:
            requested_weights = {
                int(item) for item in raw_role.get("weights", []) if str(item).isdigit()
            }
            selected_weights = [item for item in available_weights if item in requested_weights]
            updated["weights"] = selected_weights or available_weights
        # The current Build Preparation contract exposes normal Fontsource
        # variants. Keep the role's style aligned with those files.
        variant_styles = {
            str(path).rsplit("/", 1)[-1].split(".", 1)[0].rsplit("-", 1)[-1]
            for path in local_paths
            if "-" in str(path).rsplit("/", 1)[-1]
        }
        if variant_styles == {"normal"}:
            updated["style"] = "normal"
        if updated != raw_role:
            changed = True
        roles.append(updated)

    if not changed:
        return parsed
    result = dict(parsed)
    result_tokens = dict(tokens)
    result_tokens["typography_roles"] = roles
    result["tokens"] = result_tokens
    return result


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
