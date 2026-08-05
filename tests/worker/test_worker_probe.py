"""Integration tests for the worker probe handler flow."""

from __future__ import annotations

import pytest

from oryxenai.jobs.contracts import SYSTEM_PROBE_KIND, JobStatus
from oryxenai.jobs.registry import WorkerProbeHandler
from oryxenai.jobs.repository import JobRepository

pytestmark = [pytest.mark.integration, pytest.mark.worker]


async def test_probe_handler_executes():
    handler = WorkerProbeHandler()
    result = await handler.execute({"message": "test-message"}, "worker-1")
    assert "received_at" in result
    assert result["worker_instance"] == "worker-1"
    assert result["echo_message"] == "test-message"


async def test_enqueue_to_completion_flow(db_session):
    repo = JobRepository(db_session)
    job = await repo.enqueue(SYSTEM_PROBE_KIND, {"message": "flow-test"})
    assert job.status == JobStatus.QUEUED.value

    claimed = await repo.claim_batch("worker-test", 120.0, 1)
    assert len(claimed) == 1
    assert claimed[0].id == job.id
    assert claimed[0].status == JobStatus.RUNNING.value

    handler = WorkerProbeHandler()
    result = await handler.execute(claimed[0].payload or {}, "worker-test")
    assert result["echo_message"] == "flow-test"

    await repo.mark_succeeded(job.id, result)
    fetched = await repo.get_by_id(job.id)
    assert fetched is not None
    assert fetched.status == JobStatus.SUCCEEDED.value
    assert fetched.result == result
