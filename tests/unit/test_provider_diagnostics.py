from __future__ import annotations

from pydantic import ValidationError

from oryxenai.agents.build_preparation.fixture_runs import _issue_from_error
from oryxenai.agents.code_generator.core.development_schemas import ResourceReceipt
from oryxenai.agents.code_generator.core.planner_operation import PlannerOperationError
from oryxenai.agents.shared.providers.errors import ProviderConnectionError
from oryxenai.jobs.handlers.code_generator import (
    _acquisition_failure_issue,
    _planner_failure_issue,
)


def test_build_preparation_connection_error_has_network_action() -> None:
    issue = _issue_from_error(
        ProviderConnectionError(
            "Could not connect to the configured model provider.",
            details={"provider": "openai", "endpoint_host": "api.openai.com"},
        )
    )

    assert issue["code"] == "PROVIDER_CONNECTION_ERROR"
    assert issue["message"].startswith("The configured model provider could not be reached")
    assert "endpoint" in issue["next_action"]
    assert issue["details"]["endpoint_host"] == "api.openai.com"


def test_code_generator_planner_connection_error_is_not_reported_as_invalid_plan() -> None:
    issue = _planner_failure_issue(
        ProviderConnectionError(
            "Could not connect to the configured model provider.",
            details={"provider": "openai", "endpoint_host": "api.openai.com"},
        )
    )

    assert issue.code == "PROVIDER_CONNECTION_ERROR"
    assert "could not be reached" in issue.message
    assert "network" not in issue.details
    assert issue.details["endpoint_host"] == "api.openai.com"


def test_code_generator_planner_preserves_safe_validation_summary() -> None:
    issue = _planner_failure_issue(
        PlannerOperationError(
            "PLANNER_OUTPUT_INVALID",
            "experience_blueprint.routes: missing required field; work_graph: invalid dependency",
        )
    )

    assert issue.code == "PLANNER_OUTPUT_INVALID"
    assert "experience_blueprint.routes" in issue.message
    assert "invalid dependency" in issue.message


def test_code_generator_acquisition_preserves_safe_validation_summary() -> None:
    try:
        ResourceReceipt.model_validate({})
    except ValidationError as exc:
        issue = _acquisition_failure_issue(exc)
    else:  # pragma: no cover - the model must reject an empty object
        raise AssertionError("ResourceReceipt unexpectedly accepted an empty object")

    assert issue.code == "ACQUISITION_FAILED"
    assert "Acquisition produced an invalid local object" in issue.message
    assert "request_hash" in issue.details["validation_summary"]
