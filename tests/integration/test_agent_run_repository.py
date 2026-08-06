"""Integration tests for the AgentRun repository — require PostgreSQL."""

from __future__ import annotations

import pytest

from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.repositories.agent_runs import AgentRunRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository

pytestmark = pytest.mark.integration


async def _create_session_and_repo(db_session):
    session_repo = PortfolioSessionRepository(db_session)
    session = await session_repo.create(name="Run repo test")
    run_repo = AgentRunRepository(db_session)
    return session, run_repo


async def test_create_and_get_run(db_session):
    """A created run can be retrieved by ID."""
    session, run_repo = await _create_session_and_repo(db_session)
    run = AgentRun(
        portfolio_session_id=session.id,
        agent_key="discovery",
        status="pending",
        input_payload={"prompt": "test"},
        state_before={},
    )
    created = await run_repo.create(run)
    assert created.id is not None
    fetched = await run_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.agent_key == "discovery"
    assert fetched.status == "pending"


async def test_mark_succeeded(db_session):
    """mark_succeeded stores output and state_after."""
    session, run_repo = await _create_session_and_repo(db_session)
    run = AgentRun(
        portfolio_session_id=session.id,
        agent_key="discovery",
        status="running",
        input_payload={},
        state_before={},
    )
    created = await run_repo.create(run)
    await run_repo.mark_started(created.id)
    await run_repo.mark_succeeded(
        created.id,
        output_payload={"summary": "result"},
        state_after={"agents": {"discovery": {"output": {"summary": "result"}}}},
    )
    fetched = await run_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.status == "succeeded"
    assert fetched.output_payload == {"summary": "result"}
    assert fetched.state_after is not None
    assert fetched.started_at is not None
    assert fetched.finished_at is not None


async def test_mark_failed(db_session):
    """mark_failed stores a safe structured error."""
    session, run_repo = await _create_session_and_repo(db_session)
    run = AgentRun(
        portfolio_session_id=session.id,
        agent_key="discovery",
        status="running",
        input_payload={},
        state_before={},
    )
    created = await run_repo.create(run)
    await run_repo.mark_failed(
        created.id,
        error_payload={"code": "AGENT_EXECUTION_ERROR", "message": "boom"},
    )
    fetched = await run_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.status == "failed"
    assert fetched.error_payload == {"code": "AGENT_EXECUTION_ERROR", "message": "boom"}


async def test_list_for_session_ordering(db_session):
    """Runs are returned most-recent-first."""
    session, run_repo = await _create_session_and_repo(db_session)
    for i in range(3):
        run = AgentRun(
            portfolio_session_id=session.id,
            agent_key="discovery",
            status="succeeded",
            input_payload={"i": i},
            state_before={},
        )
        await run_repo.create(run)
    runs = await run_repo.list_for_session(session.id, limit=10)
    assert len(runs) == 3
    # Order: newest first.
    assert runs[0].created_at >= runs[1].created_at


async def test_idempotency_lookup(db_session):
    """find_by_idempotency returns an existing run with the same key."""
    session, run_repo = await _create_session_and_repo(db_session)
    run = AgentRun(
        portfolio_session_id=session.id,
        agent_key="discovery",
        status="succeeded",
        input_payload={},
        state_before={},
        idempotency_key="key-abc",
    )
    created = await run_repo.create(run)
    found = await run_repo.find_by_idempotency(session.id, "discovery", "key-abc")
    assert found is not None
    assert found.id == created.id
    assert found.idempotency_key == "key-abc"


async def test_idempotency_unique_constraint(db_session):
    """A duplicate idempotency key violates the unique index."""
    from sqlalchemy.exc import IntegrityError

    session, run_repo = await _create_session_and_repo(db_session)
    run1 = AgentRun(
        portfolio_session_id=session.id,
        agent_key="discovery",
        status="succeeded",
        input_payload={},
        state_before={},
        idempotency_key="dup-key",
    )
    await run_repo.create(run1)
    run2 = AgentRun(
        portfolio_session_id=session.id,
        agent_key="discovery",
        status="pending",
        input_payload={},
        state_before={},
        idempotency_key="dup-key",
    )
    with pytest.raises(IntegrityError):
        await run_repo.create(run2)


async def test_jsonb_round_trip(db_session):
    """JSONB input/output/state payloads persist and round-trip."""
    session, run_repo = await _create_session_and_repo(db_session)
    payload = {"key": "value", "nested": {"deep": [1, 2, {"x": True}]}}
    run = AgentRun(
        portfolio_session_id=session.id,
        agent_key="discovery",
        status="succeeded",
        input_payload=payload,
        state_before={"before": True},
    )
    created = await run_repo.create(run)
    await run_repo.mark_succeeded(created.id, payload, {"after": True})
    fetched = await run_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.input_payload == payload
    assert fetched.output_payload == payload


async def test_provider_metadata_persisted_on_success(db_session):
    """finish_reason/latency_ms/usage/prompt_version are persisted (Section 8)."""
    session, run_repo = await _create_session_and_repo(db_session)
    run = AgentRun(
        portfolio_session_id=session.id,
        agent_key="discovery",
        status="running",
        input_payload={},
        state_before={},
    )
    created = await run_repo.create(run)
    await run_repo.mark_started(created.id)
    metadata = {
        "provider": "opencode_go",
        "model": "deepseek-v4-pro",
        "response_id": "resp-abc",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        "latency_ms": 1234.5,
        "finish_reason": "stop",
        "repair_attempted": False,
    }
    await run_repo.mark_succeeded(
        created.id,
        {"operation": "prepare_questions"},
        {"after": True},
        prompt_version="discovery.call_a.v2",
        model_metadata=metadata,
    )
    fetched = await run_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.prompt_version == "discovery.call_a.v2"
    assert fetched.finish_reason == "stop"
    assert fetched.latency_ms == 1234.5
    assert fetched.usage == {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    assert fetched.model_metadata["response_id"] == "resp-abc"


async def test_provider_metadata_persisted_on_failure(db_session):
    """Failed runs also retain provider metadata for observability."""
    session, run_repo = await _create_session_and_repo(db_session)
    run = AgentRun(
        portfolio_session_id=session.id,
        agent_key="discovery",
        status="running",
        input_payload={},
        state_before={},
    )
    created = await run_repo.create(run)
    await run_repo.mark_started(created.id)
    metadata = {
        "finish_reason": "length",
        "latency_ms": 900.25,
        "usage": {"total_tokens": 5000},
    }
    await run_repo.mark_failed(
        created.id,
        {"code": "MODEL_OUTPUT_TRUNCATED", "message": "truncated"},
        model_metadata=metadata,
    )
    fetched = await run_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.status == "failed"
    assert fetched.finish_reason == "length"
    assert fetched.latency_ms == 900.25
    assert fetched.usage == {"total_tokens": 5000}
