"""Database-authoritative authorization for portfolio aggregates."""

from __future__ import annotations

from dataclasses import dataclass

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
