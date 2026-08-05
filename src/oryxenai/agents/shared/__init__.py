"""Shared agent boundaries: contracts, context, model client, registry, executor, providers."""

from oryxenai.agents.shared.contracts import (
    Agent,
    AgentContext,
    AgentError,
    AgentKey,
    AgentRequest,
    AgentResult,
    AgentRunStatus,
    ModelClient,
)
from oryxenai.agents.shared.model_client import (
    MockModelClient,
    build_model_client,
    build_provider_client,
    resolve_api_key,
)

__all__ = [
    "Agent",
    "AgentContext",
    "AgentError",
    "AgentKey",
    "AgentRequest",
    "AgentResult",
    "AgentRunStatus",
    "MockModelClient",
    "ModelClient",
    "build_model_client",
    "build_provider_client",
    "resolve_api_key",
]
