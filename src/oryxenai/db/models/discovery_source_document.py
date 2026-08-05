"""Immutable source snapshots used by Discovery model runs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from oryxenai.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class DiscoverySourceDocument(Base):
    """One immutable source representation for a Discovery revision.

    The original text is kept here so worker jobs can load a stable input
    without putting sensitive content in a background-job payload.
    """

    __tablename__ = "discovery_source_documents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("portfolio_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_kind: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(Text, nullable=False, default="en")
    source_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_discovery_source_session_created", "portfolio_session_id", "created_at"),
        Index("ix_discovery_source_kind", "source_kind"),
        Index(
            "ux_discovery_source_current",
            "portfolio_session_id",
            "source_kind",
            unique=True,
            postgresql_where=superseded_at.is_(None),
        ),
    )
