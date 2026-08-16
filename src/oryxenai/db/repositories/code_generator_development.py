"""Repository for standalone Code Generator Phase 1 development runs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.db.models.code_generator_development import (
    CodeGeneratorDevelopmentEvent,
    CodeGeneratorDevelopmentRun,
)


class CodeGeneratorDevelopmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, input_reference: dict[str, object], idempotency_key: str | None
    ) -> CodeGeneratorDevelopmentRun:
        run = CodeGeneratorDevelopmentRun(
            input_reference=input_reference,
            idempotency_key=idempotency_key or None,
        )
        self._session.add(run)
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def find_idempotent(self, key: str) -> CodeGeneratorDevelopmentRun | None:
        result = await self._session.execute(
            select(CodeGeneratorDevelopmentRun).where(
                CodeGeneratorDevelopmentRun.idempotency_key == key
            )
        )
        return result.scalar_one_or_none()

    async def get(self, run_id: UUID) -> CodeGeneratorDevelopmentRun | None:
        result = await self._session.execute(
            select(CodeGeneratorDevelopmentRun).where(CodeGeneratorDevelopmentRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def compare_and_swap(
        self,
        run_id: UUID,
        *,
        expected_revision: int,
        values: dict[str, object],
    ) -> CodeGeneratorDevelopmentRun | None:
        stmt = (
            update(CodeGeneratorDevelopmentRun)
            .where(
                CodeGeneratorDevelopmentRun.id == run_id,
                CodeGeneratorDevelopmentRun.revision == expected_revision,
            )
            .values(**values, revision=expected_revision + 1, updated_at=datetime.now(UTC))
            .returning(CodeGeneratorDevelopmentRun)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            await self._session.refresh(row)
        return row

    async def append_event(
        self,
        run_id: UUID,
        *,
        event_type: str,
        level: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> CodeGeneratorDevelopmentEvent:
        sequence_result = await self._session.execute(
            select(func.coalesce(func.max(CodeGeneratorDevelopmentEvent.sequence), 0)).where(
                CodeGeneratorDevelopmentEvent.run_id == run_id
            )
        )
        event = CodeGeneratorDevelopmentEvent(
            run_id=run_id,
            sequence=int(sequence_result.scalar_one()) + 1,
            event_type=event_type,
            level=level,
            message=message,
            details=details or {},
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def events(
        self, run_id: UUID, *, after: int = 0, limit: int = 100
    ) -> list[CodeGeneratorDevelopmentEvent]:
        result = await self._session.execute(
            select(CodeGeneratorDevelopmentEvent)
            .where(
                CodeGeneratorDevelopmentEvent.run_id == run_id,
                CodeGeneratorDevelopmentEvent.sequence > max(0, after),
            )
            .order_by(CodeGeneratorDevelopmentEvent.sequence)
            .limit(max(1, limit))
        )
        return list(result.scalars().all())
