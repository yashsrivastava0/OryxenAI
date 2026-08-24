"""PortfolioSession ORM model."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from oryxenai.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PortfolioSession(Base):
    """A test portfolio session — the aggregate root for agent runs."""

    __tablename__ = "portfolio_sessions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "app_users.id",
            name="fk_portfolio_sessions_owner_user_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    legacy_quarantined: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    session_mode: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="legacy",
        server_default="legacy",
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, default="Untitled session")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    deletion_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_state: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "(owner_user_id IS NOT NULL AND legacy_quarantined = false) OR "
            "(owner_user_id IS NULL AND legacy_quarantined = true)",
            name="ck_portfolio_sessions_owner_legacy_consistency",
        ),
        CheckConstraint(
            "(session_mode = 'owned' AND owner_user_id IS NOT NULL AND legacy_quarantined = false) OR "
            "(session_mode IN ('detached', 'legacy') AND owner_user_id IS NULL AND legacy_quarantined = true)",
            name="ck_portfolio_sessions_session_mode_consistency",
        ),
        CheckConstraint(
            "session_mode IN ('owned', 'detached', 'legacy')",
            name="ck_portfolio_sessions_session_mode",
        ),
        CheckConstraint(
            "status IN ('active', 'deletion_pending', 'deleted')",
            name="ck_portfolio_sessions_lifecycle_status",
        ),
        Index(
            "ix_portfolio_sessions_owner_created",
            "owner_user_id",
            "created_at",
        ),
    )
