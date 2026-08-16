from __future__ import annotations

import pytest

from oryxenai.agents.code_generator.resource_adapters import default_adapters
from oryxenai.core.settings import get_settings
from oryxenai.db.repositories.code_generator_development import CodeGeneratorDevelopmentRepository
from oryxenai.jobs.handlers.code_generator import CodeGeneratorAcquisitionHandler
from tests.integration.test_code_generator_development_worker import _create_run, _plan


@pytest.mark.worker
async def test_code_generator_acquisition_redelivery_reuses_receipts(db_session, tmp_path) -> None:
    settings = get_settings()
    settings.code_generator_acquisition.materials_root = str(tmp_path / "materials")
    settings.code_generator_dependencies.workspaces_root = str(tmp_path / "workspaces")
    run = await _create_run(db_session, settings, _plan(resource_slot=False))
    handler = CodeGeneratorAcquisitionHandler(adapter_factory=lambda _settings: default_adapters())
    payload = {"development_run_id": str(run.id)}
    first = await handler.execute(payload, "worker-redelivery")
    second = await handler.execute(payload, "worker-redelivery")
    assert first["status"] == "succeeded"
    assert second == {"status": "succeeded", "run_id": str(run.id), "reused": True}
    stored = await CodeGeneratorDevelopmentRepository(db_session).get(run.id)
    assert stored is not None
    await db_session.refresh(stored)
    assert stored.resource_ledger is not None
