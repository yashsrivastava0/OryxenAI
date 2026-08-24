"""Short database transactions for the administrator console."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.auth.models import (
    AdminAuditEvent,
    AdminOperation,
    AppUser,
    AppUserCapacity,
    DeletedIdentityTombstone,
    DeletedPortfolioTombstone,
    PortfolioEntitlement,
)
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.models.background_job import BackgroundJob
from oryxenai.db.models.code_generator_development import (
    CodeGeneratorDevelopmentEvent,
    CodeGeneratorDevelopmentRun,
    CodeGeneratorStageAttempt,
)
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.jobs.contracts import JobStatus

_SAFE_DETAIL_KEYS = frozenset(
    {
        "reason_present",
        "local_status",
        "original_action",
        "error_code",
        "can_create_portfolio",
        "reset_count",
        "role",
        "portfolio_count",
        "readmission_approved",
        "portfolio_deleted",
        "had_promoted_success",
        "accepted",
        "session_id",
    }
)
_SAFE_BOOLEAN_KEYS = frozenset(
    {
        "reason_present",
        "can_create_portfolio",
        "readmission_approved",
        "portfolio_deleted",
        "had_promoted_success",
        "accepted",
    }
)
_SAFE_INTEGER_KEYS = frozenset({"reset_count", "portfolio_count"})
_SAFE_STRING_KEYS = frozenset(
    {"local_status", "original_action", "error_code", "role", "session_id"}
)


def validate_safe_details(details: dict[str, object] | None) -> dict[str, object]:
    """Allow only small, content-free facts in durable admin records."""
    if details is None:
        return {}
    if set(details) - _SAFE_DETAIL_KEYS:
        raise ValueError("Unsafe administrator detail key.")
    for key, value in details.items():
        if key in _SAFE_BOOLEAN_KEYS:
            if type(value) is not bool:
                raise ValueError("Unsafe administrator detail value.")
        elif key in _SAFE_INTEGER_KEYS:
            if type(value) is not int or not 0 <= value <= 100_000:
                raise ValueError("Unsafe administrator detail value.")
        elif key in _SAFE_STRING_KEYS:
            if (
                not isinstance(value, str)
                or not 1 <= len(value) <= 128
                or any(ord(char) < 32 for char in value)
                or "@" in value
                or "/" in value
                or "\\" in value
            ):
                raise ValueError("Unsafe administrator detail value.")
        else:
            raise ValueError("Unsafe administrator detail key.")
    return dict(details)


class AdminRepository:
    """Repository that makes lock order visible at each mutation boundary."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user(self, user_id: UUID, *, lock: bool = False) -> AppUser | None:
        stmt = select(AppUser).where(AppUser.id == user_id)
        if lock:
            stmt = stmt.with_for_update()
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def lock_users(self, *user_ids: UUID) -> dict[UUID, AppUser]:
        identifiers = sorted(set(user_ids))
        if not identifiers:
            return {}
        rows = await self.session.execute(
            select(AppUser)
            .where(AppUser.id.in_(identifiers))
            .order_by(AppUser.id)
            .with_for_update()
        )
        return {row.id: row for row in rows.scalars().all()}

    async def lock_capacity(self) -> AppUserCapacity:
        row = await self.session.get(AppUserCapacity, "normal-users", with_for_update=True)
        if row is None:
            row = AppUserCapacity(scope="normal-users", normal_user_limit=15, revision=0)
            self.session.add(row)
            await self.session.flush()
        return row

    async def active_admin_count(self) -> int:
        result = await self.session.execute(
            select(func.count(AppUser.id)).where(
                AppUser.role == "admin",
                AppUser.status == "active",
                AppUser.onboarding_completed_at.is_not(None),
            )
        )
        return int(result.scalar_one())

    async def get_entitlement(
        self, user_id: UUID, *, lock: bool = False
    ) -> PortfolioEntitlement | None:
        stmt = select(PortfolioEntitlement).where(PortfolioEntitlement.user_id == user_id)
        if lock:
            stmt = stmt.with_for_update()
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_identity_tombstone(
        self, former_app_user_id: UUID, *, lock: bool = False
    ) -> DeletedIdentityTombstone | None:
        stmt = select(DeletedIdentityTombstone).where(
            DeletedIdentityTombstone.former_app_user_id == former_app_user_id
        )
        if lock:
            stmt = stmt.with_for_update()
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_session(self, session_id: UUID, *, lock: bool = False) -> PortfolioSession | None:
        stmt = select(PortfolioSession).where(PortfolioSession.id == session_id)
        if lock:
            stmt = stmt.with_for_update()
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def count_running_jobs(self, session_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count(BackgroundJob.id)).where(
                BackgroundJob.portfolio_session_id == session_id,
                BackgroundJob.status == JobStatus.RUNNING.value,
            )
        )
        return int(result.scalar_one())

    async def cancel_queued_jobs(self, session_id: UUID) -> int:
        result = await self.session.execute(
            update(BackgroundJob)
            .where(
                BackgroundJob.portfolio_session_id == session_id,
                BackgroundJob.status == JobStatus.QUEUED.value,
            )
            .values(
                status=JobStatus.FAILED.value,
                error_payload={
                    "code": "PROJECT_DELETION_PENDING",
                    "message": "The portfolio was selected for deletion.",
                    "retryable": False,
                },
                finished_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def find_operation(
        self,
        *,
        actor_id: UUID,
        action: str,
        target_type: str,
        target_id: UUID | None,
        idempotency_key: str,
    ) -> AdminOperation | None:
        result = await self.session.execute(
            select(AdminOperation).where(
                AdminOperation.actor_user_id == actor_id,
                AdminOperation.action == action,
                AdminOperation.target_type == target_type,
                AdminOperation.target_id == target_id,
                AdminOperation.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def create_operation(
        self,
        *,
        actor_id: UUID,
        action: str,
        target_type: str,
        target_id: UUID | None,
        idempotency_key: str,
        fingerprint: str,
        request_id: str,
        safe_details: dict[str, object],
    ) -> tuple[AdminOperation, bool]:
        safe_details = validate_safe_details(safe_details)
        existing = await self.find_operation(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return existing, False
        operation = AdminOperation(
            id=uuid4(),
            actor_user_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            status="running",
            step="requested",
            attempt_count=0,
            safe_state=safe_details,
        )
        self.session.add(operation)
        try:
            async with self.session.begin_nested():
                await self.session.flush()
        except IntegrityError:
            existing = await self.find_operation(
                actor_id=actor_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                idempotency_key=idempotency_key,
            )
            if existing is None:
                raise
            return existing, False
        self.session.add(
            AdminAuditEvent(
                actor_user_id=actor_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                operation_id=operation.id,
                outcome="requested",
                request_id=request_id[:128],
                safe_details=safe_details,
            )
        )
        await self.session.flush()
        return operation, True

    async def add_audit(
        self,
        *,
        actor_id: UUID,
        action: str,
        target_type: str,
        target_id: UUID | None,
        operation_id: UUID | None,
        outcome: str,
        request_id: str,
        safe_details: dict[str, object] | None = None,
    ) -> None:
        safe_details = validate_safe_details(safe_details)
        self.session.add(
            AdminAuditEvent(
                actor_user_id=actor_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                operation_id=operation_id,
                outcome=outcome,
                request_id=request_id[:128],
                safe_details=safe_details or {},
            )
        )
        await self.session.flush()

    async def finish_operation(
        self,
        operation_id: UUID,
        *,
        actor_id: UUID,
        outcome: str,
        request_id: str,
        error_code: str | None = None,
        safe_state: dict[str, object] | None = None,
    ) -> AdminOperation:
        operation = await self.session.get(AdminOperation, operation_id, with_for_update=True)
        if operation is None:
            raise RuntimeError("Administrator operation disappeared.")
        operation.attempt_count += 1
        operation.updated_at = datetime.now(UTC)
        operation.last_error_code = error_code
        if safe_state:
            operation.safe_state = validate_safe_details({**operation.safe_state, **safe_state})
        operation.status = "completed" if outcome == "completed" else "retryable_failure"
        operation.step = "completed" if outcome == "completed" else operation.step
        operation.completed_at = datetime.now(UTC) if outcome == "completed" else None
        await self.add_audit(
            actor_id=actor_id,
            action=operation.action if operation.action else "operation_resume",
            target_type=operation.target_type,
            target_id=operation.target_id,
            operation_id=operation.id,
            outcome=outcome,
            request_id=request_id,
            safe_details={"error_code": error_code} if error_code else safe_state,
        )
        await self.session.flush()
        return operation

    async def list_users(
        self, *, limit: int, cursor: tuple[datetime, UUID] | None
    ) -> list[AppUser]:
        stmt = select(AppUser).order_by(AppUser.created_at.desc(), AppUser.id.desc()).limit(limit)
        if cursor is not None:
            created_at, identifier = cursor
            stmt = stmt.where(
                (AppUser.created_at < created_at)
                | ((AppUser.created_at == created_at) & (AppUser.id < identifier))
            )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_projects(
        self,
        *,
        limit: int,
        cursor: tuple[datetime, UUID] | None,
        legacy: bool | None = None,
    ) -> list[PortfolioSession]:
        conditions: list[Any] = []
        if legacy is not None:
            conditions.append(PortfolioSession.legacy_quarantined.is_(legacy))
        if cursor is not None:
            created_at, identifier = cursor
            conditions.append(
                (PortfolioSession.created_at < created_at)
                | ((PortfolioSession.created_at == created_at) & (PortfolioSession.id < identifier))
            )
        stmt = (
            select(PortfolioSession)
            .where(*conditions)
            .order_by(PortfolioSession.created_at.desc(), PortfolioSession.id.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_tombstones(
        self, *, limit: int, cursor: tuple[datetime, UUID] | None
    ) -> list[DeletedIdentityTombstone]:
        stmt = (
            select(DeletedIdentityTombstone)
            .order_by(
                DeletedIdentityTombstone.deleted_at.desc(), DeletedIdentityTombstone.id.desc()
            )
            .limit(limit)
        )
        if cursor is not None:
            deleted_at, identifier = cursor
            stmt = stmt.where(
                (DeletedIdentityTombstone.deleted_at < deleted_at)
                | (
                    (DeletedIdentityTombstone.deleted_at == deleted_at)
                    & (DeletedIdentityTombstone.id < identifier)
                )
            )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_audit(
        self, *, limit: int, cursor: tuple[datetime, UUID] | None
    ) -> list[AdminAuditEvent]:
        stmt = (
            select(AdminAuditEvent)
            .order_by(AdminAuditEvent.created_at.desc(), AdminAuditEvent.id.desc())
            .limit(limit)
        )
        if cursor is not None:
            created_at, identifier = cursor
            stmt = stmt.where(
                (AdminAuditEvent.created_at < created_at)
                | ((AdminAuditEvent.created_at == created_at) & (AdminAuditEvent.id < identifier))
            )
        return list((await self.session.execute(stmt)).scalars().all())

    async def summary(self) -> dict[str, Any]:
        async def count(model: Any, *conditions: Any) -> int:
            result = await self.session.execute(
                select(func.count()).select_from(model).where(*conditions)
            )
            return int(result.scalar_one())

        pending = await count(
            AdminOperation, AdminOperation.status.in_(("pending", "running", "retryable_failure"))
        )
        return {
            "users": {
                "active": await count(AppUser, AppUser.status == "active"),
                "suspended": await count(AppUser, AppUser.status == "suspended"),
                "deletion_pending": await count(AppUser, AppUser.status == "deletion_pending"),
                "deleted": await count(AppUser, AppUser.status == "deleted"),
            },
            "projects": {
                "active": await count(PortfolioSession, PortfolioSession.status == "active"),
                "deletion_pending": await count(
                    PortfolioSession, PortfolioSession.status == "deletion_pending"
                ),
                "legacy": await count(
                    PortfolioSession, PortfolioSession.legacy_quarantined.is_(True)
                ),
            },
            "jobs": {
                "queued": await count(BackgroundJob, BackgroundJob.status == "queued"),
                "running": await count(BackgroundJob, BackgroundJob.status == "running"),
                "failed": await count(BackgroundJob, BackgroundJob.status == "failed"),
            },
            "pending_operations": pending,
        }

    async def finalize_project_delete(
        self,
        *,
        session: PortfolioSession,
        actor_id: UUID,
        request_id: str,
        operation_id: UUID,
        complete_operation: bool = True,
    ) -> None:
        """Delete one already-fenced aggregate in declared FK order."""
        entitlement = None
        had_success = False
        if session.owner_user_id is not None and not session.legacy_quarantined:
            entitlement = await self.get_entitlement(session.owner_user_id, lock=True)
            had_success = entitlement is not None and entitlement.successful_run_id is not None
            if entitlement is not None and entitlement.portfolio_session_id == session.id:
                entitlement.portfolio_session_id = None
                entitlement.generation_run_id = None
                entitlement.successful_run_id = None
                entitlement.deleted_portfolio_session_id = session.id
                entitlement.project_deleted_at = datetime.now(UTC)
                entitlement.revision += 1
                entitlement.updated_at = datetime.now(UTC)

        await self.session.execute(
            delete(BackgroundJob).where(BackgroundJob.portfolio_session_id == session.id)
        )
        await self.session.execute(
            delete(AgentRun).where(AgentRun.portfolio_session_id == session.id)
        )
        run_ids = select(CodeGeneratorDevelopmentRun.id).where(
            CodeGeneratorDevelopmentRun.portfolio_session_id == session.id
        )
        await self.session.execute(
            delete(CodeGeneratorStageAttempt).where(CodeGeneratorStageAttempt.run_id.in_(run_ids))
        )
        await self.session.execute(
            delete(CodeGeneratorDevelopmentEvent).where(
                CodeGeneratorDevelopmentEvent.run_id.in_(run_ids)
            )
        )
        await self.session.execute(
            delete(CodeGeneratorDevelopmentRun).where(
                CodeGeneratorDevelopmentRun.portfolio_session_id == session.id
            )
        )
        await self.session.execute(
            delete(DeletedPortfolioTombstone).where(
                DeletedPortfolioTombstone.original_session_id == session.id
            )
        )
        self.session.add(
            DeletedPortfolioTombstone(
                original_session_id=session.id,
                former_owner_user_id=None if session.legacy_quarantined else session.owner_user_id,
                legacy_quarantined=session.legacy_quarantined,
                had_promoted_success=had_success,
                deleted_by=actor_id,
            )
        )
        await self.session.execute(
            delete(PortfolioSession).where(PortfolioSession.id == session.id)
        )
        if complete_operation:
            await self.finish_operation(
                operation_id,
                actor_id=actor_id,
                outcome="completed",
                request_id=request_id,
                safe_state={"portfolio_deleted": True, "had_promoted_success": had_success},
            )
