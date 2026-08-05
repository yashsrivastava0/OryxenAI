"""Integration tests for the PortfolioSession repository — require PostgreSQL."""

from __future__ import annotations

import pytest

from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository

pytestmark = pytest.mark.integration


async def test_create_and_get_session(db_session):
    """A created session can be retrieved by ID."""
    repo = PortfolioSessionRepository(db_session)
    session = await repo.create(name="Test via repo")
    assert session.id is not None
    assert session.name == "Test via repo"
    assert session.revision == 0
    assert session.current_state == {}

    fetched = await repo.get_by_id(session.id)
    assert fetched is not None
    assert fetched.name == "Test via repo"


async def test_list_recent_sessions(db_session):
    """list_recent returns sessions in most-recent-first order."""
    repo = PortfolioSessionRepository(db_session)
    s1 = await repo.create(name="First")
    s2 = await repo.create(name="Second")
    s3 = await repo.create(name="Third")
    sessions = await repo.list_recent(limit=10)
    assert len(sessions) >= 3
    ids = [s.id for s in sessions]
    assert s1.id in ids
    assert s2.id in ids
    assert s3.id in ids


async def test_list_recent_limit(db_session):
    """list_recent respects the limit parameter."""
    repo = PortfolioSessionRepository(db_session)
    for i in range(5):
        await repo.create(name=f"Session {i}")
    sessions = await repo.list_recent(limit=2)
    assert len(sessions) == 2


async def test_update_state_optimistic(db_session):
    """update_state increments revision and updates state."""
    repo = PortfolioSessionRepository(db_session)
    session = await repo.create(name="State test")
    new_state = {"agents": {"discovery": {"latestRunId": "abc", "output": {"summary": "s"}}}}
    updated = await repo.update_state(session.id, new_state, session.revision)
    assert updated is not None
    assert updated.revision == 1
    assert updated.current_state["agents"]["discovery"]["latestRunId"] == "abc"


async def test_update_state_concurrent(db_session):
    """Optimistic update fails on revision mismatch (returns None)."""
    repo = PortfolioSessionRepository(db_session)
    session = await repo.create(name="Conflict test")
    result = await repo.update_state(session.id, {"x": 1}, expected_revision=session.revision + 1)
    assert result is None


async def test_jsonb_persistence(db_session):
    """JSONB state persists and round-trips correctly."""
    repo = PortfolioSessionRepository(db_session)
    session = await repo.create(name="JSONB test")
    state = {"nested": {"deep": {"value": 42}}, "list": [1, 2, 3]}
    await repo.update_state(session.id, state, session.revision)
    fetched = await repo.get_by_id(session.id)
    assert fetched is not None
    assert fetched.current_state["nested"]["deep"]["value"] == 42
    assert fetched.current_state["list"] == [1, 2, 3]
