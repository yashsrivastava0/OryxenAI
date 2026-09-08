from __future__ import annotations

import pytest
from pydantic import BaseModel

from oryxenai.agents.discovery.schemas import StructuredModelResult
from oryxenai.agents.shared.model_execution import RoutedModelClient
from oryxenai.agents.shared.model_runtime import ModelRuntime
from oryxenai.agents.shared.model_usage import ModelUsageLedger
from oryxenai.agents.shared.providers.errors import (
    ModelCapacityUnavailableError,
    ModelUsagePersistenceError,
)
from oryxenai.core.settings import get_settings


class _Output(BaseModel):
    ok: bool


class _FakeClient:
    def __init__(self, result: StructuredModelResult | None = None) -> None:
        self.result = result or StructuredModelResult(
            parsed_output={"ok": True}, model="fake", finish_reason="stop"
        )
        self.calls = 0

    async def generate_structured(self, **_kwargs: object) -> StructuredModelResult:
        self.calls += 1
        return self.result


@pytest.mark.asyncio
async def test_capacity_rejection_uses_one_shared_fallback_without_provider_call() -> None:
    settings = get_settings()
    runtime = ModelRuntime(settings.models)
    ledger = ModelUsageLedger()
    primary = _FakeClient()
    fallback = _FakeClient()
    clients = {
        "gemini_flash_lite_1": primary,
        "gemini_flash_lite_2": fallback,
    }
    runtime.resolve_profile_client = lambda name: clients[name]  # type: ignore[method-assign]

    reservations: list[str] = []

    async def reserve(**kwargs: object) -> str:
        route = kwargs["route"]
        profile_name = route.profile_name
        if profile_name == "gemini_flash_lite_1":
            error = ModelCapacityUnavailableError()
            raise error
        reservations.append(profile_name)
        return "attempt-2"

    ledger.reserve = reserve  # type: ignore[method-assign]
    async def finish(*_args: object, **_kwargs: object) -> None:
        return None

    ledger.finish = finish  # type: ignore[method-assign]

    client = RoutedModelClient(
        runtime,
        "discovery",
        input_classification="sanitized",
        usage_ledger=ledger,
    )
    result = await client.generate_structured(
        operation="understand_and_question",
        instructions="Return an object.",
        input_payload={"input_classification": "sanitized", "value": "synthetic"},
        output_model=_Output,
    )

    assert result.parsed_output == {"ok": True}
    assert primary.calls == 0
    assert fallback.calls == 1
    assert reservations == ["gemini_flash_lite_2"]
    assert client.budget.transmissions == 1
    assert client.budget.recovery_used == 1


@pytest.mark.asyncio
async def test_usage_persistence_failure_is_terminal_and_never_rotates_provider() -> None:
    settings = get_settings()
    runtime = ModelRuntime(settings.models)
    ledger = ModelUsageLedger()
    clients = {"gemini_flash_lite_1": _FakeClient(), "gemini_flash_lite_2": _FakeClient()}
    runtime.resolve_profile_client = lambda name: clients[name]  # type: ignore[method-assign]

    async def reserve(**_kwargs: object) -> str:
        raise ModelUsagePersistenceError()

    ledger.reserve = reserve  # type: ignore[method-assign]
    client = RoutedModelClient(
        runtime,
        "discovery",
        input_classification="sanitized",
        usage_ledger=ledger,
    )

    with pytest.raises(ModelUsagePersistenceError):
        await client.generate_structured(
            operation="understand_and_question",
            instructions="Return an object.",
            input_payload={"input_classification": "sanitized"},
            output_model=_Output,
        )

    assert clients["gemini_flash_lite_1"].calls == 0
    assert clients["gemini_flash_lite_2"].calls == 0


@pytest.mark.asyncio
async def test_usage_settlement_failure_is_terminal_after_provider_response() -> None:
    settings = get_settings()
    runtime = ModelRuntime(settings.models)
    ledger = ModelUsageLedger()
    primary = _FakeClient()
    fallback = _FakeClient()
    runtime.resolve_profile_client = lambda name: {
        "gemini_flash_lite_1": primary,
        "gemini_flash_lite_2": fallback,
    }[name]  # type: ignore[method-assign]

    async def finish(*_args: object, **_kwargs: object) -> None:
        raise ModelUsagePersistenceError()

    ledger.finish = finish  # type: ignore[method-assign]
    client = RoutedModelClient(
        runtime,
        "discovery",
        input_classification="sanitized",
        usage_ledger=ledger,
    )

    with pytest.raises(ModelUsagePersistenceError):
        await client.generate_structured(
            operation="understand_and_question",
            instructions="Return an object.",
            input_payload={"input_classification": "sanitized"},
            output_model=_Output,
        )

    assert primary.calls == 1
    assert fallback.calls == 0
