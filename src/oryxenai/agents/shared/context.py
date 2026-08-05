"""Agent context helpers."""

from __future__ import annotations

from uuid import UUID, uuid4

from oryxenai.agents.shared.contracts import AgentContext, AgentKey


def build_context(
    portfolio_session_id: UUID,
    agent_key: AgentKey,
    current_state: dict[str, object],
    agent_input: dict[str, object],
    request_id: str = "",
    attempt: int = 1,
    run_id: UUID | None = None,
) -> AgentContext:
    """Create an AgentContext from structured data only."""
    return AgentContext(
        portfolio_session_id=str(portfolio_session_id),
        run_id=str(run_id or uuid4()),
        agent_key=agent_key,
        current_state=dict(current_state),
        agent_input=dict(agent_input),
        request_id=request_id,
        attempt=attempt,
    )
