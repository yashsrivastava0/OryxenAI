"""AgentRun ORM model."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Double, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from oryxenai.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AgentRun(Base):
    """An append-oriented record of a single agent execution.

    Successful runs are immutable — their original input/output are never
    updated after completion. Failed runs carry a safe structured error.
    """

    __tablename__ = "agent_runs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("portfolio_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_key: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    input_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    output_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    state_before: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    state_after: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    model_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    error_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    finish_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Double, nullable=True)
    usage: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Session run history (most recent first).
        Index("ix_agent_runs_session_created", "portfolio_session_id", "created_at"),
        # Agent run history across all sessions.
        Index("ix_agent_runs_agent_created", "agent_key", "created_at"),
        # Run status lookups.
        Index("ix_agent_runs_status", "status"),
        # Idempotency: prevent duplicate mock execution for the same
        # session + agent + idempotency key. Partial index — only when key
        # is present.
        Index(
            "ux_agent_runs_idempotency",
            "portfolio_session_id",
            "agent_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )
