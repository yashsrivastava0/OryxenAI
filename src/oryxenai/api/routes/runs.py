"""Run endpoints — mock execution and run history."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.agents.shared.executor import AgentExecutor
from oryxenai.agents.shared.registry import AgentRegistry
from oryxenai.api.dependencies import (
    get_agent_registry,
    get_db_session,
    get_executor,
    get_run_repo,
    get_session_repo,
)
from oryxenai.api.errors import (
    PayloadTooLargeError,
    SessionNotFoundError,
    ValidationError,
)
from oryxenai.core.logging import get_request_id
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.repositories.agent_runs import AgentRunRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository
from oryxenai.runtime.mock_runner import MockRunner

router = APIRouter(tags=["runs"])

MAX_INPUT_BYTES = 256_000  # 256 KB reasonable limit for the testing harness


class MockRunRequest(BaseModel):
    agentKey: str
    input: dict[str, Any] = Field(default_factory=dict)
    idempotencyKey: str | None = None


class RunResponse(BaseModel):
    id: str
    portfolio_session_id: str
    agent_key: str
    status: str
    input_payload: dict[str, Any]
    output_payload: dict[str, Any] | None
    state_before: dict[str, Any]
    state_after: dict[str, Any] | None
    error_payload: dict[str, Any] | None
    attempt: int
    idempotency_key: str | None
    created_at: str
    finished_at: str | None


def _to_run_response(run: AgentRun) -> RunResponse:
    finished: datetime | None = run.finished_at
    return RunResponse(
        id=str(run.id),
        portfolio_session_id=str(run.portfolio_session_id),
        agent_key=run.agent_key,
        status=run.status,
        input_payload=dict(run.input_payload or {}),
        output_payload=run.output_payload,
        state_before=dict(run.state_before or {}),
        state_after=run.state_after,
        error_payload=run.error_payload,
        attempt=run.attempt,
        idempotency_key=run.idempotency_key,
        created_at=run.created_at.isoformat(),
        finished_at=finished.isoformat() if finished else None,
    )


@router.get("/sessions/{session_id}/runs", response_model=list[RunResponse])
async def list_runs(
    session_id: str,
    limit: int = 20,
    run_repo: AgentRunRepository = Depends(get_run_repo),
    session_repo: PortfolioSessionRepository = Depends(get_session_repo),
) -> list[RunResponse]:
    try:
        sid = UUID(session_id)
    except ValueError as exc:
        raise ValidationError(f"Invalid session ID format: '{session_id}'") from exc
    session = await session_repo.get_by_id(sid)
    if session is None:
        raise SessionNotFoundError(session_id)
    runs = await run_repo.list_for_session(sid, limit=limit)
    return [_to_run_response(r) for r in runs]


@router.post("/sessions/{session_id}/runs/mock", response_model=RunResponse)
async def create_mock_run(
    session_id: str,
    body: MockRunRequest,
    db: AsyncSession = Depends(get_db_session),
    session_repo: PortfolioSessionRepository = Depends(get_session_repo),
    run_repo: AgentRunRepository = Depends(get_run_repo),
    executor: AgentExecutor = Depends(get_executor),
    runner_registry: AgentRegistry = Depends(get_agent_registry),
) -> RunResponse:
    try:
        sid = UUID(session_id)
    except ValueError as exc:
        raise ValidationError(f"Invalid session ID: '{session_id}'") from exc

    # Size guard.
    import json

    raw = json.dumps(body.input).encode("utf-8")
    if len(raw) > MAX_INPUT_BYTES:
        raise PayloadTooLargeError(f"Input payload exceeds {MAX_INPUT_BYTES} bytes.")

    session = await session_repo.get_by_id(sid)
    if session is None:
        raise SessionNotFoundError(session_id)

    runner = MockRunner(runner_registry, executor)
    request_id = get_request_id() or ""
    run = await runner.run_mock(
        db_session=db,
        session_id=sid,
        agent_key=body.agentKey,
        agent_input=body.input,
        idempotency_key=body.idempotencyKey,
        request_id=request_id,
    )
    return _to_run_response(run)
