"""BackgroundJob ORM model."""

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


class BackgroundJob(Base):
    """A durable row-backed job for the worker queue.

    At-least-once semantics. Idempotent handlers expected.
    """

    __tablename__ = "background_jobs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_kind: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    portfolio_session_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("portfolio_sessions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    owner_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=True
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=True
    )
    authorization_context_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    entitlement_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_lane: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    lease_token: Mapped[str | None] = mapped_column(Text, nullable=True)
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
        CheckConstraint(
            "authorization_context_version IN (0, 1)",
            name="ck_background_jobs_authorization_context_version",
        ),
        CheckConstraint(
            "authorization_context_version = 0 OR "
            "(portfolio_session_id IS NOT NULL AND owner_user_id IS NOT NULL AND actor_user_id IS NOT NULL)",
            name="ck_background_jobs_current_context_bindings",
        ),
        CheckConstraint(
            "entitlement_revision IS NULL OR entitlement_revision >= 0",
            name="ck_background_jobs_entitlement_revision",
        ),
        CheckConstraint(
            "execution_lane IS NULL OR execution_lane IN ('model-generation')",
            name="ck_background_jobs_execution_lane",
        ),
        Index("ix_bgjobs_authorization", "portfolio_session_id", "owner_user_id", "actor_user_id"),
        Index(
            "ux_bgjobs_running_execution_lane",
            "execution_lane",
            unique=True,
            postgresql_where=text("status = 'running' AND execution_lane IS NOT NULL"),
        ),
    )
