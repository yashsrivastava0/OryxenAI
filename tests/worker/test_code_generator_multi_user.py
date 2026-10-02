"""Several users building at once through the real Worker loop: isolation and lane limits."""

from __future__ import annotations

import asyncio
import copy
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from oryxenai.agents.code_generator.agent import CodeGeneratorAgent
from oryxenai.agents.code_generator.dev.mock_client import ReferenceModelClient
from oryxenai.core.settings import get_settings
from oryxenai.db.models.background_job import BackgroundJob
from oryxenai.jobs.worker import Worker
from tests.integration.test_code_generator_worker import _new_session, _service
from tests.unit.agents.code_generator.helpers import sample_content

pytestmark = [pytest.mark.integration, pytest.mark.worker]

NAMES = ["Asha Verma", "Bruno Keller", "Chen Wei", "Dara Okafor"]


class _CountingClient(ReferenceModelClient):
    """Records how many model calls overlap, and holds each one briefly."""

    active = 0
    peak = 0

    async def generate_structured(self, **kwargs: Any) -> Any:
        type(self).active += 1
        type(self).peak = max(type(self).peak, type(self).active)
        try:
            return await super().generate_structured(**kwargs)
        finally:
            type(self).active -= 1


@pytest.mark.asyncio
async def test_four_users_build_concurrently_without_crossing_wires(
    db_session, monkeypatch
) -> None:
    _CountingClient.active = _CountingClient.peak = 0
    monkeypatch.setattr(
        "oryxenai.jobs.handlers.code_generator._build_code_generator_agent",
        lambda **kwargs: CodeGeneratorAgent(
            _CountingClient(delay=0.4), theme_id=kwargs["theme_id"]
        ),
    )
    sessions: dict[UUID, str] = {}
    for name in NAMES:
        content = copy.deepcopy(sample_content("01_strong_profile"))
        content["hero"]["name"] = name
        content["metadata"]["title"] = f"{name} - Portfolio"
        session_id = await _new_session(db_session, content=content)
        sessions[session_id] = name
    for session_id in sessions:
        await _service(db_session).start(session_id)
    await db_session.commit()

    # The worker owns (and disposes) its own engine, so it cannot pull the pool out
    # from under the shared fixture engine that the rest of the suite uses.
    worker_engine = create_async_engine(get_settings().database_url, pool_size=3)
    monkeypatch.setattr("oryxenai.jobs.worker.get_engine", lambda _settings: worker_engine)
    worker = Worker()
    task = asyncio.create_task(worker.run())
    try:
        deadline = asyncio.get_running_loop().time() + 60
        while asyncio.get_running_loop().time() < deadline:
            db_session.expire_all()
            states = [await _service(db_session).get_state(sid) for sid in sessions]
            if all(state["code_generator"]["status"] == "ready" for state in states):
                break
            await asyncio.sleep(0.5)
        else:
            pytest.fail(f"builds did not finish: {[s['code_generator']['status'] for s in states]}")
    finally:
        worker._running = False
        await asyncio.wait_for(task, timeout=30)

    lane_limit = get_settings().worker.model_lane_concurrency
    assert 1 <= _CountingClient.peak <= lane_limit  # the shared model lane is respected
    for session_id, name in sessions.items():
        service = _service(db_session)
        state = await service.get_state(session_id)
        [version] = state["versions"]
        assert (version["status"], version["version_number"]) == ("ready", 1)
        html = (await service.get_version(session_id, UUID(version["id"]), include_html=True))[
            "index_html"
        ]
        assert name in html
        assert not any(other in html for other in NAMES if other != name)
        assert state["chat"][-1]["body"] == "Your portfolio is ready (version 1)."
    jobs = (await db_session.execute(select(BackgroundJob))).scalars().all()
    assert len(jobs) == len(NAMES)
    assert {(job.status, job.max_attempts, job.attempt) for job in jobs} == {("succeeded", 1, 1)}
