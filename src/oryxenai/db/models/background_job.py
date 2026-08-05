"""BackgroundJob ORM model."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from oryxenai.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class BackgroundJob(Base):
    """A durable row-backed job for the worker queue.

    At-least-once semantics. Idempotent handlers expected.
    """

    __tablename__ = "background_jobs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_kind: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    error_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    locked_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Due queued jobs — primary claim query.
        Index(
            "ix_bgjobs_claim",
            "status",
            "available_at",
            "priority",
            "created_at",
            postgresql_where=text("status = 'queued'"),
        ),
        # Running stale jobs — recovery query.
        Index(
            "ix_bgjobs_stale",
            "status",
            "heartbeat_at",
            postgresql_where=text("status = 'running'"),
        ),
        Index("ix_bgjobs_kind_created", "job_kind", "created_at"),
        Index("ix_bgjobs_status", "status"),
        # Idempotency: unique when both scope and key are present.
        Index(
            "ux_bgjobs_idempotency",
            "idempotency_scope",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_scope IS NOT NULL AND idempotency_key IS NOT NULL"),
        ),
    )
