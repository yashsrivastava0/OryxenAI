"""Unit tests for the state service and safe error serialization."""

from __future__ import annotations

from oryxenai.agents.shared.contracts import AgentError
from oryxenai.runtime.state_service import (
    get_agent_state,
    merge_agent_output,
    next_revision,
)


def test_merge_agent_output_creates_agents_namespace():
    """Merging into empty state creates the agents namespace."""
    state = {}
    result = merge_agent_output(state, "discovery", "run-1", {"summary": "s"})
    assert "agents" in result
    assert result["agents"]["discovery"]["latestRunId"] == "run-1"
    assert result["agents"]["discovery"]["output"] == {"summary": "s"}


def test_merge_agent_output_preserves_other_agents():
    """Merging for one agent does not remove another agent's state."""
    state = {"agents": {"discovery": {"latestRunId": "run-1", "output": {"summary": "old"}}}}
    result = merge_agent_output(state, "content_architect", "run-2", {"sections": []})
    assert result["agents"]["discovery"]["output"] == {"summary": "old"}
    assert result["agents"]["content_architect"]["latestRunId"] == "run-2"


def test_merge_agent_output_overwrites_same_agent():
    """Merging for the same agent replaces its previous output."""
    state = {"agents": {"discovery": {"latestRunId": "run-1", "output": {"summary": "old"}}}}
    result = merge_agent_output(state, "discovery", "run-2", {"summary": "new"})
    assert result["agents"]["discovery"]["latestRunId"] == "run-2"
    assert result["agents"]["discovery"]["output"] == {"summary": "new"}


def test_merge_agent_output_does_not_mutate_input():
    """The input state dict is not modified."""
    state = {"agents": {"discovery": {"output": {}}}}
    merge_agent_output(state, "discovery", "run-1", {"summary": "s"})
    assert state["agents"]["discovery"]["output"] == {}


def test_merge_agent_output_preserves_top_level_keys():
    """Top-level keys like 'revision' are preserved."""
    state = {"revision": 5, "agents": {}}
    result = merge_agent_output(state, "discovery", "run-1", {})
    assert result["revision"] == 5


def test_get_agent_state_returns_none_when_absent():
    """Returns None when the agent namespace doesn't exist."""
    assert get_agent_state({}, "discovery") is None
    assert get_agent_state({"agents": {}}, "discovery") is None
    assert get_agent_state({"agents": {"discovery": {}}}, "content_architect") is None


def test_get_agent_state_returns_node():
    assert get_agent_state({"agents": {"discovery": {"latestRunId": "r1"}}}, "discovery") == {
        "latestRunId": "r1"
    }


def test_next_revision_increments():
    assert next_revision(0) == 1
    assert next_revision(5) == 6
    assert next_revision(100) == 101


def test_agent_error_to_payload():
    """AgentError serializes to a safe structured payload."""
    err = AgentError(code="TEST_ERROR", message="Something went wrong.")
    payload = err.to_payload()
    assert payload["code"] == "TEST_ERROR"
    assert payload["message"] == "Something went wrong."
    assert payload["details"] == {}


def test_agent_error_with_details():
    err = AgentError(
        code="VALIDATION_ERROR", message="Invalid input", details={"field": "agentKey"}
    )
    payload = err.to_payload()
    assert payload["details"]["field"] == "agentKey"
    # No stack trace or secret in the payload.
    assert "Traceback" not in str(payload)
    assert "password" not in str(payload).lower()
