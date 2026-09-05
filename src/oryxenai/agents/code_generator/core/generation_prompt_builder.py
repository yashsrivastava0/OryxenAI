"""Receipt-bound prompt assembly for Code Generator source operations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from oryxenai.agents.code_generator.core.development_schemas import (
    GenerationContextReceipt,
    GenerationResult,
)
from oryxenai.agents.code_generator.core.generation_contract import (
    render_contract_instructions,
)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_VERSIONS = {
    "director": "code_generator.director.v3",
    "planner_v4": "code_generator.planner.v12",
    "planner_legacy": "code_generator.planner.v7",
    "foundation": "code_generator.foundation_compat.v1",
    "route_batch": "code_generator.route_batch.v8",
    "route_compose": "code_generator.route_compose.v6",
    "integrate": "code_generator.integrate.v6",
    "integration_review": "code_generator.integration_review.v1",
    "repair": "code_generator.repair.v8",
}
_FILES = {
    "director": "director.md",
    "planner_v4": "planner.md",
    "planner_legacy": "planner_legacy.md",
    "foundation": "foundation_compat.md",
    "route_batch": "route_batch.md",
    "route_compose": "route_compose.md",
    "integrate": "integrate.md",
    "integration_review": "integration_review.md",
    "repair": "repair_source.md",
}

# Stable-first wire-payload ordering, passed to ModelClient.generate_structured
# as request_context={"key_order": ...}. This does not change the JSON shape a
# model sees (same flat keys, same nesting) — only the order the OpenAI-
# compatible adapter serializes them in. Placing content that repeats
# byte-for-byte across many calls in one run (the compiled site/visual/
# resource contract, the frozen foundation source files) before per-call
# content (plan/diagnostics/unit-specific slices) maximizes whatever
# provider-side prefix caching the configured gateway performs. Listing a key
# here is an optimization hint only: any key not listed is still sent,
# appended afterward in its original order — omitting one only forfeits a
# caching opportunity, it never drops data.
PLANNER_FOUNDATION_KEY_ORDER: tuple[str, ...] = (
    "site_contract",
    "navigation_contract",
    "visual_direction",
    "resource_bindings",
    "target_contract",
    "content_key_manifest",
    "blueprint_identity_manifest",
    "blueprint_selector_manifest",
    "receipt",
    "role_profile",
)

ROUTE_UNIT_KEY_ORDER: tuple[str, ...] = (
    "workspace_api",
    "role_profile",
    "operation",
    "shared_source",
    "site_contract",
    "visual_direction",
    "resource_bindings",
    "execution_contract",
    "plan",
    "generation_contract",
    "output_ceiling",
)

FINAL_REPAIR_KEY_ORDER: tuple[str, ...] = (
    "role_profile",
    "operation",
    "plan",
    "generation_contract",
    "candidate_identity",
    "output_ceiling",
)

# The whole-site integration review is the one call site this ordering hint
# was missing entirely (up to ~600,000 chars of context, up to ~8 calls in
# one run -- the single most expensive, most frequently repeated call in
# the pipeline). Order matters more here than for the tuples above: "round"
# and "source_manifest" both change on virtually every call (a fresh round
# number; a per-file hash list that changes whenever any file changes from
# a repair), so either one placed early would break the shared byte-prefix
# at that point on every single round, forfeiting the cache benefit for
# everything placed after it -- including the large, run-invariant
# creative_direction/experience_blueprint/work_graph/execution_bindings
# content. Keep the always-changing scalars last, immediately before the
# large assembled_source file-content dict (whose own internal ordering is
# already lexicographically stable across rounds via the same directory
# traversal source_manifest itself uses, so no extra sort is needed there).
INTEGRATION_REVIEW_KEY_ORDER: tuple[str, ...] = (
    "role_profile",
    "trusted_build_runtime",
    "creative_direction",
    "experience_blueprint",
    "work_graph",
    "execution_bindings",
    "design_realization_contracts",
    "round",
    "source_manifest",
    "assembled_source",
)


def build_instructions(
    operation: str,
    context: dict[str, Any],
    *,
    output_model: type[BaseModel] = GenerationResult,
    allow_accepted_result: bool = False,
) -> tuple[str, str, GenerationContextReceipt]:
    if operation not in _FILES:
        raise ValueError(f"Unknown Code Generator operation: {operation}")
    system = _read("system.md")
    operation_prompt = _read(_FILES[operation])
    contract = context.get("generation_contract")
    contract_block = (
        render_contract_instructions(contract) if isinstance(contract, dict) and contract else ""
    )
    schema = json.dumps(output_model.model_json_schema(), ensure_ascii=False, sort_keys=True)
    # Keep receipt accounting identical to the orchestrator's preflight
    # ceiling check. Whitespace is not part of the provider payload contract,
    # and counting it here made receipts report a larger context than the
    # value that was actually admitted.
    serialized = json.dumps(
        context,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    task = (
        f"{operation_prompt}\n\n"
        + (f"{contract_block}\n\n" if contract_block else "")
        + "Return exactly one JSON object. The transport enforces the declared output schema; "
        "do not include prose, Markdown, or reasoning outside that object."
    )
    # Do not infer accepted-result authority from the operation label. The
    # same label can be reused by a retry whose current source is not
    # acceptable, and _model_result validates every such response with
    # forbid_accepted_result=True. A caller that truly reviews an existing
    # source must opt in explicitly; fresh generation and repair calls stay
    # fail-closed by default.
    accepted_valid = bool(allow_accepted_result) and not bool(context.get("forbid_accepted_result"))
    mode_choices = (
        "changes/requests/accepted/cannot_complete"
        if accepted_valid
        else "changes/requests/cannot_complete"
    )
    if output_model is GenerationResult:
        task += (
            "\nCopy the input's context_receipt_hash value EXACTLY, unchanged, into "
            "based_on_context_receipt.\n"
            f"Set mode to exactly one of {mode_choices}; every payload "
            "field that does not match your mode MUST be null."
        )
        if not accepted_valid:
            if context.get("forbid_accepted_result"):
                task += (
                    " This is a failed final-verification candidate, so mode=accepted is "
                    "forbidden; return mode=changes with a bounded correction or "
                    "mode=cannot_complete with the precise gap."
                )
            else:
                task += (
                    " This unit has not been generated before, so mode=accepted is never a "
                    "valid choice here."
                )
    elif output_model.__name__ == "SourceGenerationEnvelopeV2":
        task += (
            f"\nSet result_tag to exactly one of {mode_choices}. "
            "Always include files, exported_signatures, content_ids, criterion_ids, "
            "resource_slot_ids, interaction_ids, resource_requests, dependency_requests, "
            "and failure_details as separate arrays; "
            "use empty arrays when a result kind does not need that payload."
        )
        if not accepted_valid:
            if context.get("forbid_accepted_result"):
                task += (
                    " This is a failed final-verification candidate, so result_tag=accepted "
                    "is forbidden; return result=changes with a bounded correction or "
                    "result=cannot_complete with the precise gap."
                )
            else:
                task += (
                    " This unit has not been generated before, so result_tag=accepted is never "
                    "a valid choice here."
                )
    context_hash = _hash(context)
    schema_hash = hashlib.sha256(schema.encode("utf-8")).hexdigest()
    operation_version = _VERSIONS[operation]
    if output_model.__name__ == "SourceGenerationEnvelopeV2":
        operation_version = f"{operation_version}.v4"
    receipt = GenerationContextReceipt(
        receipt_id=f"context-{context_hash[:20]}",
        operation_id=operation,
        role_profile=str(context.get("role_profile", "")),
        prompt_versions={
            "system": "code_generator.system.v4",
            "operation": operation_version,
            "system_hash": _hash(system),
            # Hash the full composed instructions so a changed contract block
            # invalidates cached model calls, not just a changed prompt file.
            "operation_hash": _hash(task),
        },
        output_schema_hash=schema_hash,
        ordered_input_hashes=[str(value) for value in context.get("input_hashes", [])],
        owned_paths=[str(value) for value in context.get("owned_paths", [])],
        context_hash=context_hash,
        context_estimate=len(serialized),
        output_ceiling=int(context.get("output_ceiling", 0) or 0),
    )
    return system, task, receipt


def _read(name: str) -> str:
    path = _PROMPTS_DIR / name
    if not path.is_file():
        raise ValueError(f"Code Generator prompt is missing: {name}")
    return path.read_text(encoding="utf-8").strip()


def _hash(value: object) -> str:
    if isinstance(value, str):
        data = value.encode("utf-8")
    else:
        data = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


__all__ = [
    "FINAL_REPAIR_KEY_ORDER",
    "PLANNER_FOUNDATION_KEY_ORDER",
    "ROUTE_UNIT_KEY_ORDER",
    "build_instructions",
]
