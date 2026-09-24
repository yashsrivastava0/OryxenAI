"""Shared agent contracts.

A lean set of Protocols and Pydantic models — not a framework. Agents are
ordinary async Python objects that receive an AgentContext (structured data
only; never a DB session, FastAPI request, or settings object) and return an
AgentResult. The executor handles persistence and state transitions.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class AgentKey(StrEnum):
    """Logical agent identifiers. Adding a new agent means adding a member."""

    DISCOVERY = "discovery"
    CONTENT_ARCHITECT = "content_architect"

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
        strict_schema: bool = False,
        result_validator: Callable[[dict[str, Any]], None] | None = None,
    ) -> Any: ...


@dataclass(frozen=True)
class NormalizedUsage:
    """Provider-neutral usage facts.  Unknown values remain ``None``."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    cache_write_tokens: int | None = None
    reasoning_tokens: int | None = None
    total_tokens: int | None = None
    actual_cost: float | None = None
    estimated_cost: float | None = None
    cost_unit: str = ""
    provider_request_id: str = ""
    gateway_attempt_count: int | None = None


@dataclass(frozen=True)
class ModelCallContext:
    """Attribution context carried through one logical model operation."""

    session_id: str = ""
    run_id: str = ""
    job_id: str = ""
    owner_id_hash: str = ""
    agent: str = ""
    stage: str = ""
    operation: str = ""
    request_id: str = ""
    routing_policy_version: str = ""
    input_classification: str = "unknown"
    job_attempt: int = 0
    request_attempt: int = 0
    fallback_attempt: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResolvedModelRoute:
    """Immutable route selected before a provider request is admitted."""

    profile_name: str
    provider: str
    model: str
    credential_alias: str
    capacity_source_id: str
    quota_group: str
    profile_fingerprint: str = ""
    policy_version: str = ""
    input_policy: str = "any"
    pricing_card_ref: str = ""
    alternatives: tuple[str, ...] = ()


@dataclass
class OperationBudget:
    """One shared normal/recovery budget for a stage invocation."""

    normal_calls: int = 1
    recovery_allowance: int = 1
    deadline_monotonic: float | None = None
    normal_used: int = 0
    recovery_used: int = 0
    transmissions: int = 0
    max_transmissions: int | None = None
    reservations: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def recovery_remaining(self) -> int:
        return max(0, self.recovery_allowance - self.recovery_used)

    @property
    def normal_remaining(self) -> int:
        return max(0, self.normal_calls - self.normal_used)

    def admit_normal(self) -> None:
        if self.normal_remaining <= 0:
            raise RuntimeError("The logical model-call allowance is exhausted.")
        self.normal_used += 1

    def admit_recovery(self) -> None:
        if self.recovery_remaining <= 0:
            raise RuntimeError("The shared model recovery allowance is exhausted.")
        self.recovery_used += 1

    def record_transmission(self) -> None:
        if self.max_transmissions is not None and self.transmissions >= self.max_transmissions:
            raise RuntimeError("The application model-transmission ceiling is exhausted.")
        self.transmissions += 1
