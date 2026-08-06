"""Agent registry — maps AgentKey to an agent implementation.

Unknown agents produce a controlled ApplicationError, never a raw KeyError.
"""

from __future__ import annotations

from oryxenai.agents.shared.contracts import Agent, AgentError, AgentKey


class AgentNotFoundError(Exception):
    """Raised when a requested agent key is not registered."""

    def __init__(self, key: str) -> None:
        self.error = AgentError(
            code="AGENT_NOT_FOUND",
            message=f"Agent '{key}' is not registered.",
            details={"key": key, "valid": [m.value for m in AgentKey]},
        )
        super().__init__(self.error.message)


class AgentRegistry:
    """Maps AgentKey -> Agent implementation."""

    def __init__(self) -> None:
        self._agents: dict[AgentKey, Agent] = {}

    def register(self, agent: Agent) -> None:
        if not hasattr(agent, "key") or not isinstance(agent.key, AgentKey):
            raise TypeError(f"agent {agent!r} must have an AgentKey 'key' attribute")
        self._agents[agent.key] = agent

    def get(self, key: AgentKey | str) -> Agent:
        if isinstance(key, AgentKey):
            resolved = key
        else:
            try:
                resolved = AgentKey.from_string(key)
            except ValueError as exc:
                raise AgentNotFoundError(key) from exc
        agent = self._agents.get(resolved)
        if agent is None:
            raise AgentNotFoundError(resolved.value)
        return agent

    def list_keys(self) -> list[AgentKey]:
        return list(self._agents.keys())

    def has(self, key: AgentKey | str) -> bool:
        resolved = key if isinstance(key, AgentKey) else _try_coerce(key)
        return resolved is not None and resolved in self._agents


def _try_coerce(key: str) -> AgentKey | None:
    try:
        return AgentKey.from_string(key)
    except ValueError:
        return None


def default_registry() -> AgentRegistry:
    """Build and return the registry with all four agents registered.

    The Discovery agent in the registry is wired to the deterministic fake
    client so the mock-runs endpoint never makes network calls. The durable
    worker builds its own agent with the real provider adapter when a key is
    configured (jobs/handlers/discovery.py).
    """
    from oryxenai.agents.code_generator.agent import CodeGeneratorAgent
    from oryxenai.agents.content_architect.agent import ContentArchitectAgent
    from oryxenai.agents.discovery.agent import DiscoveryAgent
    from oryxenai.agents.discovery.fake_client import FakeDiscoveryModelClient
    from oryxenai.agents.visual_design_director.agent import VisualDesignDirectorAgent

    registry = AgentRegistry()

    registry.register(DiscoveryAgent(model_client=FakeDiscoveryModelClient()))

    registry.register(ContentArchitectAgent())
    registry.register(VisualDesignDirectorAgent())
    registry.register(CodeGeneratorAgent())
    return registry
