"""Bounded text-only resource-scout context assembly and selection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from oryxenai.agents.code_generator.core.acquisition_validators import (
    AcquisitionValidationError,
    select_candidate,
)
from oryxenai.agents.code_generator.core.development_schemas import (
    ResourceCandidate,
    ResourceRequest,
)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_SCOUT_OPERATION = "code_generator.resource_scout"


class ScoutSelection(BaseModel):
    """The scout's only authority: pick one already-vetted candidate ID."""

    model_config = ConfigDict(extra="forbid")

    selected_id: str
    rationale: str = ""


def build_resource_scout_context(
    request: ResourceRequest, candidates: list[ResourceCandidate]
) -> dict[str, Any]:
    """Return metadata only; resource bytes and provider clients never enter context."""

    return {
        "request_text": {
            "category": request.category,
            "purpose": request.placement.purpose,
            "positive_terms": request.query.positive_terms,
            "negative_terms": request.query.negative_terms,
            "requiredness": request.requiredness,
        },
        "candidate_summaries": [
            {
                "candidate_id": candidate.candidate_id,
                "provider_key": candidate.provider_key,
                "title": candidate.title,
                "description": candidate.description,
                "tags": candidate.tags,
                "technical_metadata": candidate.technical_metadata,
                "canonical_source": candidate.canonical_source,
                "licence": candidate.licence,
                "attribution": candidate.attribution,
                "vendoring_policy": candidate.vendoring_policy,
                "dependency_metadata": candidate.dependency_metadata,
            }
            for candidate in candidates
        ],
    }


async def select_candidate_with_scout(
    scout: Any,
    request: ResourceRequest,
    candidates: list[ResourceCandidate],
    *,
    profile_name: str = "code_generator_resource_scout",
) -> tuple[str, str]:
    """Model-assisted selection over policy-filtered metadata.

    Falls back to the deterministic scorer when no scout client is available;
    a scout answer naming an unknown candidate is a hard validation failure,
    never silently repaired.
    """

    if scout is None or not candidates:
        return select_candidate(request, candidates)
    system_prompt = (_PROMPTS_DIR / "resource_scout.md").read_text(encoding="utf-8").strip()
    task_prompt = (_PROMPTS_DIR / "resource_scout_task.md").read_text(encoding="utf-8").strip()
    context = build_resource_scout_context(request, candidates)
    result = await scout.generate_structured(
        operation=_SCOUT_OPERATION,
        instructions=(
            f"{task_prompt}\n\n"
            "Return exactly one JSON object. The transport enforces the declared output schema; "
            "do not include prose, Markdown, or reasoning outside that object."
        ),
        input_payload=context,
        output_model=ScoutSelection,
        system_prompt=system_prompt,
        model_profile=profile_name,
        strict_schema=True,
    )
    parsed = getattr(result, "parsed_output", result)
    selection = ScoutSelection.model_validate(parsed)
    if selection.selected_id not in {candidate.candidate_id for candidate in candidates}:
        raise AcquisitionValidationError(
            "SCOUT_SELECTION_INVALID", "The resource scout selected an unknown candidate."
        )
    return selection.selected_id, selection.rationale or "model-selected candidate"
