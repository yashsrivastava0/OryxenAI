from __future__ import annotations

import pytest
from pydantic import BaseModel

from oryxenai.agents.discovery.schemas import StructuredModelResult
from oryxenai.agents.shared.model_execution import RoutedModelClient
from oryxenai.agents.shared.model_runtime import ModelRuntime
from oryxenai.agents.shared.model_usage import ModelUsageLedger
from oryxenai.agents.shared.providers.errors import (
    ModelCapacityUnavailableError,
    ModelOutputInvalidError,
    ModelUsagePersistenceError,
    ProviderAuthError,
    ProviderConfigError,
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
        self.requests: list[dict[str, object]] = []

    async def generate_structured(self, **_kwargs: object) -> StructuredModelResult:
        self.calls += 1
        self.requests.append(dict(_kwargs))
        return self.result


class _FailingClient(_FakeClient):
    def __init__(self, error: BaseException) -> None:
        super().__init__()
        self.error = error

    async def generate_structured(self, **_kwargs: object) -> StructuredModelResult:
        self.calls += 1
        self.requests.append(dict(_kwargs))
        raise self.error


@pytest.mark.asyncio
async def test_capacity_rejection_uses_one_shared_fallback_without_provider_call() -> None:
    settings = get_settings()
    runtime = ModelRuntime(settings.models)
    ledger = ModelUsageLedger()
    primary = _FakeClient()
    fallback = _FakeClient()
    clients = {
        "experiential_luna": primary,
        "gemini_flash_lite_1": fallback,
        "gemini_flash_lite_2": fallback,
        "gemini_flash_lite_3": fallback,
    }
    runtime.resolve_profile_client = lambda name: clients[name]  # type: ignore[method-assign]

    reservations: list[str] = []

    async def reserve(**kwargs: object) -> str:
        route = kwargs["route"]
        profile_name = route.profile_name
        if profile_name == "experiential_luna":
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
    assert reservations[0].startswith("gemini_flash_lite_")
    assert client.budget.transmissions == 1
    assert client.budget.recovery_used == 1


@pytest.mark.asyncio
async def test_usage_persistence_failure_is_terminal_and_never_rotates_provider() -> None:
    settings = get_settings()
    runtime = ModelRuntime(settings.models)
    ledger = ModelUsageLedger()
    clients = {
        "experiential_luna": _FakeClient(),
        "gemini_flash_lite_1": _FakeClient(),
        "gemini_flash_lite_2": _FakeClient(),
        "gemini_flash_lite_3": _FakeClient(),
    }
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
        "experiential_luna": primary,
        "gemini_flash_lite_1": fallback,
        "gemini_flash_lite_2": fallback,
        "gemini_flash_lite_3": fallback,
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


@pytest.mark.asyncio
async def test_primary_auth_failure_uses_gemini_fallback_for_personal_input() -> None:
    settings = get_settings()
    runtime = ModelRuntime(settings.models)
    ledger = ModelUsageLedger()
    primary = _FailingClient(ProviderAuthError())
    fallback = _FakeClient()
    runtime.resolve_profile_client = lambda name: {
        "experiential_luna": primary,
        "gemini_flash_1": fallback,
        "gemini_flash_2": fallback,
        "gemini_flash_3": fallback,
    }[name]  # type: ignore[method-assign]

    client = RoutedModelClient(
        runtime,
        "discovery",
        input_classification="personal",
        usage_ledger=ledger,
    )
    result = await client.generate_structured(
        operation="build_or_revise_brief",
        instructions="Return an object.",
        input_payload={"input_classification": "personal", "value": "approved packet"},
        output_model=_Output,
    )

    assert result.parsed_output == {"ok": True}
    assert primary.calls == 1
    assert fallback.calls == 1
    assert fallback.requests[0]["input_payload"] == {
        "input_classification": "personal",
        "value": "approved packet",
    }
    assert client.budget.recovery_used == 1
    assert result.telemetry["provider"] == "gemini"
    assert result.telemetry["fallback_attempt"] == 1


@pytest.mark.asyncio
async def test_primary_structural_failure_uses_gemini_fallback_before_returning_error() -> None:
    settings = get_settings()
    runtime = ModelRuntime(settings.models)
    ledger = ModelUsageLedger()
    primary = _FakeClient(
        StructuredModelResult(parsed_output={"ok": False}, model="fake", finish_reason="stop")
    )
    fallback = _FakeClient()
    runtime.resolve_profile_client = lambda name: {
        "experiential_luna": primary,
        "gemini_flash_1": fallback,
        "gemini_flash_2": fallback,
        "gemini_flash_3": fallback,
    }[name]  # type: ignore[method-assign]

    client = RoutedModelClient(
        runtime,
        "content_architect",
        input_classification="personal",
        usage_ledger=ledger,
    )

    def validate(parsed: dict[str, object]) -> None:
        if parsed.get("ok") is not True:
            raise ValueError("required structure is missing")

    result = await client.generate_structured(
        operation="plan_content",
        instructions="Return an object.",
        input_payload={"input_classification": "personal"},
        output_model=_Output,
        result_validator=validate,
    )

    assert result.parsed_output == {"ok": True}
    assert primary.calls == 1
    assert fallback.calls == 1
    assert any(event.get("error_code") == "MODEL_OUTPUT_INVALID" for event in ledger.events)


@pytest.mark.asyncio
async def test_both_provider_structural_failures_return_model_output_error() -> None:
    settings = get_settings()
    runtime = ModelRuntime(settings.models)
    ledger = ModelUsageLedger()
    primary = _FakeClient(
        StructuredModelResult(parsed_output={"ok": False}, model="fake", finish_reason="stop")
    )
    fallback = _FakeClient(
        StructuredModelResult(parsed_output={"ok": False}, model="fake", finish_reason="stop")
    )
    runtime.resolve_profile_client = lambda name: {
        "experiential_luna": primary,
        "gemini_flash_1": fallback,
        "gemini_flash_2": fallback,
        "gemini_flash_3": fallback,
    }[name]  # type: ignore[method-assign]

    client = RoutedModelClient(
        runtime,
        "content_architect",
        input_classification="personal",
        usage_ledger=ledger,
    )

    def validate(parsed: dict[str, object]) -> None:
        if parsed.get("ok") is not True:
            raise ValueError("required structure is missing")

    with pytest.raises(ModelOutputInvalidError):
        await client.generate_structured(
            operation="plan_content",
            instructions="Return an object.",
            input_payload={"input_classification": "personal"},
            output_model=_Output,
            result_validator=validate,
        )

    assert primary.calls == 1
    assert fallback.calls == 1
    assert client.budget.recovery_used == 1


@pytest.mark.asyncio
async def test_primary_configuration_failure_uses_gemini_fallback() -> None:
    settings = get_settings()
    runtime = ModelRuntime(settings.models)
    ledger = ModelUsageLedger()
    fallback = _FakeClient()

    def resolve_profile(name: str) -> _FakeClient:
        if name == "experiential_luna":
            raise ProviderConfigError("EXPLABS_API_KEY is unavailable")
        return fallback

    runtime.resolve_profile_client = resolve_profile  # type: ignore[method-assign]
    client = RoutedModelClient(
        runtime,
        "discovery",
        input_classification="personal",
        usage_ledger=ledger,
    )

    result = await client.generate_structured(
        operation="build_or_revise_brief",
        instructions="Return an object.",
        input_payload={"input_classification": "personal", "resume": "approved details"},
        output_model=_Output,
    )

    assert result.parsed_output == {"ok": True}
    assert fallback.calls == 1
    assert fallback.requests[0]["input_payload"] == {
        "input_classification": "personal",
        "resume": "approved details",
    }
    assert client.budget.transmissions == 1
    assert client.budget.recovery_used == 1
