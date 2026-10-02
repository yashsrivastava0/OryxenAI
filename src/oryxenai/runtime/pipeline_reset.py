"""Fenced cleanup and reset of a portfolio pipeline."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.auth.admin.provider import AdminIdentityProvider
from oryxenai.auth.admin.service import AdminService
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.models.archived_output import (
    ArchivedOutputAttempt,
    ArchivedOutputEvent,
    ArchivedOutputRun,
)
from oryxenai.db.models.background_job import BackgroundJob
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.models.site_version import PortfolioChatMessage, PortfolioSiteVersion
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository


class PipelineResetError(Exception):
    """Safe, retryable cleanup failure for the API boundary."""


logger = logging.getLogger(__name__)


class PipelineResetService:
    """Reset an owned session or restart a detached development session."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        settings: Any,
        artifact_store: Any | None = None,
        archive_storage: Any | None = None,
        auth_admin_provider: Any | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.artifact_store = artifact_store
        self.archive_storage = archive_storage
        self.auth_admin_provider = auth_admin_provider

    async def restart(self, session_id: UUID, replacement_id: UUID) -> PortfolioSession:
        if session_id == replacement_id:
            raise ValueError("replacement session must have a different ID")

        repo = PortfolioSessionRepository(self.db)
        session = await repo.get_by_id_for_update(session_id)
        if session is None:
            existing = await repo.get_by_id_internal(replacement_id)
            if existing is not None and self._is_empty_detached(existing):
                return existing
            raise LookupError("session not found")
        if getattr(session, "session_mode", "legacy") != "detached":
            raise LookupError("session not found")

        existing_replacement = await repo.get_by_id_internal(replacement_id)
        if existing_replacement is not None:
            if self._is_empty_detached(existing_replacement) and session.status == "deleted":
                return existing_replacement
            raise ValueError("replacement session ID is already in use")

        session.status = "deletion_pending"
        session.revision += 1
        await self.db.execute(
            update(BackgroundJob)
            .where(
                BackgroundJob.portfolio_session_id == session_id,
                BackgroundJob.status == "queued",
            )
            .values(
                status="failed",
                error_payload={
                    "code": "PIPELINE_RESTARTED",
                    "message": "The pipeline was restarted before this job ran.",
                    "retryable": False,
                },
            )
        )
        await self.db.flush()
        # Persist the fence before external cleanup. A failed object-store or
        # filesystem delete therefore leaves the old session unable to accept
        # new work, and a later request can retry cleanup safely.
        await self.db.commit()

        try:
            cleanup = AdminService(
                db=self.db,
                provider=cast(AdminIdentityProvider, self.auth_admin_provider),
                archive_storage=self.archive_storage,
                artifact_store=self.artifact_store,
                settings=self.settings,
            )
            await cleanup._cleanup_external(session_id)
        except Exception as exc:
            await self.db.rollback()
            raise PipelineResetError() from exc

        session = await repo.get_by_id_for_update(session_id)
        if session is None:
            existing = await repo.get_by_id_internal(replacement_id)
            if existing is not None and self._is_empty_detached(existing):
                return existing
            raise LookupError("session not found")

        run_ids = select(ArchivedOutputRun.id).where(
            ArchivedOutputRun.portfolio_session_id == session_id
        )
        await self.db.execute(
            delete(BackgroundJob).where(BackgroundJob.portfolio_session_id == session_id)
        )
        await self.db.execute(delete(AgentRun).where(AgentRun.portfolio_session_id == session_id))
        await self.db.execute(
            delete(ArchivedOutputAttempt).where(ArchivedOutputAttempt.run_id.in_(run_ids))
        )
        await self.db.execute(
            delete(ArchivedOutputEvent).where(ArchivedOutputEvent.run_id.in_(run_ids))
        )
        await self.db.execute(
            delete(ArchivedOutputRun).where(ArchivedOutputRun.portfolio_session_id == session_id)
        )
        await self.db.execute(delete(PortfolioSession).where(PortfolioSession.id == session_id))

        replacement = PortfolioSession(
            id=replacement_id,
            legacy_quarantined=True,
            session_mode="detached",
            name="Untitled session",
            status="active",
            current_state={},
            revision=0,
        )
        self.db.add(replacement)
        await self.db.flush()
        await self.db.refresh(replacement)
        return replacement

    async def reset_admin_pipeline(
        self,
        session_id: UUID,
        actor_id: UUID,
        request_id: str = "",
    ) -> PortfolioSession:
        """Reset a session selected by an administrator."""
        return await self.reset_pipeline(
            session_id,
            actor_id=actor_id,
            request_id=request_id,
            audit_action="admin_pipeline_reset",
        )

    async def reset_pipeline(
        self,
        session_id: UUID,
        *,
        actor_id: UUID | None = None,
        expected_owner_id: UUID | None = None,
        request_id: str = "",
        audit_action: str = "owner_pipeline_reset",
    ) -> PortfolioSession:
        """Fence workers and return one authorized portfolio to empty Discovery."""
        repo = PortfolioSessionRepository(self.db)
        session = await repo.get_by_id_for_update(session_id)
        if session is None or (
            expected_owner_id is not None
            and (session.owner_user_id != expected_owner_id or session.legacy_quarantined)
        ):
            raise LookupError("session not found")

        session.status = "deletion_pending"
        session.revision += 1
        session.updated_at = datetime.now(UTC)
        await self.db.execute(
            update(BackgroundJob)
            .where(
                BackgroundJob.portfolio_session_id == session_id,
                BackgroundJob.status == "queued",
            )
            .values(
                status="failed",
                error_payload={
                    "code": "PIPELINE_RESET",
                    "message": "The portfolio pipeline was reset.",
                    "retryable": False,
                },
            )
        )
        await self.db.flush()
        # Persist the fence before external cleanup.
        await self.db.commit()

        try:
            cleanup = AdminService(
                db=self.db,
                provider=cast(AdminIdentityProvider, self.auth_admin_provider),
                archive_storage=self.archive_storage,
                artifact_store=self.artifact_store,
                settings=self.settings,
            )
            await cleanup._cleanup_external(session_id)
        except Exception as exc:
            await self.db.rollback()
            raise PipelineResetError() from exc

        session = await repo.get_by_id_for_update(session_id)
        if session is None:
            raise LookupError("session not found")

        run_ids = select(ArchivedOutputRun.id).where(
            ArchivedOutputRun.portfolio_session_id == session_id
        )
        await self.db.execute(
            delete(BackgroundJob).where(BackgroundJob.portfolio_session_id == session_id)
        )
        await self.db.execute(delete(AgentRun).where(AgentRun.portfolio_session_id == session_id))
        await self.db.execute(
            delete(ArchivedOutputAttempt).where(ArchivedOutputAttempt.run_id.in_(run_ids))
        )
        await self.db.execute(
            delete(ArchivedOutputEvent).where(ArchivedOutputEvent.run_id.in_(run_ids))
        )
        await self.db.execute(
            delete(ArchivedOutputRun).where(ArchivedOutputRun.portfolio_session_id == session_id)
        )

        # The session row survives an admin reset, so its generated pages and
        # chat go explicitly (they would otherwise only cascade with the row).
        await self.db.execute(
            delete(PortfolioChatMessage).where(
                PortfolioChatMessage.portfolio_session_id == session_id
            )
        )
        await self.db.execute(
            delete(PortfolioSiteVersion).where(
                PortfolioSiteVersion.portfolio_session_id == session_id
            )
        )

        session.current_state = {}
        session.status = "active"
        session.revision += 1
        session.updated_at = datetime.now(UTC)
        await self.db.flush()

        if self.auth_admin_provider is not None and actor_id is not None:
            try:
                from oryxenai.auth.admin.repository import AdminRepository

                admin_repo = AdminRepository(self.db)
                await admin_repo.add_audit(
                    actor_id=actor_id,
                    action=audit_action,
                    target_type="project",
                    target_id=session_id,
                    operation_id=None,
                    outcome="completed",
                    request_id=request_id,
                    safe_details={"message": "Pipeline reset to zero."},
                )
                await self.db.flush()
            except Exception as exc:
                logger.warning("Failed to record admin reset audit: %s", exc)

        await self.db.commit()
        await self.db.refresh(session)
        return session

    @staticmethod
    def _is_empty_detached(session: PortfolioSession | None) -> bool:
        return bool(
            session is not None
            and getattr(session, "session_mode", "legacy") == "detached"
            and session.status == "active"
            and session.revision == 0
            and not session.current_state
        )
