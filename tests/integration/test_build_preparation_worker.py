"""Durable Phase 3 Build Preparation flow over the real test database."""

from __future__ import annotations

from uuid import UUID

import pytest

from oryxenai.agents.build_preparation.service import (
    BuildPreparationOperationError,
    BuildPreparationService,
)
from oryxenai.agents.content_architect.schemas import (
    ContentArchitectApproval,
    ContentArchitectState,
    ContentArchitectStatus,
    ContentSection,
    PageContentPack,
    RoutePlanEntry,
)
from oryxenai.agents.visual_design_director.schemas import (
    PageVisualDirection,
    VisualDesignDirectorApproval,
    VisualDesignDirectorState,
    VisualDesignDirectorStatus,
)
from oryxenai.db.repositories.build_preparation import BuildPreparationRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository
from oryxenai.jobs.handlers.build_preparation import BuildPreparationHandler
from oryxenai.jobs.service import JobService

pytestmark = pytest.mark.integration


def _approved_upstream_state() -> dict[str, object]:
    content_architect = ContentArchitectState(
        status=ContentArchitectStatus.APPROVED,
        route_plan=[RoutePlanEntry(route_id="home", path="/", title="Home")],
        page_content_packs=[
            PageContentPack(
                route_id="home",
                sections=[
                    ContentSection(
                        section_id="hero",
                        purpose="Introduce the portfolio.",
                        content={"heading": "A grounded portfolio heading"},
                    )
                ],
            )
        ],
        approved=ContentArchitectApproval(
            approved_at="2026-08-11T00:00:00+00:00",
            content_hash="content-hash",
        ),
    )
    visual_design_director = VisualDesignDirectorState(
        status=VisualDesignDirectorStatus.APPROVED,
        pages=[PageVisualDirection(route_id="home", path="/")],
        approved=VisualDesignDirectorApproval(
            approved_at="2026-08-11T00:00:00+00:00",
            visual_direction_hash="visual-hash",
        ),
    )
    return {
        "content_architect": content_architect.model_dump(mode="json"),
        "visual_design_director": visual_design_director.model_dump(mode="json"),
    }


@pytest.mark.asyncio
async def test_start_requires_approved_content_architect(db_session) -> None:
    session = await PortfolioSessionRepository(db_session).create("Build Preparation gate")
    service = BuildPreparationService(
        BuildPreparationRepository(db_session), JobService(db_session)
    )

    with pytest.raises(BuildPreparationOperationError) as exc_info:
        await service.start(session.id)

    assert exc_info.value.code == "BUILD_PREPARATION_CONTENT_ARCHITECT_NOT_APPROVED"


@pytest.mark.asyncio
async def test_phase_3_start_and_worker_flow_persist_blocked_visual_state(db_session) -> None:
    session = await PortfolioSessionRepository(db_session).create("Build Preparation worker")
    session_id = session.id
    session.current_state = _approved_upstream_state()
    await db_session.flush()

    service = BuildPreparationService(
        BuildPreparationRepository(db_session), JobService(db_session)
    )
    started = await service.start(session_id)
    assert started["build_preparation"]["status"] == "running"
    await db_session.commit()

    job = await JobService(db_session).get(UUID(started["build_preparation"]["job_id"]))
    assert job is not None
    result = await BuildPreparationHandler().execute(job.payload, "test-worker")

    assert result["status"] == "succeeded"
    replay = await BuildPreparationHandler().execute(job.payload, "test-worker-replay")
    assert replay["status"] == "succeeded"
    await db_session.commit()
    db_session.expire_all()

    review = await service.get_state(session_id)
    build_preparation = review["build_preparation"]
    assert build_preparation["status"] == "needs_attention"
    assert build_preparation["handoff_report"]["handoff_eligible"] is False
    assert build_preparation["handoff_report"]["execution_gaps"]
    assert build_preparation["routes"][0]["route_id"] == "home"
    assert build_preparation["scope_hash"]
    assert build_preparation["current_stage"] == "phase_3"
    assert build_preparation["materialization"]["manifest_path"] == "resources/manifest.json"
    assert build_preparation["package"]["archive_sha256"]
