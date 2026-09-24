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
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.jobs.policy import policy_for


@dataclass(frozen=True, slots=True)
class AuthorizationFenceError(Exception):
    code: str = "AUTHORIZATION_FENCE_REJECTED"
    message: str = "This background operation is no longer authorized to continue."
    retryable: bool = False


class WorkerAuthorizationFence:
    """Re-check current ownership and account state before durable work."""

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
        if not policy_for(job.job_kind).portfolio_bound:
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

        portfolio = await self._one(PortfolioSession, job.portfolio_session_id)
        if (
            portfolio is None
            or portfolio.legacy_quarantined
            or portfolio.owner_user_id != job.owner_user_id
            or portfolio.status != "active"
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

        if owner.role == "user" and actor.id == owner.id:
            entitlement = await self._one(PortfolioEntitlement, owner.id, "user_id")
            if (
                entitlement is None
                or entitlement.portfolio_session_id != portfolio.id
                or (
                    job.entitlement_revision is not None
                    and entitlement.revision != job.entitlement_revision
                )
            ):
                raise AuthorizationFenceError()

        agent_run_id = _uuid_from_payload(payload, "agent_run_id")
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

    async def validate_payload(self, payload: dict[str, Any]) -> None:
        """Re-check the claimed job from the worker-only payload."""

        job_id = _uuid_from_payload(payload, "job_id")
        if job_id is None:
            return
        job = await self._one(BackgroundJob, job_id)
        attempt = _int_from_payload(payload, "attempt")
        if job is None or job.status != "running" or attempt is None:
            raise AuthorizationFenceError()
        lease_token = payload.get("lease_token")
        if job.lease_token is not None and not isinstance(lease_token, str):
            raise AuthorizationFenceError()
        await self.validate_job(
            job,
            expected_attempt=attempt,
            expected_lease_token=lease_token or None,
        )

    async def _validate_legacy_compatibility(self, job: BackgroundJob) -> None:
        """Permit only quarantined detached sessions without owner bindings."""

        payload = job.payload or {}
        session_id = _uuid_from_payload(payload, "portfolio_session_id")
        if session_id is None:
            session_id = _uuid_from_payload(payload, "session_id")
        if session_id is None:
            raise AuthorizationFenceError()
        portfolio = await self._one(PortfolioSession, session_id)
        if (
            portfolio is None
            or portfolio.status != "active"
            or not portfolio.legacy_quarantined
            or portfolio.owner_user_id is not None
            or getattr(portfolio, "session_mode", "legacy") not in {"detached", "legacy"}
        ):
            raise AuthorizationFenceError()

    async def _one(self, model: Any, identifier: UUID, field: str = "id") -> Any | None:
        column = getattr(model, field)
        result = await self._session.execute(select(model).where(column == identifier))
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
