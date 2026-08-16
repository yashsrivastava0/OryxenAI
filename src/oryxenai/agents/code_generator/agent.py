"""Code Generator agent — structured planner operation behind the Agent protocol.

The full standalone workflow (admission, acquisition, progressive generation,
verification, repair, preview promotion) runs as three durable jobs; this
agent surface exposes its planner operation through the shared registry so
any ModelClient-driven harness executes the same trusted-prompt, strict
structured-output call the durable ``code_generator.plan`` job uses.
"""

from __future__ import annotations

from oryxenai.agents.code_generator.core.planner_operation import (
    PlannerOperationError,
    run_planner_operation,
)
from oryxenai.agents.code_generator.schemas import (
    CodeGeneratorRequest,
    CodeGeneratorResponse,
)
from oryxenai.agents.shared.contracts import Agent, AgentContext, AgentKey, AgentResult, ModelClient


class CodeGeneratorModelError(ValueError):
    """A safe, code-carrying failure of the structured planner call."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class CodeGeneratorAgent(Agent):
    """Structured planner-role agent backed by any ModelClient."""

    key = AgentKey.CODE_GENERATOR

    def __init__(self, model_client: ModelClient) -> None:
        self._model_client = model_client

    async def run(self, context: AgentContext) -> AgentResult:
        request = CodeGeneratorRequest(**context.agent_input)
        try:
            plan, prompt_version, _receipt, _result = await run_planner_operation(
                self._model_client,
                context=request.planner_context,
                profile_name=request.model_profile,
                projections=request.projections or None,
                max_work_units=request.max_work_units,
            )
        except PlannerOperationError as exc:
            raise CodeGeneratorModelError(exc.code, exc.message) from exc
        response = CodeGeneratorResponse(
            plan=plan.model_dump(mode="json"),
            plan_id=plan.plan_id,
            route_ids=[route.route_id for route in plan.routes],
            work_unit_ids=[unit.unit_id for unit in plan.work_graph.units],
        )
        return AgentResult(
            output=response.model_dump(mode="json"),
            prompt_version=prompt_version,
            model_metadata={
                "operation": "code_generator.plan",
                "profile": request.model_profile,
                "agent": self.key.value,
            },
        )
