"""Pytest configuration and fixtures.

Integration/worker tests use OryxenAI_CONFIG_OVERLAY=config/app.test.toml
to point to a dedicated test database (oryxenai_test) so the application
database is never touched.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

import pytest
import pytest_asyncio

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

# ── Test-only deterministic model client ────────────────────────────────────
#
# Not a demo feature: a plain test double (the equivalent of
# unittest.mock.Mock) so flow tests never make network calls.


_DEFAULT_QUESTIONS: dict[str, Any] = {
    "mode": "ASK_QUESTIONS",
    "assistant_message": "I have enough to ask a few focused questions.",
    "questions": [
        {
            "id": "target_direction",
            "text": "Should the portfolio lead with backend or full-stack?",
            "kind": "single_select",
            "options": [
                {"id": "backend", "label": "Backend"},
                {"id": "fullstack", "label": "Full-stack"},
                {"id": "balanced", "label": "Balanced"},
            ],
            "reason": "changes positioning and project order",
            "allow_skip": True,
            "allow_auto": False,
        }
    ],
    "memory_update": {"intent_summary": "Backend engineering roles", "open_items": []},
}

_DEFAULT_BRIEF: dict[str, Any] = {
    "mode": "BRIEF_READY",
    "assistant_message": "I prepared the Discovery brief. Review it and change anything before approving.",
    "brief_title": "Portfolio Discovery Brief — Mock User",
    "brief_markdown": (
        "# Portfolio Discovery Brief — Mock User\n\n"
        "## Portfolio direction at a glance\n\n"
        "Primary goal: secure backend engineering opportunities.\n\n"
        "## Approval summary\n\n"
        "Ready for approval."
    ),
    "open_items": ["no metrics supplied"],
    "memory_update": {},
}

_DEFAULT_BRIEF_REVISED: dict[str, Any] = {
    **_DEFAULT_BRIEF,
    "brief_title": "Portfolio Discovery Brief — Mock User (revised)",
    "brief_markdown": (
        "# Portfolio Discovery Brief — Mock User (revised)\n\n"
        "## Portfolio direction at a glance\n\n"
        "Primary goal: secure backend engineering opportunities. QueueGuard leads the story.\n\n"
        "## Approval summary\n\n"
        "Ready for approval."
    ),
}


class _MockModelClient:
    """Test-only deterministic ModelClient used by flow tests. Not a demo feature."""

    def __init__(
        self,
        questions_payload: dict[str, Any] | None = None,
        brief_payload: dict[str, Any] | None = None,
        brief_revised_payload: dict[str, Any] | None = None,
    ) -> None:
        self.questions_payload = questions_payload or _DEFAULT_QUESTIONS
        self.brief_payload = brief_payload or _DEFAULT_BRIEF
        self.brief_revised_payload = brief_revised_payload or _DEFAULT_BRIEF_REVISED
        self.requests: list[dict[str, Any]] = []

    async def complete(self, *, system: str, task: str, **_kwargs: Any) -> str:
        self.requests.append({"system": system, "task": task})
        return "mock complete"

    async def generate_structured(
        self,
        *,
        operation: str,
        instructions: str,
        input_payload: dict[str, Any],
        output_model: Any,
        **_kwargs: Any,
    ) -> Any:
        self.requests.append(
            {"operation": operation, "instructions": instructions, "input_payload": input_payload}
        )
        from oryxenai.agents.discovery.schemas import StructuredModelResult

        if operation in ("understand_and_question", "prepare_questions"):
            parsed = self.questions_payload
        else:
            revision_request = str((input_payload or {}).get("revision_request", "") or "")
            parsed = self.brief_revised_payload if revision_request else self.brief_payload
        parsed_output = output_model.model_validate(parsed).model_dump(mode="json")
        return StructuredModelResult(
            parsed_output=parsed_output,
            response_id="mock-response-id",
            model="mock-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            finish_reason="stop",
            latency_ms=1.0,
        )

    def reset_requests(self) -> None:
        self.requests = []


@pytest.fixture
def mock_model_client() -> _MockModelClient:
    """Deterministic test model client for Discovery flow tests."""
    return _MockModelClient()


# ── Ensure the test overlay is loaded for integration / worker tests. ──────

AUTO_CONFTEST_FLAG = "_ORYXENAI_CONFTEST_RAN"


@pytest.fixture(autouse=True)
def _set_test_overlay(monkeypatch, request):
    """Automatically set the test configuration overlay for integration
    and worker tests so they use the dedicated test database."""
    marks = [m.name for m in request.node.iter_markers()]
    if "integration" in marks or "worker" in marks:
        monkeypatch.setenv("OryxenAI_CONFIG_OVERLAY", "config/app.test.toml")
        # Clear cached settings so the overlay takes effect.
        from oryxenai.core.settings import reset_settings

        reset_settings()
        # Ensure only one conftest run sets the overlay (fixtures are re-run
        # per test, but the env var + reset is idempotent).


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


# ── DB fixtures (integration + worker) ─────────────────────────────────────


@pytest_asyncio.fixture
async def test_engine() -> AsyncIterator[AsyncEngine]:
    """Per-test async engine for integration/worker tests.

    Uses the test overlay (config/app.test.toml -> oryxenai_test).
    Creates/drops all tables per test. Skipped when PostgreSQL is unreachable.
    """
    from sqlalchemy import text

    from oryxenai.core.settings import get_settings
    from oryxenai.db.base import Base
    from oryxenai.db.session import get_engine, reset_engine_cache

    reset_engine_cache()

    settings = get_settings()
    try:
        engine = get_engine(settings)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("PostgreSQL unavailable")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
    reset_engine_cache()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Per-test DB session with automatic cleanup."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session
        await session.rollback()
        await session.execute(text("DELETE FROM background_jobs"))
        await session.execute(text("DELETE FROM service_heartbeats"))
        await session.execute(text("DELETE FROM agent_runs"))
        await session.execute(text("DELETE FROM portfolio_sessions"))
        await session.commit()
