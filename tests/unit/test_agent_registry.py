"""Unit tests for the agent registry."""

from __future__ import annotations

import pytest

from oryxenai.agents.shared.contracts import AgentKey
from oryxenai.agents.shared.registry import AgentNotFoundError, default_registry


def test_default_registry_has_five_agents():
    """The default registry registers all five deterministic/mock agents."""
    reg = default_registry()
    keys = set(reg.list_keys())
    assert keys == {
        AgentKey.DISCOVERY,
        AgentKey.CONTENT_ARCHITECT,
        AgentKey.VISUAL_DESIGN_DIRECTOR,
        AgentKey.BUILD_PREPARATION,
        AgentKey.CODE_GENERATOR,
    }


def test_registry_get_known_agent():
    """Getting a known agent returns its implementation."""
    reg = default_registry()
    agent = reg.get(AgentKey.DISCOVERY)
    assert agent.key == AgentKey.DISCOVERY


def test_registry_get_by_string():
    """Getting by string key also works."""
    reg = default_registry()
    agent = reg.get("discovery")
    assert agent.key == AgentKey.DISCOVERY


def test_registry_unknown_agent_raises():
    """An unknown agent key raises AgentNotFoundError, not KeyError."""
    reg = default_registry()
    with pytest.raises(AgentNotFoundError) as exc_info:
        reg.get("nonexistent_agent")
    assert exc_info.value.error.code == "AGENT_NOT_FOUND"
    assert "nonexistent_agent" in exc_info.value.error.message


def test_registry_has_known_and_unknown():
    reg = default_registry()
    assert reg.has("discovery")
    assert not reg.has("nonexistent")
