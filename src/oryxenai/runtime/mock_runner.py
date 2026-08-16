"""Mock runner — wires the executor with repositories for the API layer.

A thin facade the API dependencies call. The real orchestration lives in the
executor; this provides a stable entry point so the API does not import
executor internals directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from oryxenai.agents.shared.executor import AgentExecutor
from oryxenai.core.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from oryxenai.agents.shared.registry import AgentRegistry
    from oryxenai.db.models.agent_run import AgentRun

logger = get_logger("oryxenai.runtime.mock_runner")


def _mock_input_for_agent(agent_key: str, agent_input: dict[str, Any]) -> dict[str, Any]:
    """Provide the minimal upstream-shaped context needed by mock agents."""
    if agent_key != "visual_design_director" or "intake" in agent_input:
        return agent_input
    return {
        **agent_input,
        "intake": {
            "route_plan": [
                {
                    "route_id": "home",
                    "path": "/",
                    "purpose": "Single-page portfolio home",
                    "publication_status": "approved",
                }
            ],
            "page_content_packs": [{"route_id": "home", "sections": [{"section_id": "hero"}]}],
        },
    }


class MockRunner:
    """Facade that runs a deterministic mock agent and persists the result."""

    def __init__(
        self,
        registry: AgentRegistry,
        executor: AgentExecutor,
    ) -> None:
        self._registry = registry
        self._executor = executor

    async def run_mock(
        self,
        db_session: AsyncSession,
        session_id: UUID,
        agent_key: str,
        agent_input: dict[str, Any],
        idempotency_key: str | None,
        request_id: str = "",
    ) -> AgentRun:

        # Idempotency: return existing run if the key was already used.
        if idempotency_key:
            existing = await self._executor.find_idempotent(session_id, agent_key, idempotency_key)
            if existing is not None:
                logger.info("idempotent reuse: run %s for %s", existing.id, agent_key)
                return existing

        run: AgentRun = await self._executor.execute(
            db_session=db_session,
            session_id=session_id,
            agent_key=agent_key,
            agent_input=_mock_input_for_agent(agent_key, agent_input),
            request_id=request_id,
        )

        # Attach the idempotency key to the run record (if provided).
        if idempotency_key and run.idempotency_key is None:
            run.idempotency_key = idempotency_key
            await db_session.flush()

        return run
