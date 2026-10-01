from __future__ import annotations

import pytest

from oryxenai.agents.shared.contracts import OperationBudget
from oryxenai.agents.shared.model_quota import CapacityRegistry, CapacitySnapshot
from oryxenai.agents.shared.model_router import ModelRouter
from oryxenai.agents.shared.providers.errors import (
    ProviderRateLimitError,
    safe_operation_failure,
)
from oryxenai.core.settings import get_settings


def test_active_routes_use_only_experiential_luna() -> None:
    settings = get_settings()
    router = ModelRouter(settings.models)

    personal = router.operation_profile_names(
        "discovery", "understand_and_question", input_classification="personal"
    )
    sanitized = router.operation_profile_names(
        "discovery", "understand_and_question", input_classification="sanitized"
    )

    assert personal == ("experiential_luna_6",)
    assert sanitized == ("experiential_luna_6",)
    assert settings.models.get_profile(personal[0]).api_key_env == "EXPLABS_API_KEY"
    assert settings.models.routing.selectable_profiles == []
    assert all(
        not source.enabled
        for source in settings.models.routing.capacity.sources.values()
        if source.provider == "gemini"
    )
    assert all(
        settings.models.get_profile(name).api_key_env != "OPENAI_API_KEY"
        for name in (*personal, *sanitized)
    )


@pytest.mark.parametrize(
    ("engine", "operation", "profile", "model"),
    [
        ("discovery", "understand_and_question", "experiential_luna_6", "gpt-6-luna"),
        ("discovery", "build_or_revise_brief", "experiential_luna_6", "gpt-6-luna"),
        ("content_architect", "plan_content", "experiential_luna_6", "gpt-6-luna"),
        ("content_architect", "write_pages", "experiential_luna_6", "gpt-6-luna"),
        ("content_architect", "integrate_content", "experiential_luna_6", "gpt-6-luna"),
    ],
)
def test_all_active_personal_operations_keep_experiential_as_primary(
    engine: str, operation: str, profile: str, model: str
) -> None:
    settings = get_settings()
    router = ModelRouter(settings.models)
    names = router.operation_profile_names(engine, operation, input_classification="personal")
    assert names
    assert settings.models.get_profile(names[0]).provider == "experiential"
    assert settings.models.get_profile(names[0]).model == model
    assert names == (profile,)
    assert settings.models.get_profile(names[0]).api_key_env == "EXPLABS_API_KEY"
    route = settings.models.routing.operation_route(engine, operation)
    assert route is not None
    assert route.fallback_profiles == []
    assert route.recovery_allowance == (1 if engine == "discovery" else 0)
    assert all(settings.models.get_profile(name).api_key_env != "OPENAI_API_KEY" for name in names)


def test_unknown_input_also_uses_only_the_configured_experiential_profile() -> None:
    settings = get_settings()
    router = ModelRouter(settings.models)

    names = router.operation_profile_names(
        "content_architect",
        "plan_content",
        input_classification="unknown",
    )

    assert names == ("experiential_luna_6",)


def test_capacity_registry_uses_remaining_capacity_and_cooldown() -> None:
    registry = CapacityRegistry(0.8)
    registry.observe(
        CapacitySnapshot(
            provider="gemini",
            source_id="GEMINI_1",
            request_limit=10,
            observed_requests=7,
            confidence="observed",
        )
    )
    registry.observe(
        CapacitySnapshot(
            provider="gemini",
            source_id="GEMINI_2",
            request_limit=10,
            observed_requests=1,
            confidence="observed",
        )
    )
    assert registry.order_profiles([("lite_1", "GEMINI_1"), ("lite_2", "GEMINI_2")]) == [
        "lite_2",
        "lite_1",
    ]
    registry.mark_failure("GEMINI_2", cooldown_seconds=60)
    assert registry.order_profiles([("lite_1", "GEMINI_1"), ("lite_2", "GEMINI_2")]) == ["lite_1"]


def test_operation_budget_has_one_shared_recovery_slot() -> None:
    budget = OperationBudget(normal_calls=3, recovery_allowance=1, max_transmissions=4)
    budget.admit_normal()
    budget.admit_normal()
    budget.admit_recovery()
    budget.record_transmission()
    assert budget.normal_remaining == 1
    assert budget.recovery_remaining == 0
    with pytest.raises(RuntimeError):
        budget.admit_recovery()


def test_public_error_has_support_reference_without_secret_details() -> None:
    error = ProviderRateLimitError(retry_after_seconds=12)
    error.details["provider_label"] = "Google Gemini"
    error.details["api_key"] = "xpl_secret_should_never_escape"
    payload = safe_operation_failure(error, operation="discovery.understand_and_question")
    assert payload["provider_label"] == "Google Gemini"
    assert payload["operation_label"] == "discovery.understand_and_question"
    assert payload["retry_after_seconds"] == 12.0
    assert "xpl_secret" not in str(payload)
