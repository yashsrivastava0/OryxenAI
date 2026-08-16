"""Request/response schemas for the Code Generator agent surface.

The agent exposes the planner operation of the standalone workflow through
the shared Agent protocol: it takes a canonical planner context (plus,
optionally, the admitted pack projections for deep semantic validation) and
returns a schema-validated ``SitePlan``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CodeGeneratorRequest(BaseModel):
    """Input for the Code Generator agent's structured planner operation."""

    planner_context: dict[str, Any] = Field(default_factory=dict)
    # Optional admitted pack projections; when present the plan must also pass
    # full semantic validation (route/fact/criteria coverage, work graph).
    projections: dict[str, Any] = Field(default_factory=dict)
    model_profile: str = "code_generator_planner"
    max_work_units: int = 64


class CodeGeneratorResponse(BaseModel):
    """Summary of the validated SitePlan produced by the planner operation."""

    plan: dict[str, Any] = Field(default_factory=dict)
    plan_id: str = ""
    route_ids: list[str] = Field(default_factory=list)
    work_unit_ids: list[str] = Field(default_factory=list)
