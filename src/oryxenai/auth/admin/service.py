"""Administrator lifecycle orchestration with explicit short transactions."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.agents.code_generator.core import fs_safe
from oryxenai.agents.code_generator.core.development_schemas import ActivePreview
from oryxenai.agents.code_generator.core.workspace import repository_root
from oryxenai.api.errors import AppError, NotFoundError
from oryxenai.auth.admin.masking import bounded_limit, decode_cursor, encode_cursor, mask_email
from oryxenai.auth.admin.provider import AdminIdentityProvider, AdminProviderError
from oryxenai.auth.admin.repository import AdminRepository
from oryxenai.auth.domain import AuthRole
from oryxenai.auth.errors import (
    AdminConfirmationMismatchError,
    AdminDemotionRequiresProjectCleanupError,
    AdminOperationConflictError,
    AdminOperationRetryableError,
    AdminProviderRateLimitedError,
    AdminProviderUnavailableError,
    AdminRequiredError,
    AdminSelfActionForbiddenError,
    DeletedIdentityNotReadmittableError,
    EntitlementResetNotApplicableError,
    LastActiveAdminRequiredError,
    ProjectDeletionPendingError,
    ProjectMustBeDeletedBeforeEntitlementResetError,
    ProjectRunningWorkPendingError,
    StorageCleanupFailedError,
)
from oryxenai.auth.models import (
    AdminOperation,
    AppUser,
    DeletedIdentityTombstone,
    PortfolioEntitlement,
)
from oryxenai.db.models.code_generator_development import (
    CodeGeneratorDevelopmentRun,
    CodeGeneratorStageAttempt,
)
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.storage.artifacts import ArtifactReference


def _fingerprint(action: str, target_id: UUID | None, body: Mapping[str, object]) -> str:
    canonical = json.dumps(
        {"action": action, "target_id": str(target_id) if target_id else None, "body": body},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _preview_host(session_id: UUID) -> str:
    encoded = base64.b32encode(hashlib.sha256(str(session_id).encode()).digest()).decode().lower()
    return f"session-{encoded[:24].rstrip('=')}"


class AdminService:
    """The only application service allowed to mutate administrator state."""

    def __init__(
        self,
        *,
        db: AsyncSession,
        provider: AdminIdentityProvider,
        preview_storage: Any | None = None,
        artifact_store: Any | None = None,
        settings: Any | None = None,
    ) -> None:
        self.repo = AdminRepository(db)
        self.provider = provider
        self.preview_storage = preview_storage
        self.artifact_store = artifact_store
        self.settings = settings

    @staticmethod
    def _request_id(value: str | None) -> str:
        return (value or "").strip()[:128]

    @staticmethod
    def _require_confirmation(target_id: UUID, confirmation: UUID) -> None:
        if target_id != confirmation:
            raise AdminConfirmationMismatchError()

    @staticmethod
    def _require_key(value: str | None) -> str:
        key = (value or "").strip()
        if not 8 <= len(key) <= 128 or any(ord(char) < 33 or ord(char) > 126 for char in key):
            from oryxenai.auth.errors import AdminIdempotencyRequiredError

            raise AdminIdempotencyRequiredError()
        return key

    async def _operation(
        self,
        *,
        actor_id: UUID,
        action: str,
        target_type: str,
        target_id: UUID | None,
        key: str,
        body: Mapping[str, object],
        request_id: str,
    ) -> tuple[AdminOperation, bool]:
        fingerprint = _fingerprint(action, target_id, body)
        operation, created = await self.repo.create_operation(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            idempotency_key=self._require_key(key),
            fingerprint=fingerprint,
            request_id=self._request_id(request_id),
            safe_details={"reason_present": bool(body.get("reason"))},
        )
        if not created and operation.request_fingerprint != fingerprint:
            raise AdminOperationConflictError()
        return operation, created

    async def _replayed_operation(
        self,
        *,
        actor_id: UUID,
        action: str,
        target_type: str,
        target_id: UUID | None,
        key: str,
        body: Mapping[str, object],
    ) -> AdminOperation | None:
        """Return a completed replay before validating the new state.

        A completed idempotent request must remain replayable after the target
        has changed state.  This prevents a successful promotion, deletion,
        reset, or readmission from turning into a misleading validation error
        when the browser retries the same request.
        """
        existing = await self.repo.find_operation(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            idempotency_key=self._require_key(key),
        )
        if existing is None:
            return None
        if existing.request_fingerprint != _fingerprint(action, target_id, body):
            raise AdminOperationConflictError()
        if existing.status == "completed":
            return existing
        return None

    async def _commit(self) -> None:
        await self.repo.session.commit()

    async def _provider_failure(
        self, operation: AdminOperation, actor_id: UUID, request_id: str, exc: AdminProviderError
    ) -> None:
        await self.repo.finish_operation(
            operation.id,
            actor_id=actor_id,
            outcome="retryable",
            request_id=request_id,
            error_code=exc.code,
        )
        await self._commit()
        if exc.code == "AUTH_ADMIN_PROVIDER_RATE_LIMITED":
            raise AdminProviderRateLimitedError() from exc
        if exc.code == "AUTH_ADMIN_PROVIDER_UNAVAILABLE":
            raise AdminProviderUnavailableError() from exc
        raise AppError(
            "The identity provider administrator operation was rejected.",
            code=exc.code,
            status_code=503,
            retryable=exc.retryable,
        ) from exc

    async def suspend_user(
        self,
        *,
        actor_id: UUID,
        target_id: UUID,
        confirmation: UUID,
        username: str | None,
        reason: str | None,
        idempotency_key: str,
        request_id: str,
    ) -> AdminOperation:
        self._require_confirmation(target_id, confirmation)
        await self.repo.lock_capacity()
        users = await self.repo.lock_users(actor_id, target_id)
        actor = users.get(actor_id)
        target = users.get(target_id)
        self._validate_admin_actor(actor)
        self._validate_user_target(actor_id, target, username)
        if actor_id == target_id:
            raise AdminSelfActionForbiddenError()
        if target is None:
            raise NotFoundError("The administrator target was not found.")
        if target.role == AuthRole.ADMIN.value and target.status == "active":
            await self._protect_last_admin()
        operation, created = await self._operation(
            actor_id=actor_id,
            action="suspend",
            target_type="user",
            target_id=target_id,
            key=idempotency_key,
            body={"confirmation": str(confirmation), "username": username, "reason": reason},
            request_id=request_id,
        )
        if not created and operation.status == "completed":
            return operation
        if target.status != "suspended":
            target.status = "suspended"
            target.updated_at = datetime.now(UTC)
            await self.repo.session.flush()
        operation.step = "local_committed"
        await self._commit()
        try:
            if target.supabase_user_id is None:
                raise AdminProviderError("AUTH_ADMIN_PROVIDER_CONFIG_INVALID")
            await self.provider.suspend_user(target.supabase_user_id)
        except AdminProviderError as exc:
            await self._provider_failure(operation, actor_id, request_id, exc)
        operation = await self.repo.finish_operation(
            operation.id,
            actor_id=actor_id,
            outcome="completed",
            request_id=request_id,
            safe_state={"local_status": "suspended"},
        )
        await self._commit()
        return operation

    async def restore_user(
        self,
        *,
        actor_id: UUID,
        target_id: UUID,
        confirmation: UUID,
        username: str | None,
        reason: str | None,
        idempotency_key: str,
        request_id: str,
    ) -> AdminOperation:
        self._require_confirmation(target_id, confirmation)
        users = await self.repo.lock_users(actor_id, target_id)
        actor = users.get(actor_id)
        target = users.get(target_id)
        self._validate_admin_actor(actor)
        self._validate_user_target(actor_id, target, username)
        if target is None:
            raise NotFoundError("The administrator target was not found.")
        if target.status == "deleted":
            raise DeletedIdentityNotReadmittableError()
        operation, created = await self._operation(
            actor_id=actor_id,
            action="restore",
            target_type="user",
            target_id=target_id,
            key=idempotency_key,
            body={"confirmation": str(confirmation), "username": username, "reason": reason},
            request_id=request_id,
        )
        if not created and operation.status == "completed":
            return operation
        operation.step = "provider_pending"
        await self._commit()
        try:
            if target.supabase_user_id is None:
                raise AdminProviderError("AUTH_ADMIN_PROVIDER_CONFIG_INVALID")
            await self.provider.restore_user(target.supabase_user_id)
        except AdminProviderError as exc:
            await self._provider_failure(operation, actor_id, request_id, exc)
        target = await self.repo.get_user(target_id, lock=True)
        if target is None or target.status == "deleted":
            raise DeletedIdentityNotReadmittableError()
        target.status = "active"
        target.updated_at = datetime.now(UTC)
        operation = await self.repo.finish_operation(
            operation.id,
            actor_id=actor_id,
            outcome="completed",
            request_id=request_id,
            safe_state={"local_status": "active"},
        )
        await self._commit()
        return operation

    async def delete_project(
        self,
        *,
        actor_id: UUID,
        session_id: UUID,
        confirmation: UUID,
        reason: str | None,
        idempotency_key: str,
        request_id: str,
        legacy: bool = False,
    ) -> AdminOperation:
        self._require_confirmation(session_id, confirmation)
        self._validate_admin_actor(await self.repo.get_user(actor_id))
        action = "legacy_project_delete" if legacy else "project_delete"
        target_type = "legacy_project" if legacy else "project"
        body = {"confirmation": str(confirmation), "reason": reason}
        replay = await self._replayed_operation(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=session_id,
            key=idempotency_key,
            body=body,
        )
        if replay is not None:
            return replay
        await self.repo.lock_capacity()
        self._validate_admin_actor(await self.repo.get_user(actor_id, lock=True))
        session = await self.repo.get_session(session_id, lock=True)
        if session is None or session.legacy_quarantined is not legacy:
            raise NotFoundError("The portfolio was not found.")
        if session.status == "deleted":
            raise NotFoundError("The portfolio was not found.")
        operation, created = await self._operation(
            actor_id=actor_id,
            action=action,
            target_type="legacy_project" if legacy else "project",
            target_id=session_id,
            key=idempotency_key,
            body=body,
            request_id=request_id,
        )
        if not created and operation.status == "completed":
            return operation
        session.status = "deletion_pending"
        session.deletion_requested_at = datetime.now(UTC)
        session.revision += 1
        session.updated_at = datetime.now(UTC)
        await self.repo.cancel_queued_jobs(session_id)
        operation.step = "cleanup_pending"
        await self._commit()
        return await self._finish_project_cleanup(
            operation=operation,
            actor_id=actor_id,
            session_id=session_id,
            request_id=request_id,
        )

    async def resume_operation(
        self, *, actor_id: UUID, operation_id: UUID, idempotency_key: str, request_id: str
    ) -> AdminOperation:
        self._require_key(idempotency_key)
        self._validate_admin_actor(await self.repo.get_user(actor_id))
        operation = await self.repo.session.get(AdminOperation, operation_id)
        if operation is None:
            raise NotFoundError("The administrator operation was not found.")
        if operation.status == "completed":
            return operation
        await self.repo.add_audit(
            actor_id=actor_id,
            action="operation_resume",
            target_type="operation",
            target_id=operation.id,
            operation_id=operation.id,
            outcome="requested",
            request_id=request_id,
            safe_details={"original_action": operation.action},
        )
        await self._commit()
        if operation.action in {"project_delete", "legacy_project_delete"} and operation.target_id:
            return await self._finish_project_cleanup(
                operation=operation,
                actor_id=actor_id,
                session_id=operation.target_id,
                request_id=request_id,
            )
        if operation.action == "delete" and operation.target_id:
            return await self._complete_user_delete(
                operation=operation,
                actor_id=actor_id,
                target_id=operation.target_id,
                request_id=request_id,
            )
        raise AdminOperationRetryableError()

    async def _complete_user_delete(
        self,
        *,
        operation: AdminOperation,
        actor_id: UUID,
        target_id: UUID,
        request_id: str,
    ) -> AdminOperation:
        """Resume local/project/provider deletion after any retryable step."""
        users = await self.repo.lock_users(actor_id, target_id)
        self._validate_admin_actor(users.get(actor_id))
        target = users.get(target_id)
        if target is None:
            raise NotFoundError("The administrator target was not found.")

        if target.status == "deleted":
            tombstone = await self.repo.get_identity_tombstone(target.id, lock=True)
            if tombstone is None:
                raise DeletedIdentityNotReadmittableError()
            await self.repo.finish_operation(
                operation.id,
                actor_id=actor_id,
                outcome="completed",
                request_id=request_id,
                safe_state={"local_status": "deleted"},
            )
            await self._commit()
            return await self._get_operation(operation.id)

        if target.status != "deletion_pending":
            target.status = "deletion_pending"
            target.deleted_at = None
            target.updated_at = datetime.now(UTC)
        owned = list(
            (
                await self.repo.session.execute(
                    select(PortfolioSession).where(
                        PortfolioSession.owner_user_id == target_id,
                        PortfolioSession.legacy_quarantined.is_(False),
                        PortfolioSession.status != "deleted",
                    )
                )
            )
            .scalars()
            .all()
        )
        for session in owned:
            session.status = "deletion_pending"
            session.deletion_requested_at = datetime.now(UTC)
            session.revision += 1
            await self.repo.cancel_queued_jobs(session.id)
        operation.step = "cleanup_pending"
        await self._commit()
        for session in owned:
            await self._finish_project_cleanup(
                operation=operation,
                actor_id=actor_id,
                session_id=session.id,
                request_id=request_id,
                complete_operation=False,
            )

        target = await self.repo.get_user(target_id, lock=True)
        if target is None or target.supabase_user_id is None:
            raise DeletedIdentityNotReadmittableError()
        try:
            await self.provider.delete_user(target.supabase_user_id)
        except AdminProviderError as exc:
            await self._provider_failure(operation, actor_id, request_id, exc)

        tombstone = await self.repo.get_identity_tombstone(target.id, lock=True)
        if tombstone is None:
            self.repo.session.add(
                DeletedIdentityTombstone(
                    former_app_user_id=target.id,
                    supabase_user_id=target.supabase_user_id,
                    primary_email=target.primary_email,
                    former_role=target.role,
                    deleted_by=actor_id,
                )
            )
        target.status = "deleted"
        target.deleted_at = datetime.now(UTC)
        target.username = None
        target.onboarding_completed_at = None
        target.updated_at = datetime.now(UTC)
        await self.repo.finish_operation(
            operation.id,
            actor_id=actor_id,
            outcome="completed",
            request_id=request_id,
            safe_state={"local_status": "deleted"},
        )
        await self._commit()
        return await self._get_operation(operation.id)

    async def _finish_project_cleanup(
        self,
        *,
        operation: AdminOperation,
        actor_id: UUID,
        session_id: UUID,
        request_id: str,
        complete_operation: bool = True,
    ) -> AdminOperation:
        running = await self.repo.count_running_jobs(session_id)
        if running:
            operation = await self.repo.finish_operation(
                operation.id,
                actor_id=actor_id,
                outcome="retryable",
                request_id=request_id,
                error_code="PROJECT_RUNNING_WORK_PENDING",
            )
            await self._commit()
            raise ProjectRunningWorkPendingError()
        try:
            await self._cleanup_external(session_id)
        except Exception as exc:
            operation = await self.repo.finish_operation(
                operation.id,
                actor_id=actor_id,
                outcome="retryable",
                request_id=request_id,
                error_code="STORAGE_CLEANUP_FAILED",
            )
            await self._commit()
            raise StorageCleanupFailedError() from exc
        session = await self.repo.get_session(session_id, lock=True)
        if session is None:
            return operation
        await self.repo.finalize_project_delete(
            session=session,
            actor_id=actor_id,
            request_id=request_id,
            operation_id=operation.id,
            complete_operation=complete_operation,
        )
        await self._commit()
        return await self._get_operation(operation.id)

    async def reset_entitlement(
        self,
        *,
        actor_id: UUID,
        target_id: UUID,
        confirmation: UUID,
        username: str | None,
        reason: str | None,
        idempotency_key: str,
        request_id: str,
    ) -> AdminOperation:
        self._require_confirmation(target_id, confirmation)
        body: dict[str, object] = {
            "confirmation": str(confirmation),
            "username": username,
            "reason": reason,
        }
        replay = await self._replayed_operation(
            actor_id=actor_id,
            action="reset_entitlement",
            target_type="user",
            target_id=target_id,
            key=idempotency_key,
            body=body,
        )
        if replay is not None:
            return replay
        await self.repo.lock_capacity()
        users = await self.repo.lock_users(actor_id, target_id)
        actor = users.get(actor_id)
        target = users.get(target_id)
        self._validate_admin_actor(actor)
        self._validate_user_target(actor_id, target, username)
        if target is None or target.role != "user":
            raise EntitlementResetNotApplicableError()
        entitlement = await self.repo.get_entitlement(target_id, lock=True)
        if entitlement is None or entitlement.deleted_portfolio_session_id is None:
            raise EntitlementResetNotApplicableError()
        if entitlement.portfolio_session_id is not None:
            raise ProjectMustBeDeletedBeforeEntitlementResetError()
        operation, created = await self._operation(
            actor_id=actor_id,
            action="reset_entitlement",
            target_type="user",
            target_id=target_id,
            key=idempotency_key,
            body=body,
            request_id=request_id,
        )
        if not created and operation.status == "completed":
            return operation
        entitlement.deleted_portfolio_session_id = None
        entitlement.project_deleted_at = None
        entitlement.consumed_at = None
        entitlement.reset_count += 1
        entitlement.last_reset_at = datetime.now(UTC)
        entitlement.revision += 1
        entitlement.updated_at = datetime.now(UTC)
        await self.repo.finish_operation(
            operation.id,
            actor_id=actor_id,
            outcome="completed",
            request_id=request_id,
            safe_state={"can_create_portfolio": True, "reset_count": entitlement.reset_count},
        )
        await self._commit()
        return await self._get_operation(operation.id)

    async def promote_user(self, **kwargs: Any) -> AdminOperation:
        target_id: UUID = kwargs["target_id"]
        actor_id: UUID = kwargs["actor_id"]
        self._require_confirmation(target_id, kwargs["confirmation"])
        body = {
            "confirmation": str(kwargs["confirmation"]),
            "username": kwargs.get("username"),
            "reason": kwargs.get("reason"),
        }
        replay = await self._replayed_operation(
            actor_id=actor_id,
            action="promote",
            target_type="user",
            target_id=target_id,
            key=kwargs["idempotency_key"],
            body=body,
        )
        if replay is not None:
            return replay
        await self.repo.lock_capacity()
        users = await self.repo.lock_users(actor_id, target_id)
        actor = users.get(actor_id)
        target = users.get(target_id)
        self._validate_admin_actor(actor)
        self._validate_user_target(actor_id, target, kwargs.get("username"))
        if target is None or target.role != "user" or target.status != "active":
            raise AdminRequiredError()
        operation, created = await self._operation(
            actor_id=actor_id,
            action="promote",
            target_type="user",
            target_id=target_id,
            key=kwargs["idempotency_key"],
            body=body,
            request_id=kwargs["request_id"],
        )
        if not created and operation.status == "completed":
            return operation
        await self.repo.session.execute(
            delete(PortfolioEntitlement).where(PortfolioEntitlement.user_id == target_id)
        )
        target.role = "admin"
        target.updated_at = datetime.now(UTC)
        await self.repo.finish_operation(
            operation.id,
            actor_id=actor_id,
            outcome="completed",
            request_id=kwargs["request_id"],
            safe_state={"role": "admin"},
        )
        await self._commit()
        return await self._get_operation(operation.id)

    async def demote_user(self, **kwargs: Any) -> AdminOperation:
        target_id: UUID = kwargs["target_id"]
        actor_id: UUID = kwargs["actor_id"]
        self._require_confirmation(target_id, kwargs["confirmation"])
        body = {
            "confirmation": str(kwargs["confirmation"]),
            "username": kwargs.get("username"),
            "reason": kwargs.get("reason"),
        }
        replay = await self._replayed_operation(
            actor_id=actor_id,
            action="demote",
            target_type="user",
            target_id=target_id,
            key=kwargs["idempotency_key"],
            body=body,
        )
        if replay is not None:
            return replay
        await self.repo.lock_capacity()
        users = await self.repo.lock_users(actor_id, target_id)
        actor = users.get(actor_id)
        target = users.get(target_id)
        self._validate_admin_actor(actor)
        self._validate_user_target(actor_id, target, kwargs.get("username"))
        if actor_id == target_id:
            raise AdminSelfActionForbiddenError()
        if target is None or target.role != "admin" or target.status != "active":
            raise AdminRequiredError()
        if await self.repo.active_admin_count() <= 1:
            raise LastActiveAdminRequiredError()
        normal_count = await self.repo.session.scalar(
            select(func.count(AppUser.id)).where(
                AppUser.role == "user",
                AppUser.status.in_(("active", "suspended", "deletion_pending")),
            )
        )
        if int(normal_count or 0) >= 15:
            from oryxenai.auth.errors import UserCapacityReachedError

            raise UserCapacityReachedError()
        sessions = list(
            (
                await self.repo.session.execute(
                    select(PortfolioSession)
                    .where(
                        PortfolioSession.owner_user_id == target_id,
                        PortfolioSession.legacy_quarantined.is_(False),
                        PortfolioSession.status != "deleted",
                    )
                    .order_by(PortfolioSession.id)
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        if len(sessions) > 1:
            raise AdminDemotionRequiresProjectCleanupError()
        operation, created = await self._operation(
            actor_id=actor_id,
            action="demote",
            target_type="user",
            target_id=target_id,
            key=kwargs["idempotency_key"],
            body=body,
            request_id=kwargs["request_id"],
        )
        if not created and operation.status == "completed":
            return operation
        entitlement = await self.repo.get_entitlement(target_id, lock=True)
        if entitlement is None:
            entitlement = PortfolioEntitlement(user_id=target_id)
            self.repo.session.add(entitlement)
        if sessions:
            session = sessions[0]
            run = (
                await self.repo.session.execute(
                    select(CodeGeneratorDevelopmentRun)
                    .where(
                        CodeGeneratorDevelopmentRun.portfolio_session_id == session.id,
                        CodeGeneratorDevelopmentRun.run_mode == "session",
                    )
                    .order_by(CodeGeneratorDevelopmentRun.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            entitlement.portfolio_session_id = session.id
            if run is not None:
                entitlement.generation_run_id = run.id
                verified_preview = None
                if isinstance(run.active_preview, dict):
                    try:
                        verified_preview = ActivePreview.model_validate(run.active_preview)
                    except ValidationError:
                        verified_preview = None
                if (
                    run.status == "ready"
                    and verified_preview is not None
                    and verified_preview.run_id == str(run.id)
                    and verified_preview.receipt_key
                    and verified_preview.receipt_hash
                ):
                    entitlement.successful_run_id = run.id
                    entitlement.consumed_at = datetime.now(UTC)
        target.role = "user"
        target.updated_at = datetime.now(UTC)
        await self.repo.finish_operation(
            operation.id,
            actor_id=actor_id,
            outcome="completed",
            request_id=kwargs["request_id"],
            safe_state={"role": "user", "portfolio_count": len(sessions)},
        )
        await self._commit()
        return await self._get_operation(operation.id)

    async def delete_user(self, **kwargs: Any) -> AdminOperation:
        target_id: UUID = kwargs["target_id"]
        actor_id: UUID = kwargs["actor_id"]
        self._require_confirmation(target_id, kwargs["confirmation"])
        body = {
            "confirmation": str(kwargs["confirmation"]),
            "username": kwargs.get("username"),
            "reason": kwargs.get("reason"),
        }
        replay = await self._replayed_operation(
            actor_id=actor_id,
            action="delete",
            target_type="user",
            target_id=target_id,
            key=kwargs["idempotency_key"],
            body=body,
        )
        if replay is not None:
            return replay
        await self.repo.lock_capacity()
        users = await self.repo.lock_users(actor_id, target_id)
        actor = users.get(actor_id)
        target = users.get(target_id)
        self._validate_admin_actor(actor)
        self._validate_user_target(actor_id, target, kwargs.get("username"))
        if actor_id == target_id:
            raise AdminSelfActionForbiddenError()
        if target is None:
            raise NotFoundError("The administrator target was not found.")
        if target.role == "admin" and target.status == "active":
            await self._protect_last_admin()
        operation, created = await self._operation(
            actor_id=actor_id,
            action="delete",
            target_type="user",
            target_id=target_id,
            key=kwargs["idempotency_key"],
            body=body,
            request_id=kwargs["request_id"],
        )
        if not created and operation.status == "completed":
            return operation
        return await self._complete_user_delete(
            operation=operation,
            actor_id=actor_id,
            target_id=target_id,
            request_id=kwargs["request_id"],
        )

    async def readmit_identity(self, **kwargs: Any) -> AdminOperation:
        tombstone_id: UUID = kwargs["target_id"]
        actor_id: UUID = kwargs["actor_id"]
        self._require_confirmation(tombstone_id, kwargs["confirmation"])
        body = {"confirmation": str(kwargs["confirmation"]), "reason": kwargs.get("reason")}
        replay = await self._replayed_operation(
            actor_id=actor_id,
            action="readmit",
            target_type="identity",
            target_id=tombstone_id,
            key=kwargs["idempotency_key"],
            body=body,
        )
        if replay is not None:
            return replay
        await self.repo.lock_capacity()
        tombstone = await self.repo.session.get(
            DeletedIdentityTombstone, tombstone_id, with_for_update=True
        )
        if tombstone is None or tombstone.readmission_approved_at is not None:
            raise DeletedIdentityNotReadmittableError()
        old = await self.repo.get_user(tombstone.former_app_user_id, lock=True)
        if old is None or old.status != "deleted":
            raise DeletedIdentityNotReadmittableError()
        operation, created = await self._operation(
            actor_id=actor_id,
            action="readmit",
            target_type="identity",
            target_id=tombstone_id,
            key=kwargs["idempotency_key"],
            body=body,
            request_id=kwargs["request_id"],
        )
        if not created and operation.status == "completed":
            return operation
        tombstone.readmission_approved_at = datetime.now(UTC)
        tombstone.readmission_approved_by = actor_id
        tombstone.revision += 1
        old.supabase_user_id = None
        old.primary_email = f"deleted-{old.id}@tombstone.invalid"
        old.updated_at = datetime.now(UTC)
        await self.repo.finish_operation(
            operation.id,
            actor_id=actor_id,
            outcome="completed",
            request_id=kwargs["request_id"],
            safe_state={"readmission_approved": True},
        )
        await self._commit()
        return await self._get_operation(operation.id)

    async def _cleanup_external(self, session_id: UUID) -> None:
        session = await self.repo.get_session(session_id)
        runs = list(
            (
                await self.repo.session.execute(
                    select(CodeGeneratorDevelopmentRun).where(
                        CodeGeneratorDevelopmentRun.portfolio_session_id == session_id
                    )
                )
            )
            .scalars()
            .all()
        )
        stage_attempts = list(
            (
                await self.repo.session.execute(
                    select(CodeGeneratorStageAttempt).where(
                        CodeGeneratorStageAttempt.run_id.in_([run.id for run in runs])
                    )
                )
            )
            .scalars()
            .all()
        )
        await self._cleanup_artifacts(
            session_id,
            self._find_artifact_candidates(session.current_state if session is not None else {})
            + [reference for run in runs for reference in (run.artifact_reference,)]
            + [
                reference
                for attempt in stage_attempts
                for reference in (
                    attempt.artifact_references
                    if isinstance(attempt.artifact_references, list)
                    else []
                )
            ],
        )
        for run in runs:
            await self._cleanup_local_run_paths(run.id)
            active = run.active_preview if isinstance(run.active_preview, dict) else None
            if not active:
                continue
            if self.preview_storage is None:
                raise RuntimeError("preview storage is not configured")
            if str(active.get("run_id", "")) != str(run.id):
                raise ValueError("active preview belongs to another run")
            host = str(active.get("host", ""))
            expected_host = _preview_host(session_id)
            if host != expected_host:
                raise ValueError("unsafe preview host")
            pointer_key = f"preview/hosts/{host}/active.json"
            current = await self.preview_storage.get(pointer_key)
            if current is not None:
                try:
                    pointer = json.loads(current[1].decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ValueError("invalid preview pointer") from exc
                if str(pointer.get("run_id", "")) != str(run.id):
                    raise ValueError("preview pointer belongs to another run")
                await self.preview_storage.delete(pointer_key)
                if await self.preview_storage.head(pointer_key) is not None:
                    raise ValueError("preview pointer remained active")
            receipt_key = str(active.get("receipt_key", ""))
            if (
                not receipt_key.startswith("preview/receipts/")
                or len(receipt_key.split("/")) != 3
                or not receipt_key.endswith(".json")
            ):
                raise ValueError("unsafe preview receipt key")
            await self.preview_storage.delete(receipt_key)
            candidate_prefix = str(active.get("candidate_prefix", ""))
            candidate_parts = candidate_prefix.split("/")
            if (
                len(candidate_parts) != 4
                or candidate_parts[:2] != ["preview", "candidates"]
                or candidate_parts[2] != str(active.get("candidate_id", ""))
                or candidate_parts[3] != str(active.get("build_hash", ""))
            ):
                raise ValueError("unsafe preview candidate prefix")
            continuation = None
            while True:
                keys, continuation = await self.preview_storage.list_prefix(
                    candidate_prefix, limit=100, continuation=continuation
                )
                for key in keys:
                    await self.preview_storage.delete(key)
                if continuation is None or not keys:
                    break

    async def _cleanup_artifacts(self, session_id: UUID, candidates: list[object]) -> None:
        """Delete only typed artifact references scoped to this session."""
        references: dict[str, ArtifactReference] = {}
        session_segment = f"/{session_id}/"
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                continue
            try:
                reference = ArtifactReference.model_validate(candidate)
            except (ValidationError, TypeError, ValueError):
                continue
            if session_segment not in f"/{reference.key.strip('/')}/":
                raise ValueError("artifact reference is outside the deleted session")
            references[reference.key] = reference
        if not references:
            return
        if self.artifact_store is None:
            raise RuntimeError("artifact storage is not configured")
        for reference in references.values():
            await self.artifact_store.delete(reference)

    @staticmethod
    def _find_artifact_candidates(value: object) -> list[object]:
        if isinstance(value, Mapping):
            result: list[object] = [value]
            for nested in value.values():
                result.extend(AdminService._find_artifact_candidates(nested))
            return result
        if isinstance(value, list):
            result = []
            for nested in value:
                result.extend(AdminService._find_artifact_candidates(nested))
            return result
        return []

    async def _cleanup_local_run_paths(self, run_id: UUID) -> None:
        """Remove only exact run children under configured generated roots."""
        if self.settings is None:
            return
        root = repository_root()
        generation = getattr(self.settings, "code_generator_generation", None)
        verification = getattr(self.settings, "code_generator_verification", None)
        configured_roots: list[Path] = []
        for config, attribute in (
            (generation, "workspace_root"),
            (generation, "checkpoint_root"),
        ):
            value = str(getattr(config, attribute, "") or "")
            if value:
                path = Path(value)
                configured_roots.append((path if path.is_absolute() else root / path).resolve())
        for configured in configured_roots:
            target = (configured / str(run_id)).resolve()
            if (
                target.is_relative_to(configured)
                and target != configured
                and not fs_safe.remove_tree(target, required=False)
            ):
                raise OSError("configured generated run path remains locked")
        export_value = str(getattr(verification, "export_root", "") or "")
        if not export_value:
            return
        export_path = Path(export_value)
        export_root = (export_path if export_path.is_absolute() else root / export_path).resolve()
        if not export_root.is_dir() or export_root == root:
            return
        for child in export_root.iterdir():
            if not child.is_dir() or not child.resolve().is_relative_to(export_root):
                continue
            try:
                payload = json.loads((child / "portfolio.json").read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if str(payload.get("run_id", "")) == str(run_id) and not fs_safe.remove_tree(
                child.resolve(), required=False
            ):
                raise OSError("configured export path remains locked")

    async def summary(self) -> dict[str, Any]:
        return await self.repo.summary()

    async def users(self, *, limit: int, cursor: str | None) -> dict[str, Any]:
        limit = bounded_limit(limit)
        rows = await self.repo.list_users(limit=limit + 1, cursor=decode_cursor(cursor))
        more = len(rows) > limit
        rows = rows[:limit]
        items: list[dict[str, Any]] = []
        for user in rows:
            entitlement = await self.repo.get_entitlement(user.id)
            items.append(self._user_projection(user, entitlement))
        return {
            "items": items,
            "next_cursor": encode_cursor(rows[-1].created_at, rows[-1].id)
            if more and rows
            else None,
        }

    async def user(self, user_id: UUID) -> dict[str, Any]:
        user = await self.repo.get_user(user_id)
        if user is None:
            raise NotFoundError("The administrator target was not found.")
        return self._user_projection(user, await self.repo.get_entitlement(user.id))

    async def projects(
        self, *, limit: int, cursor: str | None, legacy: bool | None = None
    ) -> dict[str, Any]:
        limit = bounded_limit(limit)
        rows = await self.repo.list_projects(
            limit=limit + 1, cursor=decode_cursor(cursor), legacy=legacy
        )
        more = len(rows) > limit
        rows = rows[:limit]
        items = [await self._project_projection(session) for session in rows]
        return {
            "items": items,
            "next_cursor": encode_cursor(rows[-1].created_at, rows[-1].id)
            if more and rows
            else None,
        }

    async def project(self, session_id: UUID) -> dict[str, Any]:
        session = await self.repo.get_session(session_id)
        if session is None:
            raise NotFoundError("The portfolio was not found.")
        return await self._project_projection(session)

    async def deleted_identities(self, *, limit: int, cursor: str | None) -> dict[str, Any]:
        limit = bounded_limit(limit)
        rows = await self.repo.list_tombstones(limit=limit + 1, cursor=decode_cursor(cursor))
        more = len(rows) > limit
        rows = rows[:limit]
        items = [
            {
                "id": row.id,
                "former_app_user_id": row.former_app_user_id,
                "masked_email": mask_email(row.primary_email),
                "former_role": row.former_role,
                "deleted_at": row.deleted_at,
                "readmission_approved": row.readmission_approved_at is not None,
            }
            for row in rows
        ]
        return {
            "items": items,
            "next_cursor": encode_cursor(rows[-1].deleted_at, rows[-1].id)
            if more and rows
            else None,
        }

    async def audit_events(self, *, limit: int, cursor: str | None) -> dict[str, Any]:
        limit = bounded_limit(limit)
        rows = await self.repo.list_audit(limit=limit + 1, cursor=decode_cursor(cursor))
        more = len(rows) > limit
        rows = rows[:limit]
        items = [
            {
                "id": row.id,
                "actor_user_id": row.actor_user_id,
                "action": row.action,
                "target_type": row.target_type,
                "target_id": row.target_id,
                "operation_id": row.operation_id,
                "outcome": row.outcome,
                "request_id": row.request_id,
                "safe_details": row.safe_details,
                "created_at": row.created_at,
            }
            for row in rows
        ]
        return {
            "items": items,
            "next_cursor": encode_cursor(rows[-1].created_at, rows[-1].id)
            if more and rows
            else None,
        }

    async def operation(self, operation_id: UUID) -> AdminOperation:
        operation = await self.repo.session.get(AdminOperation, operation_id)
        if operation is None:
            raise NotFoundError("The administrator operation was not found.")
        return operation

    async def code_generator_command(
        self,
        *,
        actor_id: UUID,
        session_id: UUID,
        confirmation: UUID,
        reason: str | None,
        idempotency_key: str,
        request_id: str,
        action: str,
        callback: Any,
    ) -> AdminOperation:
        self._require_confirmation(session_id, confirmation)
        self._validate_admin_actor(await self.repo.get_user(actor_id))
        session = await self.repo.get_session(session_id)
        if session is None:
            raise NotFoundError("The portfolio was not found.")
        if session.status != "active":
            raise ProjectDeletionPendingError()
        operation, created = await self._operation(
            actor_id=actor_id,
            action=action,
            target_type="project",
            target_id=session_id,
            key=idempotency_key,
            body={"confirmation": str(confirmation), "reason": reason},
            request_id=request_id,
        )
        if not created and operation.status == "completed":
            return operation
        operation.step = "local_committed"
        await self._commit()
        try:
            result = await callback()
        except Exception as exc:
            await self.repo.finish_operation(
                operation.id,
                actor_id=actor_id,
                outcome="retryable",
                request_id=request_id,
                error_code=getattr(exc, "code", "ADMIN_OPERATION_RETRYABLE"),
            )
            await self._commit()
            if isinstance(exc, AppError):
                raise
            raise AdminOperationRetryableError() from exc
        safe_result = {}
        if isinstance(result, dict):
            safe_result = {"accepted": True, "session_id": str(session_id)}
        await self.repo.finish_operation(
            operation.id,
            actor_id=actor_id,
            outcome="completed",
            request_id=request_id,
            safe_state=safe_result,
        )
        await self._commit()
        return await self._get_operation(operation.id)

    @staticmethod
    def _user_projection(user: AppUser, entitlement: PortfolioEntitlement | None) -> dict[str, Any]:
        return {
            "id": user.id,
            "username": user.username,
            "masked_email": mask_email(user.primary_email),
            "role": user.role,
            "status": user.status,
            "onboarding_completed": user.onboarding_completed_at is not None,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "last_seen_at": user.last_seen_at,
            "entitlement": {
                "has_live_project": entitlement is not None
                and entitlement.portfolio_session_id is not None,
                "has_deleted_project": entitlement is not None
                and entitlement.deleted_portfolio_session_id is not None,
                "consumed": entitlement is not None and entitlement.consumed_at is not None,
                "revision": entitlement.revision if entitlement is not None else 0,
                "reset_count": entitlement.reset_count if entitlement is not None else 0,
            },
        }

    async def _get_operation(self, operation_id: UUID) -> AdminOperation:
        operation = await self.repo.session.get(AdminOperation, operation_id)
        if operation is None:
            raise RuntimeError("Administrator operation disappeared after commit.")
        return operation

    async def _project_projection(self, session: PortfolioSession) -> dict[str, Any]:
        owner = await self.repo.get_user(session.owner_user_id) if session.owner_user_id else None
        from oryxenai.db.models.background_job import BackgroundJob

        job_counts = await self.repo.session.execute(
            select(BackgroundJob.status, func.count(BackgroundJob.id))
            .where(BackgroundJob.portfolio_session_id == session.id)
            .group_by(BackgroundJob.status)
        )
        counts = {str(status): int(count) for status, count in job_counts.all()}
        run_statuses = await self.repo.session.execute(
            select(CodeGeneratorDevelopmentRun.status).where(
                CodeGeneratorDevelopmentRun.portfolio_session_id == session.id
            )
        )
        stage_statuses = [str(value[0]) for value in run_statuses.all()]
        return {
            "id": session.id,
            "owner_user_id": session.owner_user_id,
            "owner_username": owner.username if owner else None,
            "owner_masked_email": mask_email(owner.primary_email) if owner else None,
            "legacy_quarantined": session.legacy_quarantined,
            "status": session.status,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "stage_statuses": stage_statuses[:20],
            "job_counts": counts,
            "preview_exists": any(
                isinstance(run.active_preview, dict)
                for run in (
                    await self.repo.session.scalars(
                        select(CodeGeneratorDevelopmentRun).where(
                            CodeGeneratorDevelopmentRun.portfolio_session_id == session.id
                        )
                    )
                ).all()
            ),
        }

    @staticmethod
    def _validate_admin_actor(actor: AppUser | None) -> None:
        if (
            actor is None
            or actor.role != "admin"
            or actor.status != "active"
            or actor.onboarding_completed_at is None
        ):
            raise AdminRequiredError()

    @staticmethod
    def _validate_user_target(actor_id: UUID, target: AppUser | None, username: str | None) -> None:
        if target is None:
            raise NotFoundError("The administrator target was not found.")
        if username is not None and username != target.username:
            raise AdminConfirmationMismatchError()

    async def _protect_last_admin(self) -> None:
        if await self.repo.active_admin_count() <= 1:
            raise LastActiveAdminRequiredError()
