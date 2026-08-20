"""Repository for session and development Code Generator runs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.db.models.code_generator_development import (
    CodeGeneratorDevelopmentEvent,
    CodeGeneratorDevelopmentRun,
    CodeGeneratorStageAttempt,
)


class CodeGeneratorDevelopmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        input_reference: dict[str, object],
        idempotency_key: str | None,
        auto_advance: bool = False,
        run_mode: str = "development",
        portfolio_session_id: UUID | None = None,
        idempotency_scope: str = "development",
        build_preparation_source_ref: dict[str, object] | None = None,
        artifact_reference: dict[str, object] | None = None,
        preflight_receipt: dict[str, object] | None = None,
        preview_host: str | None = None,
        pipeline_contract_version: str = "code-generator-v3",
        trace_id: str | None = None,
    ) -> CodeGeneratorDevelopmentRun:
        run = CodeGeneratorDevelopmentRun(
            input_reference=input_reference,
            idempotency_key=idempotency_key or None,
            idempotency_scope=idempotency_scope,
            run_mode=run_mode,
            portfolio_session_id=portfolio_session_id,
            build_preparation_source_ref=build_preparation_source_ref,
            artifact_reference=artifact_reference,
            preflight_receipt=preflight_receipt,
            preview_host=preview_host,
            # Direct repository callers are diagnostic/manual by default. The
            # HTTP service opts into the durable coordinator explicitly.
            auto_advance=auto_advance,
            pipeline_contract_version=pipeline_contract_version,
            trace_id=trace_id,
        )
        self._session.add(run)
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def find_idempotent(
        self, key: str, *, scope: str = "development"
    ) -> CodeGeneratorDevelopmentRun | None:
        result = await self._session.execute(
            select(CodeGeneratorDevelopmentRun).where(
                CodeGeneratorDevelopmentRun.idempotency_key == key,
                CodeGeneratorDevelopmentRun.idempotency_scope == scope,
            )
        )
        return result.scalar_one_or_none()

    async def get_for_session(
        self, run_id: UUID, session_id: UUID
    ) -> CodeGeneratorDevelopmentRun | None:
        result = await self._session.execute(
            select(CodeGeneratorDevelopmentRun).where(
                CodeGeneratorDevelopmentRun.id == run_id,
                CodeGeneratorDevelopmentRun.portfolio_session_id == session_id,
            )
        )
        return result.scalar_one_or_none()

    async def latest_for_session(self, session_id: UUID) -> CodeGeneratorDevelopmentRun | None:
        result = await self._session.execute(
            select(CodeGeneratorDevelopmentRun)
            .where(CodeGeneratorDevelopmentRun.portfolio_session_id == session_id)
            .order_by(CodeGeneratorDevelopmentRun.created_at.desc())
            .limit(1)
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
        attempt_id: UUID | None = None,
        pipeline_contract_version: str = "code-generator-v3",
        trace_id: str | None = None,
    ) -> CodeGeneratorDevelopmentEvent:
        sequence_result = await self._session.execute(
            select(func.coalesce(func.max(CodeGeneratorDevelopmentEvent.sequence), 0)).where(
                CodeGeneratorDevelopmentEvent.run_id == run_id
            )
        )
        event = CodeGeneratorDevelopmentEvent(
            run_id=run_id,
            attempt_id=attempt_id,
            pipeline_contract_version=pipeline_contract_version,
            trace_id=trace_id,
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

    async def create_stage_attempt(
        self,
        run_id: UUID,
        *,
        stage: str,
        input_fingerprint: str,
        idempotency_key: str,
        expected_run_revision: int,
        job_id: UUID | None = None,
        trace_id: str | None = None,
        worker_version: str | None = None,
        artifact_references: list[dict[str, object]] | None = None,
    ) -> CodeGeneratorStageAttempt:
        """Create one queued stage attempt with a deterministic caller token.

        The partial unique index is the final concurrency guard.  The
        preflight lookup makes normal duplicate delivery return the existing
        row without turning a harmless retry into a database error.
        """

        existing = await self.find_stage_attempt_idempotent(idempotency_key)
        if existing is not None:
            return existing
        latest = await self._session.execute(
            select(func.coalesce(func.max(CodeGeneratorStageAttempt.attempt_no), 0)).where(
                CodeGeneratorStageAttempt.run_id == run_id,
                CodeGeneratorStageAttempt.stage == stage,
            )
        )
        attempt = CodeGeneratorStageAttempt(
            run_id=run_id,
            stage=stage,
            attempt_no=int(latest.scalar_one()) + 1,
            status="queued",
            job_id=job_id,
            idempotency_key=idempotency_key,
            expected_run_revision=expected_run_revision,
            input_fingerprint=input_fingerprint,
            trace_id=trace_id,
            worker_version=worker_version,
            artifact_references=artifact_references or [],
        )
        self._session.add(attempt)
        await self._session.flush()
        await self._session.refresh(attempt)
        return attempt

    async def find_stage_attempt_idempotent(
        self, idempotency_key: str
    ) -> CodeGeneratorStageAttempt | None:
        result = await self._session.execute(
            select(CodeGeneratorStageAttempt).where(
                CodeGeneratorStageAttempt.idempotency_key == idempotency_key
            )
        )
        return result.scalar_one_or_none()

    async def get_stage_attempt(self, attempt_id: UUID) -> CodeGeneratorStageAttempt | None:
        result = await self._session.execute(
            select(CodeGeneratorStageAttempt).where(CodeGeneratorStageAttempt.id == attempt_id)
        )
        return result.scalar_one_or_none()

    async def active_stage_attempt(self, run_id: UUID) -> CodeGeneratorStageAttempt | None:
        result = await self._session.execute(
            select(CodeGeneratorStageAttempt)
            .where(
                CodeGeneratorStageAttempt.run_id == run_id,
                CodeGeneratorStageAttempt.status.in_(("queued", "running", "retrying")),
            )
            .order_by(CodeGeneratorStageAttempt.attempt_no.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def claim_stage_attempt(
        self,
        attempt_id: UUID,
        *,
        worker_instance: str,
        expected_run_revision: int,
    ) -> CodeGeneratorStageAttempt | None:
        stmt = (
            update(CodeGeneratorStageAttempt)
            .where(
                CodeGeneratorStageAttempt.id == attempt_id,
                CodeGeneratorStageAttempt.status.in_(("queued", "retrying")),
                CodeGeneratorStageAttempt.expected_run_revision == expected_run_revision,
            )
            .values(
                status="running",
                worker_instance=worker_instance,
                started_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            .returning(CodeGeneratorStageAttempt)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            await self._session.refresh(row)
        return row

    async def bind_stage_attempt_job(
        self, attempt_id: UUID, *, job_id: UUID
    ) -> CodeGeneratorStageAttempt | None:
        result = await self._session.execute(
            update(CodeGeneratorStageAttempt)
            .where(
                CodeGeneratorStageAttempt.id == attempt_id,
                CodeGeneratorStageAttempt.job_id.is_(None),
            )
            .values(job_id=job_id, updated_at=datetime.now(UTC))
            .returning(CodeGeneratorStageAttempt)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            await self._session.refresh(row)
        return row

    async def finalize_stage_attempt(
        self,
        attempt_id: UUID,
        *,
        run_id: UUID,
        stage: str,
        job_id: UUID | None,
        expected_run_revision: int,
        input_fingerprint: str,
        status: str,
        safe_error: dict[str, object] | None = None,
        artifact_references: list[dict[str, object]] | None = None,
    ) -> CodeGeneratorStageAttempt | None:
        """Finalize only the still-owned attempt; late handlers get no row."""

        if status not in {"succeeded", "failed", "retrying", "superseded"}:
            raise ValueError("invalid terminal stage-attempt status")
        conditions = [
            CodeGeneratorStageAttempt.id == attempt_id,
            CodeGeneratorStageAttempt.run_id == run_id,
            CodeGeneratorStageAttempt.stage == stage,
            CodeGeneratorStageAttempt.status.in_(("queued", "running", "retrying")),
            CodeGeneratorStageAttempt.expected_run_revision == expected_run_revision,
            CodeGeneratorStageAttempt.input_fingerprint == input_fingerprint,
        ]
        if job_id is not None:
            conditions.append(CodeGeneratorStageAttempt.job_id == job_id)
        values: dict[str, object] = {
            "status": status,
            "safe_error": safe_error,
            "finished_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        if artifact_references is not None:
            values["artifact_references"] = artifact_references
        result = await self._session.execute(
            update(CodeGeneratorStageAttempt)
            .where(*conditions)
            .values(**values)
            .returning(CodeGeneratorStageAttempt)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            await self._session.refresh(row)
        return row
