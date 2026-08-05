"""State service — merges agent results into session current_state.

Pure functions for state transformation; no database access here. The
executor orchestrates persistence and calls these helpers.
"""

from __future__ import annotations

from typing import Any


def merge_agent_output(
    current_state: dict[str, Any],
    agent_key: str,
    run_id: str,
    output: dict[str, Any],
) -> dict[str, Any]:
    """Return a new state dict with the agent output merged under agents.<key>.

    Does NOT mutate the input current_state.
    """
    new_state: dict[str, Any] = dict(current_state)
    agents_node: dict[str, Any] = dict(new_state.get("agents", {}))
    agent_node: dict[str, Any] = dict(agents_node.get(agent_key, {}))
    agent_node["latestRunId"] = run_id
    agent_node["output"] = output
    agents_node[agent_key] = agent_node
    new_state["agents"] = agents_node
    return new_state


def get_agent_state(
    current_state: dict[str, Any],
    agent_key: str,
) -> dict[str, Any] | None:
    """Return the namespaced state for an agent, or None."""
    agents_node = current_state.get("agents")
    if not isinstance(agents_node, dict):
        return None
    agent_node = agents_node.get(agent_key)
    if not isinstance(agent_node, dict):
        return None
    return agent_node


def next_revision(current_revision: int) -> int:
    """Return the next revision number (monotonic increment)."""
    return current_revision + 1
