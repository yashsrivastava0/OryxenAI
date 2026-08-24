"""Hard-reset service for the temporary anonymous pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.agents.code_generator.core import fs_safe
from oryxenai.agents.code_generator.core.workspace import repository_root
from oryxenai.auth.admin.provider import AdminIdentityProvider
from oryxenai.auth.admin.service import AdminService
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.models.background_job import BackgroundJob
from oryxenai.db.models.code_generator_development import (
    CodeGeneratorDevelopmentEvent,
    CodeGeneratorDevelopmentRun,
    CodeGeneratorStageAttempt,
)
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository


class PipelineResetError(Exception):
    """Safe, retryable cleanup failure for the API boundary."""


class PipelineResetService:
    """Fence, clean, delete, and recreate exactly one detached session."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        settings: Any,
        artifact_store: Any | None = None,
        preview_storage: Any | None = None,
        auth_admin_provider: Any | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.artifact_store = artifact_store
        self.preview_storage = preview_storage
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

        state_snapshot = dict(session.current_state or {})
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
                preview_storage=self.preview_storage,
                artifact_store=self.artifact_store,
                settings=self.settings,
            )
            await cleanup._cleanup_external(session_id)
            self._cleanup_build_preparation_paths(state_snapshot)
        except Exception as exc:
            await self.db.rollback()
            raise PipelineResetError() from exc

        session = await repo.get_by_id_for_update(session_id)
        if session is None:
            existing = await repo.get_by_id_internal(replacement_id)
            if existing is not None and self._is_empty_detached(existing):
                return existing
            raise LookupError("session not found")

        run_ids = select(CodeGeneratorDevelopmentRun.id).where(
            CodeGeneratorDevelopmentRun.portfolio_session_id == session_id
        )
        await self.db.execute(delete(BackgroundJob).where(BackgroundJob.portfolio_session_id == session_id))
        await self.db.execute(delete(AgentRun).where(AgentRun.portfolio_session_id == session_id))
        await self.db.execute(
            delete(CodeGeneratorStageAttempt).where(CodeGeneratorStageAttempt.run_id.in_(run_ids))
        )
        await self.db.execute(
            delete(CodeGeneratorDevelopmentEvent).where(CodeGeneratorDevelopmentEvent.run_id.in_(run_ids))
        )
        await self.db.execute(
            delete(CodeGeneratorDevelopmentRun).where(
                CodeGeneratorDevelopmentRun.portfolio_session_id == session_id
            )
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

    @staticmethod
    def _is_empty_detached(session: PortfolioSession | None) -> bool:
        return bool(
            session is not None
            and getattr(session, "session_mode", "legacy") == "detached"
            and session.status == "active"
            and session.revision == 0
            and not session.current_state
        )

    def _cleanup_build_preparation_paths(self, state: Mapping[str, object]) -> None:
        roots: list[Path] = []
        root_config = getattr(self.settings.build_preparation, "session_staging_root", "")
        mirror_config = getattr(
            self.settings.code_generator_development, "build_preparation_mirror_root", ""
        )
        for raw in (root_config, mirror_config):
            value = str(raw or "")
            if not value:
                continue
            path = Path(value)
            roots.append((path if path.is_absolute() else repository_root() / path).resolve())

        paths: list[Path] = []

        def visit(value: object, key: str = "") -> None:
            if isinstance(value, Mapping):
                for child_key, child in value.items():
                    visit(child, str(child_key))
            elif isinstance(value, list):
                for child in value:
                    visit(child, key)
            elif key in {"mirror_root", "local_archive_path"} and isinstance(value, str):
                paths.append(Path(value))

        visit(state)
        for raw_path in paths:
            path = raw_path if raw_path.is_absolute() else (repository_root() / raw_path)
            target = path.resolve()
            allowed_root = next((root for root in roots if target.is_relative_to(root)), None)
            if allowed_root is None or target == allowed_root:
                raise OSError("build preparation path is outside configured cleanup roots")
            if target.name == "build-context":
                target = target.parent
                if target == allowed_root:
                    raise OSError("build preparation mirror resolved to its configured root")
            if target.is_dir():
                if not fs_safe.remove_tree(target, required=False):
                    raise OSError("build preparation mirror remains locked")
            elif target.exists():
                target.unlink()
