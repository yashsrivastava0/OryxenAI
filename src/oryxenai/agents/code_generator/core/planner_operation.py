"""Shared structured planner operation for Code Generator.

One implementation of the planner's structured model call, used by both the
durable ``code_generator.plan`` job and the registry-compatible
``CodeGeneratorAgent``: trusted prompt files, one canonical JSON untrusted
context, strict V4 blueprint output for active V4 runs, and (when upstream
projections are supplied) full host-side plan validation.  The legacy
``SitePlan`` output remains an explicit compatibility mode for older runs.
"""

from __future__ import annotations

import hashlib
import math
import time
from typing import Any

from pydantic import ValidationError

from oryxenai.agents.code_generator.core.blueprint_compiler import compile_blueprint_site_plan
from oryxenai.agents.code_generator.core.development_planner import (
    canonical_json,
    validate_site_plan,
    validate_v4_blueprint_identities,
)
from oryxenai.agents.code_generator.core.development_schemas import (
    SHADCN_THEME_SLOTS,
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

    def __init__(
        self,
        code: str,
        message: str,
        *,
        attempt_diagnostics: list[dict[str, Any]] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.attempt_diagnostics = list(attempt_diagnostics or [])
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
    max_attempts: int = 2,
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
    attempt_diagnostics: list[dict[str, Any]] = []
    expected_identity_ids = _expected_identity_ids(context)
    # One initial call and one evidence-backed correction is the default.  A
    # caller may lower this for a dry-run, but no caller can accidentally turn
    # a malformed planner response into an unbounded paid loop.
    attempts = max(1, int(max_attempts))
    for attempt in range(attempts):
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
        result = None
        started_at = time.perf_counter()
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
            attempt_diagnostics.append(
                _planner_attempt_record(
                    attempt=attempt + 1,
                    context_hash=receipt.context_hash,
                    prompt_version=prompt_version,
                    result=None,
                    duration_ms=(time.perf_counter() - started_at) * 1000.0,
                    error_code="PLANNER_OUTPUT_INVALID",
                    error_summary=last_issue,
                    expected_identity_ids=expected_identity_ids,
                )
            )
            if attempt < attempts - 1:
                continue
            raise PlannerOperationError(
                "PLANNER_OUTPUT_INVALID",
                last_issue,
                attempt_diagnostics=attempt_diagnostics,
            ) from exc
        except Exception as exc:
            last_issue = _safe_planner_issue(exc)
            attempt_diagnostics.append(
                _planner_attempt_record(
                    attempt=attempt + 1,
                    context_hash=receipt.context_hash,
                    prompt_version=prompt_version,
                    result=None,
                    duration_ms=(time.perf_counter() - started_at) * 1000.0,
                    error_code=type(exc).__name__,
                    error_summary=last_issue,
                    expected_identity_ids=expected_identity_ids,
                )
            )
            if hasattr(exc, "__dict__"):
                exc.__dict__["attempt_diagnostics"] = list(attempt_diagnostics)
            raise

        attempt_record = _planner_attempt_record(
            attempt=attempt + 1,
            context_hash=receipt.context_hash,
            prompt_version=prompt_version,
            result=result,
            duration_ms=(time.perf_counter() - started_at) * 1000.0,
            expected_identity_ids=expected_identity_ids,
        )
        attempt_diagnostics.append(attempt_record)

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
            parsed = _canonicalize_v4_blueprint_identities(parsed, context)
            parsed = _canonicalize_v4_reserved_color_tokens(parsed)
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
            if attempt < attempts - 1:
                _mark_planner_attempt_failure(attempt_record, "PLANNER_OUTPUT_INVALID", last_issue)
                continue
            _mark_planner_attempt_failure(attempt_record, "PLANNER_OUTPUT_INVALID", last_issue)
            raise PlannerOperationError(
                "PLANNER_OUTPUT_INVALID",
                last_issue,
                attempt_diagnostics=attempt_diagnostics,
            ) from exc
        if plan is None:
            _mark_planner_attempt_failure(
                attempt_record,
                "PLANNER_OUTPUT_INVALID",
                last_issue or "The planner output failed SitePlan schema validation.",
            )
            raise PlannerOperationError(
                "PLANNER_OUTPUT_INVALID",
                last_issue or "The planner output failed SitePlan schema validation.",
                attempt_diagnostics=attempt_diagnostics,
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
                _mark_planner_attempt_failure(attempt_record, exc.code, last_issue)
                if attempt < attempts - 1:
                    continue
                exc.attempt_diagnostics = list(attempt_diagnostics)
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
                _mark_planner_attempt_failure(attempt_record, code, last_issue)
                if attempt < attempts - 1:
                    continue
                semantic_error.attempt_diagnostics = list(attempt_diagnostics)
                raise semantic_error from exc
        else:
            plan = _canonicalize_work_graph(plan)
        attempt_record["accepted"] = True
        _attach_planner_telemetry(result, attempt_diagnostics)
        return plan, prompt_version, receipt, result
    raise PlannerOperationError(
        "PLANNER_OUTPUT_INVALID",
        last_issue or "The planner output failed SitePlan validation.",
        attempt_diagnostics=attempt_diagnostics,
    )


def _expected_identity_ids(context: dict[str, Any]) -> list[str]:
    manifest = context.get("blueprint_identity_manifest")
    if not isinstance(manifest, list):
        return []
    return sorted(
        {
            str(item.get("region_id", "")).strip()
            for item in manifest
            if isinstance(item, dict) and str(item.get("region_id", "")).strip()
        }
    )[:128]


def _planner_attempt_record(
    *,
    attempt: int,
    context_hash: str,
    prompt_version: str,
    result: Any,
    duration_ms: float,
    error_code: str = "",
    error_summary: str = "",
    expected_identity_ids: list[str] | None = None,
) -> dict[str, Any]:
    usage = {
        str(key): int(value)
        for key, value in dict(getattr(result, "usage", {}) or {}).items()
        if isinstance(value, int) and not isinstance(value, bool)
    }
    payload = getattr(result, "parsed_output", None)
    record: dict[str, Any] = {
        "operation": PLANNER_OPERATION,
        "attempt": attempt,
        "context_hash": context_hash,
        "prompt_version": prompt_version,
        "response_id": str(getattr(result, "response_id", "") or ""),
        "model": str(getattr(result, "model", "") or ""),
        "usage": usage,
        "finish_reason": str(getattr(result, "finish_reason", "") or ""),
        "duration_ms": round(max(0.0, duration_ms), 3),
        "accepted": False,
        "error_code": error_code,
        "error_summary": error_summary[:500],
        "failure_field": error_summary.split(":", 1)[0][:120] if ":" in error_summary else "",
        "offending_id": "",
        "expected_identity_ids": list(expected_identity_ids or []),
    }
    if isinstance(payload, dict):
        record["response_payload_hash"] = hashlib.sha256(canonical_json(payload)).hexdigest()
        # Kept only for the restricted diagnostic artifact writer.  This key
        # is removed before the receipt is persisted or exposed to clients.
        record["_response_payload"] = payload
    return record


def _mark_planner_attempt_failure(record: dict[str, Any], code: str, summary: str) -> None:
    record.update(
        {
            "error_code": code[:120],
            "error_summary": summary[:500],
            "failure_field": summary.split(":", 1)[0][:120] if ":" in summary else "",
        }
    )


def _attach_planner_telemetry(result: Any, diagnostics: list[dict[str, Any]]) -> None:
    safe_copy = [dict(item) for item in diagnostics]
    telemetry = getattr(result, "telemetry", None)
    if isinstance(telemetry, dict):
        telemetry["planner_attempt_diagnostics"] = safe_copy
        return
    try:
        result.telemetry = {"planner_attempt_diagnostics": safe_copy}
    except Exception:
        # Test doubles may expose an immutable result object. The validated
        # plan remains usable; the handler still records the final receipt.
        return


def _canonicalize_v4_blueprint_identities(parsed: Any, context: dict[str, Any]) -> Any:
    """Rebind model aliases to the host-owned route/section identity map.

    The model still chooses composition, ranges, and selectors.  It does not
    own the IDs that connect those choices to approved content, however.  A
    known, unique ``(route_id, section_id)`` pair therefore gets the exact
    region/owner/section-selector values from the manifest *before* Pydantic's
    cross-reference validator runs.  Unknown pairs are intentionally left
    untouched so the normal validator reports a precise scope error rather
    than silently inventing a section.
    """

    if not isinstance(parsed, dict):
        return parsed
    raw_manifest = context.get("blueprint_identity_manifest")
    if not isinstance(raw_manifest, list):
        return parsed
    identities: dict[tuple[str, str], dict[str, str]] = {}
    ambiguous: set[tuple[str, str]] = set()
    for raw in raw_manifest:
        if not isinstance(raw, dict):
            continue
        key = (str(raw.get("route_id", "")).strip(), str(raw.get("section_id", "")).strip())
        if not all(key):
            continue
        if key in identities:
            ambiguous.add(key)
        else:
            identities[key] = {
                "region_id": str(raw.get("region_id", "")).strip(),
                "owner_id": str(raw.get("owner_id", "")).strip(),
            }
    for key in ambiguous:
        identities.pop(key, None)

    selector_manifest: dict[tuple[str, str], dict[str, str]] = {}
    raw_selectors = context.get("blueprint_selector_manifest")
    if isinstance(raw_selectors, list):
        for raw in raw_selectors:
            if not isinstance(raw, dict):
                continue
            key = (str(raw.get("route_id", "")).strip(), str(raw.get("section_id", "")).strip())
            if key in identities and key not in selector_manifest:
                selector_manifest[key] = {
                    name: str(raw.get(name, "")).strip()
                    for name in ("section_selector", "region_selector")
                    if str(raw.get(name, "")).strip()
                }

    changed = False
    result = dict(parsed)
    raw_regions = parsed.get("section_regions", parsed.get("regions"))
    if isinstance(raw_regions, list):
        regions: list[Any] = []
        for raw_region in raw_regions:
            if not isinstance(raw_region, dict):
                regions.append(raw_region)
                continue
            route_id = str(raw_region.get("route_id", "")).strip()
            section_id = str(raw_region.get("section_id", "")).strip()
            identity = identities.get((route_id, section_id))
            if identity is None:
                regions.append(raw_region)
                continue
            updated = dict(raw_region)
            for name in ("region_id", "owner_id"):
                value = identity.get(name, "")
                if value and updated.get(name) != value:
                    updated[name] = value
                    changed = True
            for name, value in selector_manifest.get((route_id, section_id), {}).items():
                if updated.get(name) != value:
                    updated[name] = value
                    changed = True
            regions.append(updated)
        if changed or "section_regions" in parsed:
            result["section_regions"] = regions
        elif "regions" in parsed:
            result["regions"] = regions

    raw_moves = parsed.get("distinctive_moves")
    if isinstance(raw_moves, list):
        moves: list[Any] = []
        for raw_move in raw_moves:
            if not isinstance(raw_move, dict):
                moves.append(raw_move)
                continue
            key = (
                str(raw_move.get("route_id", "")).strip(),
                str(raw_move.get("section_id", "")).strip(),
            )
            identity = identities.get(key)
            if identity is None or raw_move.get("region_id") == identity.get("region_id"):
                moves.append(raw_move)
                continue
            updated = dict(raw_move)
            updated["region_id"] = identity["region_id"]
            moves.append(updated)
            changed = True
        result["distinctive_moves"] = moves
    return result if changed else parsed


def _canonicalize_v4_reserved_color_tokens(parsed: Any) -> Any:
    """Rename raw colors that would collide with fixed shadcn slot aliases.

    The schema keeps its collision guard as a final safety net.  This
    pre-validation pass only renames the provider's raw token and rewrites
    typed references, preserving both the concrete color value and the
    semantic binding (for example ``accent`` -> ``palette-accent``).
    """

    if not isinstance(parsed, dict) or not isinstance(parsed.get("tokens"), dict):
        return parsed
    tokens = parsed["tokens"]
    colors = tokens.get("colors")
    bindings = tokens.get("shadcn_theme_bindings")
    if not isinstance(colors, list) or not isinstance(bindings, dict):
        return parsed
    reserved = set(SHADCN_THEME_SLOTS)
    existing = {
        str(item.get("name", ""))
        for item in colors
        if isinstance(item, dict) and str(item.get("name", ""))
    }
    rename: dict[str, str] = {}
    for raw_color in colors:
        if not isinstance(raw_color, dict):
            continue
        name = str(raw_color.get("name", "")).strip()
        if name not in reserved or name not in bindings:
            continue
        candidate = f"palette-{name}"
        suffix = 2
        while candidate in existing or candidate in reserved:
            candidate = f"palette-{name}-{suffix}"
            suffix += 1
        rename[name] = candidate
        existing.add(candidate)
    if not rename:
        return parsed

    result = dict(parsed)
    result_tokens = dict(tokens)
    result_tokens["colors"] = [
        {**item, "name": rename.get(str(item.get("name", "")), item.get("name"))}
        if isinstance(item, dict)
        else item
        for item in colors
    ]
    result_tokens["shadcn_theme_bindings"] = {
        slot: rename.get(str(value), value) for slot, value in bindings.items()
    }
    for field_name in ("borders", "shadows"):
        values = result_tokens.get(field_name)
        if isinstance(values, list):
            result_tokens[field_name] = [
                {
                    **item,
                    "color_token": rename.get(
                        str(item.get("color_token")), item.get("color_token")
                    ),
                }
                if isinstance(item, dict)
                else item
                for item in values
            ]
    result["tokens"] = result_tokens
    return result


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
