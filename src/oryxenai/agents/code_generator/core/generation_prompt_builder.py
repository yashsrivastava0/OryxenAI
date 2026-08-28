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
    "director": "code_generator.director.v2",
    "planner_v4": "code_generator.planner.v8",
    "planner_legacy": "code_generator.planner.v7",
    "route_batch": "code_generator.route_batch.v7",
    "route_compose": "code_generator.route_compose.v6",
    "integrate": "code_generator.integrate.v5",
    "integration_review": "code_generator.integration_review.v1",
    "repair": "code_generator.repair.v5",
}
_FILES = {
    "director": "director.md",
    "planner_v4": "planner.md",
    "planner_legacy": "planner_legacy.md",
    "route_batch": "route_batch.md",
    "route_compose": "route_compose.md",
    "integrate": "integrate.md",
    "integration_review": "integration_review.md",
    "repair": "repair_source.md",
}


def build_instructions(
    operation: str,
    context: dict[str, Any],
    *,
    output_model: type[BaseModel] = GenerationResult,
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
    # "accepted" only has a real meaning for an operation that reviews
    # already-generated content (integrate, repair): it means "the existing
    # source already satisfies the contract, nothing to change." For a
    # first-time generation operation (route_batch, route_compose,
    # foundation, director) there is no prior content for this unit to
    # accept, yet listing "accepted" as an equally valid, unqualified choice
    # here - appearing last, closest to the actual output - was observed
    # live to make the model choose it anyway even after prompt-level
    # guidance said not to. Excluding it from the listed choices for
    # generation-only operations is the fix that actually held.
    accepted_valid = operation in {"integrate", "repair"}
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
            task += (
                " This unit has not been generated before, so mode=accepted is never a valid "
                "choice here."
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
            task += (
                " This unit has not been generated before, so result_tag=accepted is never a "
                "valid choice here."
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


__all__ = ["build_instructions"]
