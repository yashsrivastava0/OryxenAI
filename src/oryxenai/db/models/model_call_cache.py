"""Durable cache rows for validated structured model-operation results."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from oryxenai.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ModelCallCache(Base):
    """An owner- or session-scoped validated model result.

    The row contains no raw prompt or source document.  ``output_payload`` is
    the already-validated structured result and is protected by the same
    ownership boundary as the originating portfolio session.
    """

    __tablename__ = "model_call_cache"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("app_users.id", name="fk_model_call_cache_owner", ondelete="CASCADE"),
        nullable=True,
    )
    portfolio_session_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "portfolio_sessions.id",
            name="fk_model_call_cache_session",
            ondelete="CASCADE",
        ),
        nullable=True,
    )
    agent_key: Mapped[str] = mapped_column(Text, nullable=False)
    operation: Mapped[str] = mapped_column(Text, nullable=False)
    cache_key: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    profile_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="producing", server_default="producing"
    )
    output_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    provider_metadata: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    lease_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=text("now()")
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    __table_args__ = (
        CheckConstraint(
            "(owner_user_id IS NOT NULL AND portfolio_session_id IS NULL) OR "
            "(owner_user_id IS NULL AND portfolio_session_id IS NOT NULL)",
            name="ck_model_call_cache_scope",
        ),
        CheckConstraint(
            "status IN ('producing', 'ready')",
            name="ck_model_call_cache_status",
        ),
        CheckConstraint(
            "hit_count >= 0",
            name="ck_model_call_cache_hit_count",
        ),
        Index(
            "ux_model_call_cache_owner_key",
            "owner_user_id",
            "cache_key",
            unique=True,
            postgresql_where=text("owner_user_id IS NOT NULL"),
        ),
        Index(
            "ux_model_call_cache_session_key",
            "portfolio_session_id",
            "cache_key",
            unique=True,
            postgresql_where=text("portfolio_session_id IS NOT NULL"),
        ),
        Index("ix_model_call_cache_expiry", "status", "expires_at"),
    )
