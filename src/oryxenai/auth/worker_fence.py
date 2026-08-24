"""Provider-neutral authorization fence for durable worker execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.auth.models import AppUser, PortfolioEntitlement
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.models.background_job import BackgroundJob
from oryxenai.db.models.code_generator_development import CodeGeneratorDevelopmentRun
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.jobs.policy import policy_for


@dataclass(frozen=True, slots=True)
class AuthorizationFenceError(Exception):
    code: str = "AUTHORIZATION_FENCE_REJECTED"
    message: str = "This background operation is no longer authorized to continue."
    retryable: bool = False


class WorkerAuthorizationFence:
    """Re-check durable local authorization immediately before handler work."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def validate_job(
        self,
        job: BackgroundJob,
        *,
        expected_attempt: int | None = None,
        expected_lease_token: str | None = None,
    ) -> None:
        if job.status not in {None, "running"}:
            raise AuthorizationFenceError()
        if expected_attempt is not None and job.attempt != expected_attempt:
            raise AuthorizationFenceError()
        if expected_lease_token is not None and job.lease_token != expected_lease_token:
            raise AuthorizationFenceError()
        policy = policy_for(job.job_kind)
        if not policy.portfolio_bound:
            return
        if job.authorization_context_version == 0:
            await self._validate_legacy_compatibility(job)
            return
        if job.authorization_context_version != 1:
            raise AuthorizationFenceError()
        if (
            job.portfolio_session_id is None
            or job.owner_user_id is None
            or job.actor_user_id is None
        ):
            raise AuthorizationFenceError()

        session = await self._one(PortfolioSession, job.portfolio_session_id)
        if (
            session is None
            or session.legacy_quarantined
            or session.owner_user_id != job.owner_user_id
            or session.status in {"deletion_pending", "deleted"}
        ):
            raise AuthorizationFenceError()
        owner = await self._one(AppUser, job.owner_user_id)
        actor = await self._one(AppUser, job.actor_user_id)
        if owner is None or actor is None or owner.status != "active" or actor.status != "active":
            raise AuthorizationFenceError()
        if job.actor_user_id != job.owner_user_id and actor.role != "admin":
            raise AuthorizationFenceError()

        payload = job.payload or {}
        payload_session_id = _uuid_from_payload(payload, "portfolio_session_id")
        if payload_session_id is None:
            payload_session_id = _uuid_from_payload(payload, "session_id")
        if payload_session_id is not None and payload_session_id != job.portfolio_session_id:
            raise AuthorizationFenceError()
        agent_run_id = _uuid_from_payload(payload, "agent_run_id")
        codegen_id = _uuid_from_payload(payload, "code_generator_run_id")
        if codegen_id is None:
            codegen_id = _uuid_from_payload(payload, "development_run_id")

        codegen_run = None
        if codegen_id is not None:
            codegen_run = await self._one(CodeGeneratorDevelopmentRun, codegen_id)
            if codegen_run is None:
                raise AuthorizationFenceError()

        # A normal user's successful entitlement freezes every portfolio
        # mutation, not only Code Generator rows.  The exact verification
        # job for the exact successful run is the one crash-recovery exception:
        # it may finish the already-promoted receipt without creating work.
        # Administrators bypass this entitlement cell while retaining the
        # owner/actor and workflow checks above.
        is_exact_verification_job = (
            job.job_kind == "code_generator.verify_and_preview" and codegen_id is not None
        )
        is_finalized_success_replay = (
            is_exact_verification_job
            and codegen_run is not None
            and str(codegen_run.run_mode) == "session"
            and codegen_run.portfolio_session_id == job.portfolio_session_id
            and codegen_run.owner_user_id == job.owner_user_id
            and codegen_run.actor_user_id == job.actor_user_id
            and codegen_run.authorization_context_version == 1
            and str(codegen_run.status) == "ready"
            and isinstance(codegen_run.active_preview, dict)
        )
        if owner.role == "user" and actor.id == owner.id:
            entitlement_result = await self._session.execute(
                select(PortfolioEntitlement).where(PortfolioEntitlement.user_id == owner.id)
            )
            entitlement = entitlement_result.scalar_one_or_none()
            if entitlement is None or (
                entitlement.successful_run_id is not None
                and (not is_finalized_success_replay or entitlement.successful_run_id != codegen_id)
            ):
                raise AuthorizationFenceError()

        if agent_run_id is not None:
            run = await self._one(AgentRun, agent_run_id)
            if (
                run is None
                or run.portfolio_session_id != job.portfolio_session_id
                or run.owner_user_id != job.owner_user_id
                or run.actor_user_id != job.actor_user_id
                or run.authorization_context_version != 1
            ):
                raise AuthorizationFenceError()

        if codegen_id is not None:
            run = codegen_run
            if run is None:
                raise AuthorizationFenceError()
            if str(run.run_mode) != "session":
                # Development runs are admin-only and should not carry a
                # current portfolio context, so a v1 context is invalid.
                raise AuthorizationFenceError()
            if (
                run.portfolio_session_id != job.portfolio_session_id
                or run.owner_user_id != job.owner_user_id
                or run.actor_user_id != job.actor_user_id
                or run.authorization_context_version != 1
                or run.entitlement_revision != job.entitlement_revision
            ):
                raise AuthorizationFenceError()
            if owner.role == "user" and actor.id == owner.id:
                await self._validate_entitlement(
                    owner.id,
                    job.portfolio_session_id,
                    run.id,
                    job.entitlement_revision,
                    allow_success=is_finalized_success_replay,
                )
        elif job.entitlement_revision is not None:
            raise AuthorizationFenceError()

    async def validate_run(self, run_id: UUID) -> None:
        run = await self._one(CodeGeneratorDevelopmentRun, run_id)
        if run is None:
            raise AuthorizationFenceError()
        if run.authorization_context_version == 0:
            if str(run.run_mode) == "development":
                return
            raise AuthorizationFenceError()
        job = BackgroundJob(
            job_kind="code_generator.verify_and_preview",
            status="running",
            payload={"code_generator_run_id": str(run.id)},
            portfolio_session_id=run.portfolio_session_id,
            owner_user_id=run.owner_user_id,
            actor_user_id=run.actor_user_id,
            authorization_context_version=run.authorization_context_version,
            entitlement_revision=run.entitlement_revision,
        )
        await self.validate_job(job)

    async def validate_payload(self, payload: dict[str, Any]) -> None:
        """Re-check the claimed job from a handler's worker-only payload."""

        job_id = _uuid_from_payload(payload, "job_id")
        if job_id is None:
            # Direct legacy handler fixtures do not carry the worker lease
            # fields. The outer worker fence still protects real execution.
            return
        job = await self._one(BackgroundJob, job_id)
        if job is None:
            raise AuthorizationFenceError()
        attempt = _int_from_payload(payload, "attempt")
        if job.status != "running" or attempt is None:
            raise AuthorizationFenceError()
        lease_token = payload.get("lease_token")
        if job.lease_token is not None and not isinstance(lease_token, str):
            raise AuthorizationFenceError()
        if job.lease_token is not None and lease_token != job.lease_token:
            raise AuthorizationFenceError()
        await self.validate_job(
            job,
            expected_attempt=attempt,
            expected_lease_token=lease_token or None,
        )

    async def _validate_entitlement(
        self,
        user_id: UUID,
        session_id: UUID,
        run_id: UUID,
        revision: int | None,
        *,
        allow_success: bool = False,
    ) -> None:
        if revision is None:
            raise AuthorizationFenceError()
        result = await self._session.execute(
            select(PortfolioEntitlement).where(PortfolioEntitlement.user_id == user_id)
        )
        entitlement = result.scalar_one_or_none()
        revision_matches = entitlement is not None and entitlement.revision == revision
        if (
            not revision_matches
            and allow_success
            and entitlement is not None
            and entitlement.successful_run_id == run_id
        ):
            # Finalization increments the entitlement revision after the
            # verified pointer is durable. Crash recovery may reconcile the
            # exact verification job once against that post-success revision.
            revision_matches = entitlement.revision == revision + 1
        if (
            entitlement is None
            or entitlement.portfolio_session_id != session_id
            or entitlement.generation_run_id != run_id
            or not revision_matches
            or (
                entitlement.successful_run_id is not None
                and not (allow_success and entitlement.successful_run_id == run_id)
            )
        ):
            raise AuthorizationFenceError()

    async def _validate_legacy_compatibility(self, job: BackgroundJob) -> None:
        """Permit only quarantined legacy fixtures; owned legacy work fails closed."""

        session_id = _uuid_from_payload(job.payload or {}, "portfolio_session_id")
        if session_id is None:
            session_id = _uuid_from_payload(job.payload or {}, "session_id")
        if session_id is None:
            run_id = _uuid_from_payload(job.payload or {}, "development_run_id")
            if run_id is None:
                run_id = _uuid_from_payload(job.payload or {}, "code_generator_run_id")
            if run_id is not None:
                run = await self._one(CodeGeneratorDevelopmentRun, run_id)
                if run is not None and str(run.run_mode) == "development":
                    return
            raise AuthorizationFenceError()
        session = await self._one(PortfolioSession, session_id)
        if (
            session is None
            or session.status in {"deletion_pending", "deleted"}
            or not session.legacy_quarantined
            or session.owner_user_id is not None
            or getattr(session, "session_mode", "legacy") not in {"detached", "legacy"}
        ):
            raise AuthorizationFenceError()

    async def _one(self, model: Any, identifier: UUID) -> Any | None:
        result = await self._session.execute(select(model).where(model.id == identifier))
        return result.scalar_one_or_none()


def _uuid_from_payload(payload: dict[str, Any], key: str) -> UUID | None:
    value = payload.get(key)
    if value is None or value == "":
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        raise AuthorizationFenceError() from None


def _int_from_payload(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise AuthorizationFenceError() from None
