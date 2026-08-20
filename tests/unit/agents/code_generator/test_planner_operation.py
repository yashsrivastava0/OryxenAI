from types import SimpleNamespace

import pytest

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
