"""Agent executor — orchestrates the full run lifecycle.

Responsibilities (inside a single database transaction):
  1. Validate the selected agent.
  2. Check idempotency — return an existing run if the key was seen.
  3. Create an agent_runs row.
  4. Capture state_before.
  5. Mark the run as running.
  6. Invoke the agent via its protocol.
  7. Validate its result.
  8. Merge the agent output into the session's current_state.
  9. Update portfolio_sessions.current_state and increment revision.
 10. Mark the run succeeded — or persist a safe structured error on failure.

Does NOT chain agents, run a supervisor, or auto-call the next agent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentError, AgentResult, AgentRunStatus
from oryxenai.agents.shared.registry import AgentNotFoundError, AgentRegistry
from oryxenai.api.errors import AppError, ConflictError, NotFoundError
from oryxenai.core.logging import get_logger, set_agent_run_id
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.repositories.agent_runs import AgentRunRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger("oryxenai.agents.executor")


# --- Error code to AppError mapper ------------------------------------------


def _to_app_error(error: AgentError) -> AppError:
    """Map an AgentError to the corresponding HTTP-aware AppError subclass."""
    code = error.code
    details = error.details or {}
    if code == "SESSION_NOT_FOUND":
        return NotFoundError(error.message, code=code, details=details)
    if code == "REVISION_CONFLICT":
        return ConflictError(error.message, code=code, details=details)
    return AppError(error.message, code=code, status_code=400, details=details)


def _merge_state(
    current: dict[str, Any],
    agent_key: str,
    run_id: str,
    output: dict[str, Any],
) -> dict[str, Any]:
    """Merge an agent result under agents.<key> without mutating the input."""
    new_state = dict(current)
    agents_bucket = dict(new_state.get("agents", {}))
    agent_bucket = dict(agents_bucket.get(agent_key, {}))
    agent_bucket["latestRunId"] = run_id
    agent_bucket["output"] = output
    agents_bucket[agent_key] = agent_bucket
    new_state["agents"] = agents_bucket
    return new_state


class _RevisionConflict(Exception):
    """Internal sentinel for optimistic-revision contention during execution."""


class AgentExecutor:
    """Single-agent executor with transactional state persistence."""

    def __init__(
        self,
        registry: AgentRegistry,
        session_repo: PortfolioSessionRepository,
        run_repo: AgentRunRepository,
    ) -> None:
        self._registry = registry
        self._session_repo = session_repo
        self._run_repo = run_repo

    @property
    def registry(self) -> AgentRegistry:
        return self._registry

    async def execute(
        self,
        db_session: AsyncSession,
        session_id: UUID,
        agent_key: str,
        agent_input: dict[str, Any],
        request_id: str = "",
    ) -> AgentRun:
        """Execute one mock agent run and persist the result.

        Returns the persisted AgentRun (succeeded or failed).
        """
        from oryxenai.agents.shared.contracts import AgentKey as AK

        # 1 — Validate the selected agent.
        try:
            key_enum = AK.from_string(agent_key)
        except ValueError as exc:
            raise _to_app_error(
                AgentError(
                    code="AGENT_NOT_FOUND",
                    message=str(exc).split(". Valid")[0] + ".",
                    details={"key": agent_key},
                )
            ) from exc

        # Find the implementation (raises AgentNotFoundError -> controlled error).
        try:
            agent = self._registry.get(key_enum)
        except AgentNotFoundError as exc:
            raise _to_app_error(exc.error) from exc

        # Validate the session exists.
        portfolio_session = await self._session_repo.get_by_id(session_id)
        if portfolio_session is None:
            raise _to_app_error(
                AgentError(
                    code="SESSION_NOT_FOUND",
                    message="Portfolio session was not found.",
                    details={"session_id": str(session_id)},
                )
            )

        run_id = uuid4()
        set_agent_run_id(str(run_id))

        # 2 — Create the run row with state_before.
        state_before = dict(portfolio_session.current_state)
        run = AgentRun(
            id=run_id,
            portfolio_session_id=session_id,
            agent_key=key_enum.value,
            status=AgentRunStatus.PENDING.value,
            input_payload=agent_input,
            state_before=state_before,
            model_metadata={"provider": "mock", "model": "deterministic-mock"},
            attempt=1,
        )
        run = await self._run_repo.create(run)

        # 4 — Mark running.
        await self._run_repo.mark_started(run_id)

        # 5 — Invoke the agent.
        context = build_context(
            portfolio_session_id=session_id,
            agent_key=key_enum,
            current_state=state_before,
            agent_input=agent_input,
            request_id=request_id,
            attempt=1,
            run_id=run_id,
        )
        try:
            result: AgentResult = await agent.run(context)
            # 6 — Validate the result.
            if not isinstance(result, AgentResult):
                raise TypeError("agent.run did not return an AgentResult")

            # 8 — Merge state.
            state_after = _merge_state(state_before, key_enum.value, str(run_id), result.output)

            # 9 — Optimistic state update.
            updated = await self._session_repo.update_state(
                session_id, state_after, portfolio_session.revision
            )
            if updated is None:
                raise _RevisionConflict()

            # 10 — Mark succeeded.
            await self._run_repo.mark_succeeded(run_id, result.output, state_after)
            return await self._run_repo.get_by_id(run_id)  # type: ignore[return-value]

        except Exception as exc:
            # Persist a safe structured error on failure inside the same tx.
            if isinstance(exc, _RevisionConflict):
                error = AgentError(
                    code="REVISION_CONFLICT",
                    message="The session was updated by another request. Please retry.",
                )
            else:
                error = AgentError(
                    code="AGENT_EXECUTION_ERROR",
                    message=f"{type(exc).__name__} during agent execution.",
                    details={"agent": key_enum.value},
                )
            await self._run_repo.mark_failed(run_id, error.to_payload())
            logger.warning(
                "agent run %s (%s) failed: %s",
                run_id,
                key_enum.value,
                error.code,
            )
            return await self._run_repo.get_by_id(run_id)  # type: ignore[return-value]

    async def find_idempotent(
        self,
        session_id: UUID,
        agent_key: str,
        idempotency_key: str,
    ) -> AgentRun | None:
        """Return an existing run for the same idempotency key, if any."""
        return await self._run_repo.find_by_idempotency(session_id, agent_key, idempotency_key)
