"""Temporary handoffs survive aggregate deletion until artifact cleanup finishes."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from oryxenai.db.base import Base

PENDING = ("queued", "preparing", "validating")
TERMINAL = ("failed", "revoked", "expired")


class ReactHandoff(Base):
    __tablename__ = "react_handoffs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("app_users.id", ondelete="SET NULL"), nullable=True
    )
    portfolio_session_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("portfolio_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("portfolio_site_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    source_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    theme_id: Mapped[str] = mapped_column(Text, nullable=False)
    adapter_revision: Mapped[str] = mapped_column(Text, nullable=False, default="1")
    viewer_version: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_prefix: Mapped[str] = mapped_column(Text, nullable=False, default="")
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    receipt: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cleaned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','preparing','validating','ready','failed','revoked','expired')",
            name="ck_react_handoff_status",
        ),
        Index("ix_react_handoff_expiry", "status", "expires_at"),
        Index("ix_react_handoff_source", "source_version_id"),
        Index(
            "uq_react_handoff_pending",
            "portfolio_session_id",
            unique=True,
            postgresql_where=text("status IN ('queued','preparing','validating')"),
        ),
        Index(
            "uq_react_handoff_ready",
            "portfolio_session_id",
            unique=True,
            postgresql_where=text("status = 'ready'"),
        ),
    )
