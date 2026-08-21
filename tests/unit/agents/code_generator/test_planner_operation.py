from types import SimpleNamespace

import pytest

import oryxenai.agents.code_generator.core.planner_operation as planner_operation
from oryxenai.agents.code_generator.core.development_planner import SitePlanValidationError
from oryxenai.agents.code_generator.core.planner_operation import run_planner_operation


class _RetryingPlanner:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def generate_structured(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(str(kwargs["instructions"]))
        if len(self.calls) == 1:
            return SimpleNamespace(parsed_output={})
        return SimpleNamespace(parsed_output={"plan_id": "plan-retry", "routes": []})


@pytest.mark.asyncio
async def test_planner_retries_structural_output_once() -> None:
    planner = _RetryingPlanner()

    plan, _prompt_version, _receipt, _result = await run_planner_operation(
        planner,  # type: ignore[arg-type]
        context={"input_hashes": [], "owned_paths": []},
        profile_name="code_generator_planner",
    )

    assert plan.plan_id == "plan-retry"
    assert len(planner.calls) == 2
    assert "previous planner response" in planner.calls[1]
    assert "plan_id" in planner.calls[1]


@pytest.mark.asyncio
async def test_planner_retries_semantic_output_once(monkeypatch) -> None:
    class _SemanticRetryingPlanner:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def generate_structured(self, **kwargs: object) -> SimpleNamespace:
            self.calls.append(str(kwargs["instructions"]))
            return SimpleNamespace(parsed_output={"plan_id": "plan-retry", "routes": []})

    planner = _SemanticRetryingPlanner()
    calls = 0

    def validate(plan, projections, *, max_work_units, require_blueprint):
        del projections, max_work_units, require_blueprint
        nonlocal calls
        calls += 1
        if calls == 1:
            raise SitePlanValidationError(
                "PLAN_SHARED_COMPONENTS",
                "Shared components must be owned by the route composer.",
            )
        return plan

    monkeypatch.setattr(
        planner_operation,
        "compile_site_plan",
        lambda plan, projections, **_: plan,
    )
    monkeypatch.setattr(planner_operation, "validate_site_plan", validate)

    plan, _prompt_version, _receipt, _result = await run_planner_operation(
        planner,  # type: ignore[arg-type]
        context={"input_hashes": [], "owned_paths": []},
        profile_name="code_generator_planner",
        projections={},
    )

    assert plan.plan_id == "plan-retry"
    assert len(planner.calls) == 2
    assert "PLAN_SHARED_COMPONENTS" in planner.calls[1]
