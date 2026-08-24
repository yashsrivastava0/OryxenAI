"""Job service — thin wrapper for enqueue operations used by the API layer."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.auth.authorization import DurableAuthorizationContext, durable_snapshot
from oryxenai.auth.errors import EntitlementBindingConflictError
from oryxenai.db.models.code_generator_development import CodeGeneratorDevelopmentRun
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.jobs.policy import MODEL_GENERATION_LANE, policy_for
from oryxenai.jobs.repository import JobRepository


class JobService:
    """Service for enqueuing durable background jobs.

    Accepts an existing SQLAlchemy session so that enqueue can participate
    in the caller's transaction.
    """

    def __init__(
        self,
        session: AsyncSession,
        authorization_context: DurableAuthorizationContext | None = None,
    ) -> None:
        self._repo = JobRepository(session)
        self._session = session
        self.authorization_context = authorization_context

    async def enqueue(
        self,
        job_kind: str,
        payload: dict[str, Any],
        *,
        priority: int = 0,
        max_attempts: int = 3,
        idempotency_scope: str = "",
        idempotency_key: str = "",
    ) -> Any:
        """Enqueue a job; returns the persisted BackgroundJob row."""
        scope = idempotency_scope or None
        key = idempotency_key or None
        if scope and key:
            existing = await self._repo.find_idempotent(scope, key)
            if existing is not None:
                return existing
        policy = policy_for(job_kind)
        context = self.authorization_context
        if policy.portfolio_bound and context is None:
            await self._reject_owned_without_context(payload)
        if (
            policy.portfolio_bound
            and context is not None
            and context.authorization_context_version == 0
        ):
            # Version 0 is retained only for historical terminal rows and
            # explicitly isolated development compatibility. New API
            # portfolio work must carry a current owner/actor snapshot; do not
            # enqueue unverifiable legacy-session work.
            raise EntitlementBindingConflictError()
        if context is not None:
            context.validate()
            self._validate_payload_context(context, payload)
            snapshot = durable_snapshot(context)
        else:
            snapshot = durable_snapshot(None)
            session_value = payload.get("portfolio_session_id") or payload.get("session_id")
            if session_value:
                try:
                    snapshot["portfolio_session_id"] = UUID(str(session_value))
                except (TypeError, ValueError) as exc:
                    raise EntitlementBindingConflictError() from exc
        return await self._repo.enqueue(
            job_kind=job_kind,
            payload=payload,
            priority=priority,
            max_attempts=max_attempts,
            idempotency_scope=scope,
            idempotency_key=key,
            portfolio_session_id=snapshot["portfolio_session_id"],
            owner_user_id=snapshot["owner_user_id"],
            actor_user_id=snapshot["actor_user_id"],
            authorization_context_version=snapshot["authorization_context_version"],
            entitlement_revision=snapshot["entitlement_revision"],
            execution_lane=MODEL_GENERATION_LANE if policy.consumes_model_credit else None,
        )

    async def _reject_owned_without_context(self, payload: dict[str, Any]) -> None:
        """Keep old trusted legacy fixtures working while fencing owned data."""

        recognized = False
        session_value = payload.get("portfolio_session_id") or payload.get("session_id")
        if session_value:
            recognized = True
            try:
                session_id = UUID(str(session_value))
            except ValueError as exc:
                raise EntitlementBindingConflictError() from exc
            result = await self._session.execute(
                select(PortfolioSession).where(PortfolioSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if (
                session is None
                or not session.legacy_quarantined
                or session.owner_user_id is not None
                or getattr(session, "session_mode", "legacy") not in {"detached", "legacy"}
                or session.status != "active"
            ):
                raise EntitlementBindingConflictError()
        run_value = payload.get("code_generator_run_id") or payload.get("development_run_id")
        if run_value:
            recognized = True
            try:
                run_id = UUID(str(run_value))
            except ValueError as exc:
                raise EntitlementBindingConflictError() from exc
            result = await self._session.execute(
                select(CodeGeneratorDevelopmentRun).where(CodeGeneratorDevelopmentRun.id == run_id)
            )
            run = result.scalar_one_or_none()
            if run is None or getattr(run, "run_mode", None) != "development":
                raise EntitlementBindingConflictError()
        if not recognized:
            raise EntitlementBindingConflictError()

    @staticmethod
    def _validate_payload_context(
        context: DurableAuthorizationContext, payload: dict[str, Any]
    ) -> None:
        if context.authorization_context_version != 1:
            return
        for key in ("portfolio_session_id", "session_id"):
            value = payload.get(key)
            if value in (None, ""):
                continue
            try:
                payload_session_id = UUID(str(value))
            except (TypeError, ValueError) as exc:
                raise EntitlementBindingConflictError() from exc
            if payload_session_id != context.portfolio_session_id:
                raise EntitlementBindingConflictError()

    async def get(self, job_id: UUID) -> Any:
        """Return a job by ID for status polling."""
        return await self._repo.get_by_id(job_id)

    async def find_idempotent(self, scope: str, key: str) -> Any:
        """Return an existing idempotent job, if one exists."""
        return await self._repo.find_idempotent(scope, key)
