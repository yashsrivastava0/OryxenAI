"""System diagnostics routes — worker status, probe lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.api.dependencies import get_db_session
from oryxenai.api.errors import NotFoundError, PayloadTooLargeError, ValidationError
from oryxenai.core.logging import get_logger
from oryxenai.jobs.contracts import SYSTEM_PROBE_KIND, EnqueueRequest, ProbePayload
from oryxenai.jobs.heartbeat import HeartbeatRepository
from oryxenai.jobs.registry import is_registered
from oryxenai.jobs.repository import JobRepository
from oryxenai.jobs.service import JobService

router = APIRouter(prefix="/system", tags=["system"])
logger = get_logger("oryxenai.api.system")


class SystemStatusResponse(BaseModel):
    application: str
    database: str
    migration_revision: str
    worker: str
    latest_heartbeat_age: float | None
    worker_instance: str | None


class WorkerProbeResponse(BaseModel):
    id: str
    job_kind: str
    status: str
    attempt: int
    max_attempts: int
    created_at: str
    started_at: str | None
    finished_at: str | None
    result: dict[str, Any] | None
    error: dict[str, Any] | None
    worker_instance: str | None


# ── system status ───────────────────────────────────────────────────────────


@router.get("/status", response_model=SystemStatusResponse)
async def system_status(
    db: AsyncSession = Depends(get_db_session),
) -> SystemStatusResponse:
    """Return aggregate system status including worker liveness."""
    app_status = "ok"
    db_status = "up"
    revision = "unknown"
    worker_status = "unknown"
    age = None
    instance = None

    # Database ping.
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"
        await db.rollback()

    # Migration revision.
    try:
        row = (
            await db.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar_one_or_none()
        if row:
            revision = str(row)
    except Exception:
        revision = "unavailable"
        await db.rollback()

    # Worker heartbeat.
    try:
        repo = HeartbeatRepository(db)
        latest = await repo.get_latest()
        if latest is not None:
            now = datetime.now(UTC)
            age = (now - latest.last_seen_at).total_seconds()
            instance = str(latest.instance_id)
            from oryxenai.core.settings import get_settings

            settings = get_settings()
            worker_status = "ok" if age <= settings.diagnostics.heartbeat_staleness else "stale"
        else:
            worker_status = "absent"
    except Exception as exc:
        logger.warning("worker heartbeat lookup failed: %s", type(exc).__name__)
        await db.rollback()
        worker_status = "absent"

    return SystemStatusResponse(
        application=app_status,
        database=db_status,
        migration_revision=revision,
        worker=worker_status,
        latest_heartbeat_age=age,
        worker_instance=instance,
    )


# ── worker probe ───────────────────────────────────────────────────────────


@router.post("/worker-probes", response_model=WorkerProbeResponse, status_code=201)
async def enqueue_worker_probe(
    body: EnqueueRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    """Enqueue a system.worker_probe job. Only the built-in probe is accepted."""

    # Only the registered infrastructure probe is allowed.
    if body.job_kind != SYSTEM_PROBE_KIND:
        raise ValidationError(
            f"Only '{SYSTEM_PROBE_KIND}' is accepted.",
            details={"provided": body.job_kind},
        )
    if not is_registered(SYSTEM_PROBE_KIND):
        raise ValidationError("Worker probe handler is not registered.")

    # Validate the probe payload.
    ProbePayload(**body.payload)

    # Size guard.
    import json

    raw = json.dumps(body.payload).encode("utf-8")
    from oryxenai.core.settings import get_settings

    if len(raw) > get_settings().api.max_input_bytes:
        raise PayloadTooLargeError(f"Payload exceeds {get_settings().api.max_input_bytes} bytes.")

    service = JobService(db)
    job = await service.enqueue(
        job_kind=SYSTEM_PROBE_KIND,
        payload=body.payload,
        idempotency_scope=body.idempotency_scope or "",
        idempotency_key=body.idempotency_key or "",
    )
    await db.flush()

    return _to_probe_response(job)


@router.get("/worker-probes/{job_id}", response_model=WorkerProbeResponse)
async def get_worker_probe(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    try:
        jid = UUID(job_id)
    except ValueError as exc:
        raise ValidationError(f"Invalid job ID: '{job_id}'") from exc
    repo = JobRepository(db)
    job = await repo.get_by_id(jid)
    if job is None:
        raise NotFoundError("Job not found.", code="JOB_NOT_FOUND", details={"job_id": job_id})
    return _to_probe_response(job)


# ── helpers ─────────────────────────────────────────────────────────────────


def _to_probe_response(job: Any) -> WorkerProbeResponse:
    finished: datetime | None = getattr(job, "finished_at", None)
    return WorkerProbeResponse(
        id=str(job.id),
        job_kind=job.job_kind,
        status=job.status,
        attempt=job.attempt,
        max_attempts=job.max_attempts,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=finished.isoformat() if finished else None,
        result=dict(job.result) if job.result else None,
        error=dict(job.error_payload) if job.error_payload else None,
        worker_instance=job.locked_by,
    )
