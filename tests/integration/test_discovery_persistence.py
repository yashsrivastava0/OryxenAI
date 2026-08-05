"""PostgreSQL integration coverage for Discovery source and aggregate state."""

from __future__ import annotations

import pytest

from oryxenai.agents.discovery.schemas import DiscoveryIntake, ResumeSource
from oryxenai.agents.discovery.service import DiscoveryOperationError, DiscoveryService
from oryxenai.db.repositories.discovery import DiscoveryRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository
from oryxenai.jobs.service import JobService

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_discovery_input_creates_immutable_source_revision(db_session) -> None:
    session = await PortfolioSessionRepository(db_session).create("Discovery integration")
    service = DiscoveryService(DiscoveryRepository(db_session), JobService(db_session))
    intake = DiscoveryIntake(
        main_prompt="Find backend engineering opportunities.",
        resume_text="Alex Rivera\nPython and FastAPI\nExample Corp",
        resume_source=ResumeSource.PASTED_TEXT,
        output_language="en",
    )

    first = await service.process_intake(session.id, intake, expected_revision=0)
    assert first["discovery"]["status"] == "input_ready"
    assert first["discovery"]["source_revision"] == 1
    sources = await DiscoveryRepository(db_session).get_sources_at_revision(session.id, 1)
    assert {source.source_kind for source in sources} == {"main_prompt", "resume_text", "links"}

    with pytest.raises(DiscoveryOperationError) as error:
        await service.process_intake(session.id, intake, expected_revision=0)
    assert error.value.code == "DISCOVERY_REVISION_CONFLICT"
