from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from oryxenai.agents.code_generator.core import worker_readiness
from oryxenai.core.settings import Settings


class _HeartbeatRepository:
    def __init__(self, rows):
        self.rows = rows

    async def get_recent(self, *, limit: int):
        assert limit == 25
        return self.rows


@pytest.mark.asyncio
async def test_worker_readiness_requires_matching_capability_receipt(monkeypatch) -> None:
    settings = Settings()
    now = datetime.now(UTC)
    row = SimpleNamespace(
        instance_id="worker-1",
        last_seen_at=now,
        stopped_at=None,
        service_metadata={
            "release_id": settings.code_generator_development.worker_release_id,
            "pipeline_contract_version": settings.code_generator_development.pipeline_contract_version,
            "code_generator_capability": False,
            "code_generator_toolchain": {"node": True, "npm": True, "browser": False},
        },
    )
    monkeypatch.setattr(
        worker_readiness,
        "HeartbeatRepository",
        lambda _session: _HeartbeatRepository([row]),
    )

    result = await worker_readiness.worker_contract_readiness(
        SimpleNamespace(_session=object()), settings
    )

    assert result["ready"] is False
    assert result["blocker"] == "code_generator_worker_toolchain_unavailable"
    assert result["active_workers"][0]["code_generator_toolchain"]["browser"] is False


@pytest.mark.asyncio
async def test_worker_readiness_accepts_only_fresh_matching_worker(monkeypatch) -> None:
    settings = Settings()
    row = SimpleNamespace(
        instance_id="worker-1",
        last_seen_at=datetime.now(UTC),
        stopped_at=None,
        service_metadata={
            "release_id": settings.code_generator_development.worker_release_id,
            "pipeline_contract_version": settings.code_generator_development.pipeline_contract_version,
            "code_generator_capability": True,
            "code_generator_toolchain": {"node": True, "npm": True, "browser": True},
        },
    )
    monkeypatch.setattr(
        worker_readiness,
        "HeartbeatRepository",
        lambda _session: _HeartbeatRepository([row]),
    )

    result = await worker_readiness.worker_contract_readiness(
        SimpleNamespace(_session=object()), settings
    )

    assert result["ready"] is True
    assert result["blocker"] == ""
