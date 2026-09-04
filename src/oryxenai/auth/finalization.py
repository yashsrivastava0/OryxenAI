"""Central post-promotion finalization for the Phase 3 success boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select

from oryxenai.agents.code_generator.core.pipeline_contract import is_verification_kind
from oryxenai.auth.errors import EntitlementBindingConflictError
from oryxenai.auth.models import AppUser, PortfolioEntitlement
from oryxenai.auth.worker_fence import WorkerAuthorizationFence
from oryxenai.db.models.background_job import BackgroundJob
from oryxenai.db.models.code_generator_development import CodeGeneratorDevelopmentRun
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.repositories.code_generator_development import CodeGeneratorDevelopmentRepository


async def finalize_promoted_success(
    sessionmaker: Any,
    *,
    run_id: UUID,
    active_preview: Any,
    projection: Any,
    values: dict[str, object],
    event: tuple[str, str] = ("promoted", "Verified portfolio preview promoted atomically."),
    job_id: UUID | None = None,
    attempt: int | None = None,
    lease_token: str | None = None,
) -> None:
    """Finalize one already-read-back pointer and consume normal entitlement once.

    Object storage and public read-back must have completed before this short
    database transaction starts.  A replay is idempotent only for the exact
    same run and promoted preview receipt.
    """

    active_payload = (
        active_preview.model_dump(mode="json")
        if hasattr(active_preview, "model_dump")
        else dict(active_preview)
    )
    async with sessionmaker() as db:
        repo = CodeGeneratorDevelopmentRepository(db)
        run = await repo.get(run_id)
        if run is None:
            raise EntitlementBindingConflictError()
        await WorkerAuthorizationFence(db).validate_run(run_id)

        owner_id = getattr(run, "owner_user_id", None)
        actor_id = getattr(run, "actor_user_id", None)
        normal_owner = False
        if (
            getattr(run, "authorization_context_version", 0) == 1
            and owner_id is not None
            and actor_id is not None
            and owner_id == actor_id
        ):
            user_result = await db.execute(select(AppUser).where(AppUser.id == owner_id))
            owner = user_result.scalar_one_or_none()
            normal_owner = owner is not None and owner.role == "user"

        if normal_owner:
            # Lock order: identity rows -> entitlement -> session -> run.
            assert owner_id is not None and actor_id is not None
            users: dict[UUID, AppUser] = {}
            for user_id in sorted({owner_id, actor_id}, key=str):
                user_result = await db.execute(
                    select(AppUser).where(AppUser.id == user_id).with_for_update()
                )
                user = user_result.scalar_one_or_none()
                if user is not None:
                    users[user_id] = user
            if (
                owner_id not in users
                or actor_id not in users
                or users[owner_id].status != "active"
                or users[actor_id].status != "active"
                or users[owner_id].role != "user"
                or users[actor_id].role != "user"
            ):
                raise EntitlementBindingConflictError()
            entitlement_result = await db.execute(
                select(PortfolioEntitlement)
                .where(PortfolioEntitlement.user_id == owner_id)
                .with_for_update()
            )
            entitlement = entitlement_result.scalar_one_or_none()
            if entitlement is None:
                raise EntitlementBindingConflictError()
            session_result = await db.execute(
                select(PortfolioSession)
                .where(PortfolioSession.id == run.portfolio_session_id)
                .with_for_update()
            )
            session = session_result.scalar_one_or_none()
            run_result = await db.execute(
                select(CodeGeneratorDevelopmentRun)
                .where(CodeGeneratorDevelopmentRun.id == run_id)
                .with_for_update()
            )
            locked_run = run_result.scalar_one_or_none()
            if (
                session is None
                or locked_run is None
                or session.owner_user_id != owner_id
                or session.legacy_quarantined
                or entitlement.portfolio_session_id != session.id
                or entitlement.generation_run_id != run_id
                or (
                    entitlement.successful_run_id is None
                    and entitlement.revision != locked_run.entitlement_revision
                )
                or (
                    entitlement.successful_run_id is not None
                    and (
                        entitlement.successful_run_id != run_id
                        or entitlement.revision != (locked_run.entitlement_revision or 0) + 1
                    )
                )
                or str(locked_run.run_mode) != "session"
            ):
                raise EntitlementBindingConflictError()
            if entitlement.successful_run_id == run_id and locked_run.status == "ready":
                # A crash/replay after the database commit is idempotent only
                # for the exact pointer already stored on this run.  The
                # pending evidence was intentionally cleared by the first
                # successful finalization, so do not require it again.
                _assert_existing_pointer(locked_run, active_payload)
                await WorkerAuthorizationFence(db).validate_run(run_id)
                await db.commit()
                return
            _assert_promotion_evidence(locked_run, active_payload, projection, values)
            _assert_existing_pointer(locked_run, active_payload)
            await _lock_current_job(
                db,
                job_id=job_id,
                attempt=attempt,
                lease_token=lease_token,
                run=locked_run,
            )
            await WorkerAuthorizationFence(db).validate_run(run_id)
            await _persist_ready(
                db,
                repo,
                locked_run,
                run_id,
                projection,
                active_payload,
                values,
                event,
                session,
            )
            if entitlement.successful_run_id is None:
                entitlement.successful_run_id = run_id
                entitlement.consumed_at = datetime.now(UTC)
                entitlement.revision += 1
                entitlement.updated_at = datetime.now(UTC)
            # The run is now ready and the exact pointer is durable in this
            # transaction. The second fence proves the only permitted
            # post-success shape before commit/replay.
            await WorkerAuthorizationFence(db).validate_run(run_id)
            await db.commit()
            return

        # Admin-owned and admin-on-user operations remain outside the normal
        # one-success entitlement; they still get the durable worker fence.
        # Keep the same lock order as the normal path. The initial run was
        # fenced above, so its immutable owner/actor/session IDs are safe
        # inputs for this short lock sequence.
        owner_id = getattr(run, "owner_user_id", None)
        actor_id = getattr(run, "actor_user_id", None)
        for user_id in sorted({item for item in (owner_id, actor_id) if item is not None}, key=str):
            user_result = await db.execute(
                select(AppUser).where(AppUser.id == user_id).with_for_update()
            )
            user = user_result.scalar_one_or_none()
            if user is None or user.status != "active":
                raise EntitlementBindingConflictError()
        session = None
        if run.portfolio_session_id is not None:
            session_result = await db.execute(
                select(PortfolioSession)
                .where(PortfolioSession.id == run.portfolio_session_id)
                .with_for_update()
            )
            session = session_result.scalar_one_or_none()
            if session is None or session.legacy_quarantined or session.owner_user_id != owner_id:
                raise EntitlementBindingConflictError()
        run_result = await db.execute(
            select(CodeGeneratorDevelopmentRun)
            .where(CodeGeneratorDevelopmentRun.id == run_id)
            .with_for_update()
        )
        locked_run = run_result.scalar_one_or_none()
        if (
            locked_run is None
            or locked_run.owner_user_id != owner_id
            or locked_run.actor_user_id != actor_id
            or locked_run.portfolio_session_id != run.portfolio_session_id
        ):
            raise EntitlementBindingConflictError()
        if locked_run.status == "ready":
            _assert_existing_pointer(locked_run, active_payload)
            await WorkerAuthorizationFence(db).validate_run(run_id)
            await db.commit()
            return
        _assert_promotion_evidence(locked_run, active_payload, projection, values)
        _assert_existing_pointer(locked_run, active_payload)
        await _lock_current_job(
            db,
            job_id=job_id,
            attempt=attempt,
            lease_token=lease_token,
            run=locked_run,
        )
        await WorkerAuthorizationFence(db).validate_run(run_id)
        await _persist_ready(
            db,
            repo,
            locked_run,
            run_id,
            projection,
            active_payload,
            values,
            event,
            session,
        )
        await db.commit()


async def _lock_current_job(
    db: Any,
    *,
    job_id: UUID | None,
    attempt: int | None,
    lease_token: str | None,
    run: CodeGeneratorDevelopmentRun,
) -> None:
    if job_id is None:
        return
    job_result = await db.execute(
        select(BackgroundJob).where(BackgroundJob.id == job_id).with_for_update()
    )
    job = job_result.scalar_one_or_none()
    if (
        job is None
        or not is_verification_kind(str(job.job_kind))
        or job.status != "running"
        or (attempt is not None and job.attempt != attempt)
        or (lease_token is not None and job.lease_token != lease_token)
        or job.authorization_context_version != run.authorization_context_version
        or job.portfolio_session_id != run.portfolio_session_id
        or job.owner_user_id != run.owner_user_id
        or job.actor_user_id != run.actor_user_id
        or job.entitlement_revision != run.entitlement_revision
    ):
        raise EntitlementBindingConflictError()


async def _persist_ready(
    db: Any,
    repo: CodeGeneratorDevelopmentRepository,
    run: CodeGeneratorDevelopmentRun,
    run_id: UUID,
    projection: Any,
    active_payload: dict[str, Any],
    values: dict[str, object],
    event: tuple[str, str],
    session: PortfolioSession | None,
) -> None:
    updated_values = {
        "verification_projection": projection.model_dump(mode="json"),
        "issues": [],
        "status": "ready",
        **values,
        "pending_promotion": None,
        "active_preview": active_payload,
        "terminal_failure": None,
    }
    updated = await repo.compare_and_swap(
        run_id,
        expected_revision=run.revision,
        values=updated_values,
    )
    if updated is None:
        raise EntitlementBindingConflictError()
    if session is not None:
        state = dict(session.current_state or {})
        raw_codegen = state.get("code_generator")
        codegen = dict(raw_codegen) if isinstance(raw_codegen, dict) else {}
        codegen.update(
            {
                "status": "ready",
                "current_run_id": str(run_id),
                "active_preview": active_payload,
                "latest_error": None,
                "retry_status": "",
            }
        )
        state["code_generator"] = codegen
        session.current_state = state
        session.revision += 1
        session.updated_at = datetime.now(UTC)
    await repo.append_event(run_id, event_type=event[0], level="info", message=event[1])


def _assert_promotion_evidence(
    run: CodeGeneratorDevelopmentRun,
    active_payload: dict[str, Any],
    projection: Any,
    values: dict[str, object],
) -> None:
    """Require the database receipt and active pointer to describe one run."""

    candidate = run.candidate_artifact if isinstance(run.candidate_artifact, dict) else {}
    pending = run.pending_promotion if isinstance(run.pending_promotion, dict) else {}
    pending_candidate = pending.get("candidate")
    if not isinstance(pending_candidate, dict):
        raise EntitlementBindingConflictError()
    if str(active_payload.get("run_id", "")) != str(run.id):
        raise EntitlementBindingConflictError()
    for key in ("candidate_id", "candidate_identity_hash", "build_hash"):
        expected = candidate.get(key)
        if (
            not expected
            or expected != pending_candidate.get(key)
            or expected != active_payload.get(key)
        ):
            raise EntitlementBindingConflictError()
    promotion_id = str(pending.get("promotion_id", ""))
    receipt_key = str(active_payload.get("receipt_key", ""))
    if not promotion_id or receipt_key != f"preview/receipts/{promotion_id}.json":
        raise EntitlementBindingConflictError()
    if not str(active_payload.get("receipt_hash", "")):
        raise EntitlementBindingConflictError()
    pending_report_hash = str(pending.get("verification_report_hash", ""))
    projection_report_hash = (
        projection.get("verification_report_hash", "")
        if isinstance(projection, dict)
        else getattr(projection, "verification_report_hash", "")
    )
    projection_report_hash = str(projection_report_hash or "")
    if not pending_report_hash or pending_report_hash != projection_report_hash:
        raise EntitlementBindingConflictError()
    source_summary = values.get("source_summary")
    if isinstance(source_summary, dict) and source_summary.get("build_hash") not in {
        None,
        active_payload.get("build_hash"),
    }:
        raise EntitlementBindingConflictError()
    public_readback = active_payload.get("public_readback")
    if public_readback is not None:
        if not isinstance(public_readback, dict):
            raise EntitlementBindingConflictError()
        if (
            public_readback.get("promotion_id") != promotion_id
            or public_readback.get("candidate_id") != active_payload.get("candidate_id")
            or public_readback.get("build_hash") != active_payload.get("build_hash")
            or not public_readback.get("receipt_hash")
        ):
            raise EntitlementBindingConflictError()


def _assert_existing_pointer(
    run: CodeGeneratorDevelopmentRun, active_payload: dict[str, Any]
) -> None:
    existing = run.active_preview if isinstance(run.active_preview, dict) else None
    if existing is None:
        return
    for key in (
        "run_id",
        "candidate_id",
        "candidate_identity_hash",
        "build_hash",
        "receipt_key",
        "receipt_hash",
    ):
        if existing.get(key) != active_payload.get(key):
            raise EntitlementBindingConflictError()
