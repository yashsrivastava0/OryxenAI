"""Durable Build Preparation handler."""

from __future__ import annotations

from typing import Any

from oryxenai.build_preparation.service import BuildPreparationService
from oryxenai.core.settings import get_settings
from oryxenai.db.session import get_sessionmaker


class BuildPreparationHandler:
    kind = "build_preparation.prepare"

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        settings = get_settings()
        sessionmaker = get_sessionmaker(settings)
        async with sessionmaker() as db:
            service = BuildPreparationService(db, settings=settings)
            return await service.prepare_job(payload, instance_id)
