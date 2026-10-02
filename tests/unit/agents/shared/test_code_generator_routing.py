"""The Code Generator engine rides the shared model layer without special cases."""

from __future__ import annotations

import json

import pytest

from oryxenai.agents.shared.contracts import AgentKey
from oryxenai.agents.shared.model_execution import RoutedModelClient
from oryxenai.agents.shared.model_router import ModelRouter
from oryxenai.agents.shared.model_runtime import ModelRuntime, validate_pipeline_job_timeouts
from oryxenai.agents.shared.providers.opencode_go import _parse_json_object
from oryxenai.core.settings import get_settings
from oryxenai.jobs.policy import policy_for


def test_code_generator_is_a_known_agent_key_and_job_kind() -> None:
    assert AgentKey.from_string("code_generator") is AgentKey.CODE_GENERATOR
    policy = policy_for("code_generator.build")
    assert policy.consumes_model_credit and policy.portfolio_bound and policy.foreground


def test_engine_budgets_come_from_the_configured_operation_routes() -> None:
    runtime = ModelRuntime(get_settings().models)
    seen = {
        engine: (
            RoutedModelClient(runtime, engine).budget.normal_calls,
            RoutedModelClient(runtime, engine).budget.recovery_allowance,
            RoutedModelClient(runtime, engine).budget.max_transmissions,
        )
        for engine in ("discovery", "content_architect", "code_generator", "not_configured")
    }
    assert seen == {
        "discovery": (1, 1, 2),
        "content_architect": (3, 0, 3),
        "code_generator": (2, 0, 2),
        "not_configured": (1, 0, 1),
    }


@pytest.mark.parametrize("operation", ["generate_page", "interpret_change"])
def test_code_generator_operations_use_only_the_configured_luna_profile(operation: str) -> None:
    settings = get_settings()
    assert settings.models.routing.engine_profiles["code_generator"] == "experiential_luna_6"
    names = ModelRouter(settings.models).operation_profile_names(
        "code_generator", operation, input_classification="personal"
    )
    assert names == ("experiential_luna_6",)
    route = settings.models.routing.operation_route("code_generator", operation)
    assert route is not None
    assert route.recovery_allowance == 0 and route.fallback_profiles == []
    assert route.max_output_tokens is not None and route.timeout_seconds is not None


def test_the_durable_job_ceiling_contains_the_code_generator_call_graph() -> None:
    validate_pipeline_job_timeouts(get_settings())


def test_json_parser_tolerates_raw_control_characters_inside_strings() -> None:
    raw = '{"lang": "en", "body_html": "<p>one\ntwo\tthree</p>"}'
    with pytest.raises(json.JSONDecodeError):
        json.loads(raw)
    assert _parse_json_object(raw) == {"lang": "en", "body_html": "<p>one\ntwo\tthree</p>"}
    assert _parse_json_object('Here you go: {"a": 1}') == {"a": 1}
    with pytest.raises(json.JSONDecodeError):
        _parse_json_object("not json at all")
