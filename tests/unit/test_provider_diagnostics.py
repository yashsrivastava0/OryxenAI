from __future__ import annotations

from oryxenai.agents.build_preparation.fixture_runs import _issue_from_error
from oryxenai.agents.shared.providers.errors import ProviderConnectionError
from oryxenai.jobs.handlers.code_generator import _planner_failure_issue


def test_build_preparation_connection_error_has_network_action() -> None:
    issue = _issue_from_error(
        ProviderConnectionError(
            "Could not connect to the configured model provider.",
            details={"provider": "openai", "endpoint_host": "api.openai.com"},
        )
    )

    assert issue["code"] == "PROVIDER_CONNECTION_ERROR"
    assert issue["message"].startswith("The configured OpenAI model provider could not be reached")
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
