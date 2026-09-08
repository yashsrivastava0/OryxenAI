"""Durable, provider-neutral model usage and quota records."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from oryxenai.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ModelOperation(Base):
    """One logical operation, independent from individual transmissions."""

    __tablename__ = "model_operations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    operation_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    owner_id_hash: Mapped[str] = mapped_column(Text, nullable=False, default="")
    session_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    run_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    job_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    agent: Mapped[str] = mapped_column(Text, nullable=False, default="")
    stage: Mapped[str] = mapped_column(Text, nullable=False, default="")
    operation: Mapped[str] = mapped_column(Text, nullable=False)
    routing_policy_version: Mapped[str] = mapped_column(Text, nullable=False, default="")
    input_classification: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="running")
    normal_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    recovery_allowance: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    normal_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recovery_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_fingerprint: Mapped[str] = mapped_column(Text, nullable=False, default="")
    accepted_result_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    accepted_attempt_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    policy_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class ModelCallAttempt(Base):
    """One application-level provider transmission, successful or failed."""

    __tablename__ = "model_call_attempts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    operation_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    profile_name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    credential_alias: Mapped[str] = mapped_column(Text, nullable=False, default="")
    capacity_source_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    quota_group: Mapped[str] = mapped_column(Text, nullable=False, default="")
    agent: Mapped[str] = mapped_column(Text, nullable=False, default="")
    stage: Mapped[str] = mapped_column(Text, nullable=False, default="")
    operation: Mapped[str] = mapped_column(Text, nullable=False)
    job_attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fallback_attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt_kind: Mapped[str] = mapped_column(Text, nullable=False, default="normal")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="reserved")
    error_class: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_request_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    gateway_attempt_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cache_write_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reasoning_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_cost_micro_usd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_micro_usd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    promotional_micro_usd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rate_limit_seconds: Mapped[float | None] = mapped_column(nullable=True)
    details: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_model_call_attempts_created", "started_at"),
        Index("ix_model_call_attempts_attribution", "provider", "model", "agent", "operation"),
        Index("ix_model_call_attempts_alias", "credential_alias", "started_at"),
    )


class ModelBudgetReservation(Base):
    """Durable request/token reservation used for quota admission."""

    __tablename__ = "model_budget_reservations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    attempt_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    capacity_source_id: Mapped[str] = mapped_column(Text, nullable=False)
    quota_group: Mapped[str] = mapped_column(Text, nullable=False, default="")
    window_kind: Mapped[str] = mapped_column(Text, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requests_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    input_tokens_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="reserved")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_model_budget_reservations_window", "capacity_source_id", "window_end"),
    )


class ModelCapacityWindow(Base):
    """Observed provider capacity and local reservations for one window."""

    __tablename__ = "model_capacity_windows"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    capacity_source_id: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    quota_group: Mapped[str] = mapped_column(Text, nullable=False, default="")
    window_kind: Mapped[str] = mapped_column(Text, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_token_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_request_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observed_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    observed_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "capacity_source_id",
            "model",
            "window_kind",
            "window_start",
            name="ux_model_capacity_window_key",
        ),
    )


class ModelProviderObservation(Base):
    """Provider usage/limit observation cursor and redacted payload."""

    __tablename__ = "model_provider_observations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    capacity_source_id: Mapped[str] = mapped_column(Text, nullable=False)
    observation_kind: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        Index(
            "ix_model_provider_observations_source", "provider", "capacity_source_id", "observed_at"
        ),
    )
