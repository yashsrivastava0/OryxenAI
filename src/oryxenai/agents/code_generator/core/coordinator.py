"""Durable server-side stage advancement for standalone Code Generator runs."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from oryxenai.agents.code_generator.core.stage_attempt import (
    StageAttemptToken,
    StageCoordinator,
    fingerprint_input,
    stage_idempotency_key,
)
from oryxenai.db.repositories.code_generator_development import CodeGeneratorDevelopmentRepository
from oryxenai.jobs.service import JobService


async def advance_after(
    sessionmaker: Any,
    run_id: UUID,
    *,
    completed_stage: str,
) -> bool:
    """Queue the next stage once, without chaining Build Preparation itself."""

    transitions = {
        "planned": ("acquire", "code_generator.acquire", "acquiring", "acquire_job_id"),
        "acquired": ("generate", "code_generator.generate", "queued", "generation_job_id"),
        "source_ready": (
            "verify",
            "code_generator.verify_and_preview",
            "queued",
            "verification_job_id",
        ),
    }
    transition = transitions.get(completed_stage)
    if transition is None:
        return False
    stage, kind, status, job_field = transition
    async with sessionmaker() as db:
        repo = CodeGeneratorDevelopmentRepository(db)
        run = await repo.get(run_id)
        if run is None or not bool(getattr(run, "auto_advance", True)):
            return False
        if run.status == "needs_attention" or run.active_preview:
            return False
        if str(getattr(run, "coordinator_stage", "plan")) == stage:
            return False
        key_material = {
            "planned": str((run.planner_receipt or {}).get("plan_hash", "")),
            "acquired": str((run.resource_ledger or {}).get("ledger_hash", "")),
            "source_ready": str((run.source_checkpoint or {}).get("checkpoint_hash", "")),
        }[completed_stage]
        idempotency_key = f"{run.id}:{stage}:{key_material}:{run.revision}"
        payload_key = (
            "code_generator_run_id"
            if str(getattr(run, "run_mode", "development")) == "session"
            else "development_run_id"
        )
        input_fingerprint = fingerprint_input(
            {
                "completed_stage": completed_stage,
                "key_material": key_material,
                "revision": run.revision,
            }
        )
        next_attempt = await repo.create_stage_attempt(
            run.id,
            stage=stage,
            input_fingerprint=input_fingerprint,
            idempotency_key=stage_idempotency_key(run.id, stage, input_fingerprint),
            expected_run_revision=run.revision,
            trace_id=str(getattr(run, "trace_id", "") or ""),
            worker_version=str(getattr(run, "pipeline_contract_version", "") or ""),
        )
        token = StageAttemptToken(
            attempt_id=next_attempt.id,
            run_id=run.id,
            stage=stage,
            attempt_no=next_attempt.attempt_no,
            expected_run_revision=run.revision,
            input_fingerprint=input_fingerprint,
            trace_id=str(getattr(run, "trace_id", "") or ""),
        )
        job = await JobService(db).enqueue(
            kind,
            StageCoordinator.payload_for_attempt(
                token, {payload_key: str(run.id), "coordinator_stage": stage}
            ),
            idempotency_scope=kind,
            idempotency_key=idempotency_key,
        )
        values: dict[str, object] = {
            "status": status,
            "coordinator_stage": stage,
            job_field: job.id,
            "active_attempt_id": next_attempt.id,
        }
        updated = await repo.compare_and_swap(run.id, expected_revision=run.revision, values=values)
        if updated is None:
            await db.rollback()
            return False
        await repo.bind_stage_attempt_job(next_attempt.id, job_id=job.id)
        await repo.append_event(
            run.id,
            event_type=f"coordinator_queued_{stage}",
            level="info",
            message=f"Coordinator queued the durable {stage} stage.",
            details={"job_id": str(job.id), "idempotency_key": idempotency_key},
        )
        await db.commit()
        return True
