"""Database-authoritative authorization for portfolio aggregates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from oryxenai.auth.domain import AuthRole, CurrentUser
from oryxenai.db.models.portfolio_session import PortfolioSession


@dataclass(frozen=True, slots=True)
class PortfolioAccess:
    """The authorized aggregate and the actor who may operate on it.

    The object is deliberately produced by a FastAPI dependency after a
    current-token verification and a database owner/admin lookup.  Handlers
    must use ``session.id`` from this object instead of reparsing a caller
    supplied identifier or trusting a client-provided owner field.
    """

    actor: CurrentUser
    session: PortfolioSession

    @property
    def is_admin(self) -> bool:
        return self.actor.role is AuthRole.ADMIN


@dataclass(frozen=True, slots=True)
class DurableAuthorizationContext:
    """Only local, durable authorization facts permitted on a job/run row."""

    portfolio_session_id: UUID | None
    owner_user_id: UUID | None
    actor_user_id: UUID | None
    authorization_context_version: int = 1
    entitlement_revision: int | None = None
    actor_is_admin: bool = False

    def validate(self) -> None:
        if self.authorization_context_version not in {0, 1}:
            raise ValueError("unsupported authorization context version")
        if self.authorization_context_version == 1 and (
            self.portfolio_session_id is None
            or self.owner_user_id is None
            or self.actor_user_id is None
        ):
            raise ValueError("current authorization contexts require local identity bindings")
        if self.authorization_context_version == 0 and any(
            value is not None
            for value in (
                self.portfolio_session_id,
                self.owner_user_id,
                self.actor_user_id,
                self.entitlement_revision,
            )
        ):
            raise ValueError("legacy authorization contexts cannot carry portfolio bindings")
        if self.entitlement_revision is not None and self.entitlement_revision < 0:
            raise ValueError("entitlement revision must not be negative")

    @classmethod
    def from_access(
        cls,
        access: PortfolioAccess,
        *,
        entitlement_revision: int | None = None,
    ) -> DurableAuthorizationContext:
        session = access.session
        if session.owner_user_id is None or session.legacy_quarantined:
            return cls(None, None, None, authorization_context_version=0)
        context = cls(
            portfolio_session_id=session.id,
            owner_user_id=session.owner_user_id,
            actor_user_id=access.actor.id,
            authorization_context_version=1,
            entitlement_revision=entitlement_revision,
            actor_is_admin=access.actor.role is AuthRole.ADMIN,
        )
        context.validate()
        return context


class DurableSnapshot(TypedDict):
    portfolio_session_id: UUID | None
    owner_user_id: UUID | None
    actor_user_id: UUID | None
    authorization_context_version: int
    entitlement_revision: int | None


def durable_snapshot(
    context: DurableAuthorizationContext | None,
) -> DurableSnapshot:
    """Return ORM-ready snapshot values without copying request/JWT data."""

    if context is None:
        return {
            "portfolio_session_id": None,
            "owner_user_id": None,
            "actor_user_id": None,
            "authorization_context_version": 0,
            "entitlement_revision": None,
        }
    context.validate()
    return {
        "portfolio_session_id": context.portfolio_session_id,
        "owner_user_id": context.owner_user_id,
        "actor_user_id": context.actor_user_id,
        "authorization_context_version": context.authorization_context_version,
        "entitlement_revision": context.entitlement_revision,
    }


def durable_snapshot_for_session(
    context: DurableAuthorizationContext | None,
    session_id: UUID,
) -> DurableSnapshot:
    """Return a durable snapshot carrying the row's session binding.

    The pre-authenticated development and legacy service paths do not have a
    request authorization context, but their run rows still retain the
    portfolio-session foreign key.  Current authenticated contexts must
    already identify that same session; silently rebinding them would weaken
    the worker fence.
    """

    snapshot = durable_snapshot(context)
    bound_session_id = snapshot["portfolio_session_id"]
    if bound_session_id is not None and bound_session_id != session_id:
        raise ValueError("authorization context does not match portfolio session")
    snapshot["portfolio_session_id"] = session_id
    return snapshot
