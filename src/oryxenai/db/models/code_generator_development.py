"""Durable persistence for production and development Code Generator runs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from oryxenai.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class CodeGeneratorRun(Base):
    """One optimistic-concurrency Code Generator attempt.

    ``run_mode=session`` binds an attempt to the portfolio aggregate.  The
    development routes use the same engine with ``run_mode=development`` so
    fixtures and uploads continue to exercise production behavior.
    """

    __tablename__ = "code_generator_runs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="created")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    run_mode: Mapped[str] = mapped_column(
        Text, nullable=False, default="development", server_default="development"
    )
    portfolio_session_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("portfolio_sessions.id", ondelete="CASCADE"),
        nullable=True,
    )
    auto_advance: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    coordinator_stage: Mapped[str] = mapped_column(
        Text, nullable=False, default="plan", server_default="plan"
    )
    input_reference: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    input_receipt: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    context_receipt: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    planner_receipt: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    plan: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    plan_summary: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    issues: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False, default=list)
    admitted_identity: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_pack_receipt: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    build_preparation_source_ref: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    artifact_reference: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    artifact_receipt: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    preflight_receipt: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    creative_direction: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    integration_review: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    pipeline_contract_version: Mapped[str] = mapped_column(
        Text, nullable=False, default="code-generator-v3", server_default="code-generator-v3"
    )
    trace_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    active_attempt_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    background_job_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    acquire_job_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    generation_job_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    resource_ledger: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    dependency_ledger: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    acquire_receipt: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    acquire_summary: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    plan_delta_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    generation_projection: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    source_checkpoint: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    source_summary: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    verification_job_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    verification_projection: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    candidate_artifact: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    pending_promotion: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    active_preview: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    terminal_failure: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    preview_host: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_scope: Mapped[str] = mapped_column(
        Text, nullable=False, default="development", server_default="development"
    )
    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        Index("ix_codegen_runs_status_created", "status", "created_at"),
        Index("ix_codegen_runs_session_created", "portfolio_session_id", "created_at"),
        Index("ix_codegen_runs_active_attempt", "active_attempt_id"),
        Index(
            "ux_codegen_runs_idempotency",
            "idempotency_scope",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )


class CodeGeneratorStageAttempt(Base):
    """Normalized fencing record for one durable Code Generator stage.

    Run JSON remains a projection for the developer/session APIs, while this
    row is the authoritative caller token for finalization.  A late worker
    therefore cannot win merely because it holds an older run revision.
    """

    __tablename__ = "code_generator_stage_attempts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("code_generator_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    stage: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    job_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    expected_run_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    worker_instance: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_references: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    safe_error: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        UniqueConstraint("run_id", "stage", "attempt_no", name="ux_codegen_stage_attempt_no"),
        Index("ix_codegen_stage_attempts_run_stage", "run_id", "stage", "attempt_no"),
        Index(
            "ux_codegen_stage_attempts_active",
            "run_id",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running', 'retrying')"),
        ),
    )


class CodeGeneratorEvent(Base):
    """Append-only safe event stream for a Code Generator run."""

    __tablename__ = "code_generator_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("code_generator_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("code_generator_stage_attempts.id", ondelete="SET NULL"),
        nullable=True,
    )
    pipeline_contract_version: Mapped[str] = mapped_column(
        Text, nullable=False, default="code-generator-v3", server_default="code-generator-v3"
    )
    trace_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(Text, nullable=False, default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="ux_codegen_event_sequence"),
        Index("ix_codegen_events_run_sequence", "run_id", "sequence"),
        Index("ix_codegen_events_attempt", "attempt_id"),
    )


# Import compatibility for the standalone development API.  Runtime code is
# migrated incrementally without creating a second ORM mapping or table.
CodeGeneratorDevelopmentRun = CodeGeneratorRun
CodeGeneratorDevelopmentEvent = CodeGeneratorEvent
