from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from oryxenai.agents.discovery.schemas import StructuredModelResult
from oryxenai.agents.shared.model_budget import (
    BudgetedModelClient,
    ModelBudgetExceededError,
    ModelCostBudget,
)
from oryxenai.core.settings import ModelPricing


class _Output(BaseModel):
    ok: bool


class _FakeClient:
    def __init__(
        self,
        profile: SimpleNamespace,
        *,
        cost: float = 0.01,
        error: Exception | None = None,
    ) -> None:
        self.profile = profile
        self.cost = cost
        self.error = error
        self.calls = 0
        self.max_tokens_seen: list[int] = []

    async def generate_structured(self, **_kwargs: object) -> StructuredModelResult:
        self.calls += 1
        self.max_tokens_seen.append(int(self.profile.max_output_tokens))
        if self.error is not None:
            raise self.error
        return StructuredModelResult(
            parsed_output={"ok": True},
            model="fake-model",
            finish_reason="stop",
            telemetry={"estimated_cost": self.cost},
        )


def _profile(*, max_output_tokens: int = 5_000) -> SimpleNamespace:
    return SimpleNamespace(
        max_output_tokens=max_output_tokens,
        pricing=ModelPricing(
            input_per_million=5,
            cached_input_per_million=0.5,
            cache_write_per_million=6.25,
            output_per_million=30,
        ),
    )


async def _call(client: BudgetedModelClient) -> StructuredModelResult:
    return await client.generate_structured(
        operation="test.operation",
        instructions="Return the requested envelope.",
        input_payload={"value": "small"},
        output_model=_Output,
        system_prompt="Follow the envelope contract.",
    )


@pytest.mark.asyncio
async def test_success_releases_unused_reservation_and_restores_profile_cap() -> None:
    profile = _profile()
    fake = _FakeClient(profile, cost=0.01)
    budget = ModelCostBudget(0.1)
    client = BudgetedModelClient(fake, profile=profile, budget=budget)

    result = await _call(client)

    assert result.parsed_output == {"ok": True}
    assert fake.calls == 1
    assert 256 <= fake.max_tokens_seen[0] < 5_000
    assert profile.max_output_tokens == 5_000
    assert budget.spent == pytest.approx(0.01)
    assert budget.reserved == 0
    assert budget.available == pytest.approx(0.09)


@pytest.mark.asyncio
async def test_budget_refuses_before_provider_call_when_reservation_is_unsafe() -> None:
    profile = _profile()
    fake = _FakeClient(profile)
    client = BudgetedModelClient(fake, profile=profile, budget=ModelCostBudget(0.01))

    with pytest.raises(ModelBudgetExceededError) as error:
        await _call(client)

    assert error.value.code == "MODEL_COST_BUDGET_EXCEEDED"
    assert fake.calls == 0
    assert profile.max_output_tokens == 5_000


@pytest.mark.asyncio
async def test_failed_call_consumes_reservation_and_blocks_follow_up() -> None:
    profile = _profile(max_output_tokens=5_000)
    fake = _FakeClient(profile, error=RuntimeError("provider failed"))
    budget = ModelCostBudget(0.2)
    client = BudgetedModelClient(fake, profile=profile, budget=budget)

    with pytest.raises(RuntimeError, match="provider failed"):
        await _call(client)
    with pytest.raises(ModelBudgetExceededError):
        await _call(client)

    assert fake.calls == 1
    assert budget.spent > 0
    assert budget.reserved == 0
    assert profile.max_output_tokens == 5_000
