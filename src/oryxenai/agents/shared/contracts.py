"""Shared agent contracts.

A lean set of Protocols and Pydantic models — not a framework. Agents are
ordinary async Python objects that receive an AgentContext (structured data
only; never a DB session, FastAPI request, or settings object) and return an
AgentResult. The executor handles persistence and state transitions.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class AgentKey(StrEnum):
    """Logical agent identifiers. Adding a new agent means adding a member."""

    DISCOVERY = "discovery"
    CONTENT_ARCHITECT = "content_architect"
    VISUAL_DESIGN_DIRECTOR = "visual_design_director"
    BUILD_PREPARATION = "build_preparation"
    CODE_GENERATOR = "code_generator"

    @classmethod
    def from_string(cls, value: str) -> AgentKey:
        """Parse a key; raises ValueError for unknown agents."""
        try:
            return cls(value)
        except ValueError as exc:
            valid = ", ".join(m.value for m in cls)
            raise ValueError(f"Unknown agent key '{value}'. Valid keys: {valid}") from exc


class AgentRunStatus(StrEnum):
    """Lifecycle status of a single agent run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AgentError(BaseModel):
    """A safe, structured error recorded on a failed run.

    Never carries raw stack traces or secrets.
    """

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


class AgentContext(BaseModel):
    """Structured data passed to an agent's run() method.

    Contains only data — no database sessions, HTTP requests, or settings.
    """

    portfolio_session_id: str
    run_id: str
    agent_key: AgentKey
    current_state: dict[str, Any] = Field(default_factory=dict)
    agent_input: dict[str, Any] = Field(default_factory=dict)
    request_id: str = ""
    attempt: int = 1


class AgentRequest(BaseModel):
    """Validated request envelope for an agent run (subclass per agent)."""

    input: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class AgentResult(BaseModel):
    """Validated result of an agent run (subclass per agent).

    The `output` dict is what gets persisted to agent_runs.output_payload
    and merged into the session's current_state under agents.<key>.
    """

    output: dict[str, Any] = Field(default_factory=dict)
    prompt_version: str = "0.0.0-mock"
    model_metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class Agent(Protocol):
    """Protocol every agent implementation must satisfy.

    Implementations may call a provider through ModelClient; persistence and
    orchestration remain outside the agent.
    """

    key: AgentKey

    async def run(self, context: AgentContext) -> AgentResult: ...


@runtime_checkable
class ModelClient(Protocol):
    """Provider-neutral model client protocol.

    Implementations can use any configured provider endpoint. Agent code
    depends on this protocol, never on a concrete provider.
    """

    async def complete(
        self,
        system_prompt: str,
        task_prompt: str,
        request_params: dict[str, Any] | None = None,
    ) -> str: ...

    async def generate_structured(
        self,
        *,
        operation: str,
        instructions: str,
        input_payload: Mapping[str, object],
        output_model: type[BaseModel],
        system_prompt: str | None = None,
        model_profile: Any = None,
        request_context: Any = None,
    ) -> Any: ...
