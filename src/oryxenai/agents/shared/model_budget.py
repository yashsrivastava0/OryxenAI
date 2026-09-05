"""Bounded configured-cost wrapper for live structured model calls.

The normal durable cache avoids repeated calls.  This wrapper is for an
explicitly bounded run: it reserves a conservative prompt estimate and the
maximum completion charge before a provider request, then settles the reserve
from returned telemetry.  Unknown or failed calls consume their reservation
so a retry cannot silently spend past the caller's ceiling.
"""

from __future__ import annotations

import asyncio
import json
import math
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from oryxenai.agents.shared.contracts import ModelClient
from oryxenai.agents.shared.providers.errors import ProviderConfigError, ProviderError

_PROMPT_OVERHEAD_BYTES = 4096
_MIN_COMPLETION_TOKENS = 256


class ModelCostBudget:
    """Mutable budget shared by every call in one explicitly bounded run."""

    def __init__(self, ceiling: float, *, spent: float = 0.0) -> None:
        if ceiling <= 0:
            raise ValueError("ceiling must be positive")
        if spent < 0:
            raise ValueError("spent must not be negative")
        self.ceiling = float(ceiling)
        self.spent = float(spent)
        self.reserved = 0.0
        self.calls = 0

    @property
    def available(self) -> float:
        return self.ceiling - self.spent - self.reserved

    def reserve(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("reservation must be positive")
        if amount > self.available + 1e-12:
            raise ModelBudgetExceededError(
                ceiling=self.ceiling,
                spent=self.spent + self.reserved,
                requested=amount,
            )
        self.reserved += amount

    def settle(self, reservation: float, actual: float | None) -> None:
        self.reserved = max(0.0, self.reserved - reservation)
        # A missing/invalid provider estimate is treated as the full reserve.
        # A valid result normally costs less than its conservative reservation,
        # so releasing that difference lets the same hard-capped run finish
        # later stages without giving up the pre-call safety guarantee. If a
        # provider reports more than the reservation, keep the overrun visible
        # and prevent any later call from being admitted.
        charge = (
            reservation
            if actual is None or not math.isfinite(actual) or actual < 0
            else max(actual, 0.0)
        )
        self.spent += charge
        self.calls += 1


class ModelBudgetExceededError(ProviderError):
    """No safe completion budget remains for another provider request."""

    def __init__(self, *, ceiling: float, spent: float, requested: float) -> None:
        super().__init__(
            "The configured live model-cost ceiling does not have enough safe budget "
            "for another request.",
            code="MODEL_COST_BUDGET_EXCEEDED",
            retryable=False,
            details={
                "ceiling": round(ceiling, 6),
                "spent": round(spent, 6),
                "requested": round(requested, 6),
            },
        )


class BudgetedModelClient:
    """Serialize and bound calls made through one provider client.

    The provider adapters read ``max_output_tokens`` from their configured
    profile.  This wrapper temporarily lowers that field for the in-flight
    call and restores it immediately, so the source profile remains unchanged
    and concurrent calls cannot race through the same budget.
    """

    def __init__(
        self,
        client: ModelClient,
        *,
        profile: Any,
        budget: ModelCostBudget,
    ) -> None:
        self._client = client
        self._profile = profile
        self._budget = budget
        self._lock = asyncio.Lock()

    async def complete(
        self,
        system_prompt: str,
        task_prompt: str,
        request_params: dict[str, Any] | None = None,
    ) -> str:
        # Plain completions do not expose a provider-neutral token override in
        # the ModelClient contract. Refuse rather than make an uncapped call.
        del system_prompt, task_prompt, request_params
        raise ModelBudgetExceededError(
            ceiling=self._budget.ceiling,
            spent=self._budget.spent,
            requested=self._budget.available,
        )

    async def generate_structured(
        self,
        *,
        operation: str,
        instructions: str,
        input_payload: Mapping[str, object],
        output_model: type[BaseModel],
        system_prompt: str | None = None,
        model_profile: Any = None,
        request_context: Any = None,
        strict_schema: bool = False,
    ) -> Any:
        del model_profile
        async with self._lock:
            prompt_cost = self._conservative_prompt_cost(
                operation=operation,
                instructions=instructions,
                input_payload=input_payload,
                output_model=output_model,
                system_prompt=system_prompt,
            )
            pricing = getattr(self._profile, "pricing", None)
            rates = self._pricing_rates(pricing)
            _input_rate, output_rate = rates
            available = self._budget.available
            if available <= prompt_cost:
                raise ModelBudgetExceededError(
                    ceiling=self._budget.ceiling,
                    spent=self._budget.spent + self._budget.reserved,
                    requested=prompt_cost,
                )
            completion_tokens = int((available - prompt_cost) * 1_000_000 / output_rate)
            configured_max = max(0, int(getattr(self._profile, "max_output_tokens", 0) or 0))
            completion_tokens = min(completion_tokens, configured_max)
            if completion_tokens < _MIN_COMPLETION_TOKENS:
                raise ModelBudgetExceededError(
                    ceiling=self._budget.ceiling,
                    spent=self._budget.spent + self._budget.reserved,
                    requested=prompt_cost + (_MIN_COMPLETION_TOKENS * output_rate / 1_000_000),
                )
            reservation = prompt_cost + completion_tokens * output_rate / 1_000_000
            self._budget.reserve(reservation)
            original_max = getattr(self._profile, "max_output_tokens", None)
            self._profile.max_output_tokens = completion_tokens
            try:
                # Preserve all existing cache-key/breakpoint context. The
                # provider reads the temporary profile ceiling directly.
                result = await self._client.generate_structured(
                    operation=operation,
                    instructions=instructions,
                    input_payload=input_payload,
                    output_model=output_model,
                    system_prompt=system_prompt,
                    request_context=request_context,
                    strict_schema=strict_schema,
                )
            except Exception:
                self._budget.settle(reservation, None)
                raise
            finally:
                if original_max is not None:
                    self._profile.max_output_tokens = original_max
            self._budget.settle(reservation, self._result_cost(result))
            return result

    async def aclose(self) -> None:
        close = getattr(self._client, "aclose", None)
        if close is not None:
            await close()

    def _conservative_prompt_cost(
        self,
        *,
        operation: str,
        instructions: str,
        input_payload: Mapping[str, object],
        output_model: type[BaseModel],
        system_prompt: str | None,
    ) -> float:
        chunks = [
            operation,
            instructions,
            system_prompt or "",
            json.dumps(input_payload, ensure_ascii=False, sort_keys=True, default=str),
            json.dumps(output_model.model_json_schema(), ensure_ascii=False, sort_keys=True),
        ]
        prompt_bytes = sum(len(chunk.encode("utf-8")) for chunk in chunks)
        # UTF-8 bytes are an upper bound for ordinary provider tokenization;
        # the fixed envelope reserve covers message framing and separators.
        prompt_tokens = prompt_bytes + _PROMPT_OVERHEAD_BYTES
        prompt_rate = self._prompt_rate(getattr(self._profile, "pricing", None))
        return prompt_tokens * prompt_rate / 1_000_000

    @staticmethod
    def _pricing_rates(pricing: Any) -> tuple[float, float]:
        values = (
            pricing.model_dump(mode="json")
            if hasattr(pricing, "model_dump")
            else dict(pricing or {})
        )
        input_rate = values.get("input_per_million")
        output_rate = values.get("output_per_million")
        if not isinstance(input_rate, (int, float)) or input_rate <= 0:
            raise ProviderConfigError(
                "An explicit model-cost budget requires a positive input token rate."
            )
        if not isinstance(output_rate, (int, float)) or output_rate <= 0:
            raise ProviderConfigError(
                "An explicit model-cost budget requires a positive output token rate."
            )
        return float(input_rate), float(output_rate)

    @staticmethod
    def _prompt_rate(pricing: Any) -> float:
        values = (
            pricing.model_dump(mode="json")
            if hasattr(pricing, "model_dump")
            else dict(pricing or {})
        )
        rates = [
            values.get("input_per_million"),
            values.get("cached_input_per_million"),
            values.get("cache_write_per_million"),
        ]
        numeric = [float(rate) for rate in rates if isinstance(rate, (int, float)) and rate > 0]
        if not numeric:
            raise ProviderConfigError(
                "An explicit model-cost budget requires a positive input token rate."
            )
        # Cache writes can be priced above ordinary input tokens. Reserving at
        # the highest configured prompt rate keeps the ceiling hard even on a
        # first provider-prefix-cache write.
        return max(numeric)

    @staticmethod
    def _result_cost(result: Any) -> float | None:
        telemetry = getattr(result, "telemetry", None)
        if not isinstance(telemetry, dict):
            return None
        value = telemetry.get("estimated_cost")
        if not isinstance(value, (int, float)):
            return None
        converted = float(value)
        return converted if math.isfinite(converted) and converted >= 0 else None
