"""SQLAlchemy models for the Phase 1 local identity boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from oryxenai.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AppUser(Base):
    """Database-authoritative mapping from a Supabase subject to OryxenAI."""

    __tablename__ = "app_users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    supabase_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    primary_email: Mapped[str] = mapped_column(Text, nullable=False)
    username: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="user")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        UniqueConstraint("supabase_user_id", name="uq_app_users_supabase_user_id"),
        UniqueConstraint("primary_email", name="uq_app_users_primary_email"),
        UniqueConstraint("username", name="uq_app_users_username"),
        CheckConstraint(
            "primary_email = lower(primary_email)", name="ck_app_users_email_lowercase"
        ),
        CheckConstraint("role IN ('user', 'admin')", name="ck_app_users_role"),
        CheckConstraint(
            "status IN ('active', 'suspended', 'deletion_pending', 'deleted')",
            name="ck_app_users_status",
        ),
        CheckConstraint(
            "status = 'deleted' OR supabase_user_id IS NOT NULL",
            name="ck_app_users_subject_required_unless_deleted",
        ),
        CheckConstraint(
            "username IS NULL OR username ~ '^[a-z0-9](?:[a-z0-9_-]{1,28})[a-z0-9]$'",
            name="ck_app_users_username_format",
        ),
        CheckConstraint(
            "username IS NULL OR username NOT IN "
            "('admin', 'api', 'app', 'auth', 'health', 'preview', 'settings', "
            "'static', 'support', 'system')",
            name="ck_app_users_username_reserved",
        ),
        CheckConstraint(
            "(username IS NULL AND onboarding_completed_at IS NULL) OR "
            "(username IS NOT NULL AND onboarding_completed_at IS NOT NULL)",
            name="ck_app_users_onboarding_consistency",
        ),
        Index("ix_app_users_role_status", "role", "status"),
        Index("ix_app_users_email_status", "primary_email", "status"),
    )


class AppUserCapacity(Base):
    """Singleton lock row for normal-user just-in-time admission."""

    __tablename__ = "app_user_capacity"

    scope: Mapped[str] = mapped_column(Text, primary_key=True)
    normal_user_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        CheckConstraint("scope = 'normal-users'", name="ck_capacity_scope"),
        CheckConstraint(
            "normal_user_limit > 0 AND normal_user_limit <= 15", name="ck_capacity_limit"
        ),
        CheckConstraint("revision >= 0", name="ck_capacity_revision"),
    )


class PortfolioEntitlement(Base):
    """The single normal-user portfolio/generation/success binding."""

    __tablename__ = "portfolio_entitlements"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("app_users.id", name="fk_portfolio_entitlements_user", ondelete="RESTRICT"),
        primary_key=True,
    )
    portfolio_session_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "portfolio_sessions.id",
            name="fk_portfolio_entitlements_session",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    generation_run_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "code_generator_runs.id",
            name="fk_portfolio_entitlements_generation",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    successful_run_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "code_generator_runs.id",
            name="fk_portfolio_entitlements_success",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    deleted_portfolio_session_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    project_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reset_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        UniqueConstraint("portfolio_session_id", name="uq_portfolio_entitlements_session"),
        UniqueConstraint("generation_run_id", name="uq_portfolio_entitlements_generation"),
        UniqueConstraint("successful_run_id", name="uq_portfolio_entitlements_success"),
        UniqueConstraint(
            "deleted_portfolio_session_id", name="uq_portfolio_entitlements_deleted_session"
        ),
        CheckConstraint("revision >= 0", name="ck_portfolio_entitlements_revision"),
        CheckConstraint(
            "generation_run_id IS NULL OR portfolio_session_id IS NOT NULL",
            name="ck_portfolio_entitlements_generation_requires_session",
        ),
        CheckConstraint(
            "successful_run_id IS NULL OR generation_run_id IS NOT NULL",
            name="ck_portfolio_entitlements_success_requires_generation",
        ),
        CheckConstraint(
            "successful_run_id IS NULL OR successful_run_id = generation_run_id",
            name="ck_portfolio_entitlements_success_matches_generation",
        ),
        CheckConstraint(
            "(consumed_at IS NULL AND successful_run_id IS NULL) OR "
            "(consumed_at IS NOT NULL AND successful_run_id IS NOT NULL) OR "
            "(consumed_at IS NOT NULL AND deleted_portfolio_session_id IS NOT NULL)",
            name="ck_portfolio_entitlements_consumed_consistency",
        ),
        CheckConstraint(
            "deleted_portfolio_session_id IS NULL OR "
            "(project_deleted_at IS NOT NULL AND portfolio_session_id IS NULL "
            "AND generation_run_id IS NULL AND successful_run_id IS NULL)",
            name="ck_portfolio_entitlements_deleted_project_consistency",
        ),
        CheckConstraint(
            "project_deleted_at IS NULL OR deleted_portfolio_session_id IS NOT NULL",
            name="ck_portfolio_entitlements_deleted_at_consistency",
        ),
        CheckConstraint("reset_count >= 0", name="ck_portfolio_entitlements_reset_count"),
        Index(
            "ix_portfolio_entitlements_deleted_project",
            "deleted_portfolio_session_id",
            "project_deleted_at",
        ),
    )


class AdminAuditEvent(Base):
    """Append-only safe administrator audit record."""

    __tablename__ = "admin_audit_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    operation_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    request_id: Mapped[str] = mapped_column(Text, nullable=False)
    safe_details: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint(
            "action IN ('suspend', 'restore', 'delete', 'readmit', 'reset_entitlement', "
            "'promote', 'demote', 'project_delete', 'legacy_project_delete', "
            "'code_generator_retry', 'code_generator_regenerate', 'operation_resume')",
            name="ck_admin_audit_action",
        ),
        CheckConstraint(
            "target_type IN ('user', 'identity', 'project', 'legacy_project', 'operation')",
            name="ck_admin_audit_target_type",
        ),
        CheckConstraint(
            "outcome IN ('requested', 'completed', 'retryable', 'failed')",
            name="ck_admin_audit_outcome",
        ),
        Index("ix_admin_audit_created_id", "created_at", "id"),
        Index("ix_admin_audit_target_created", "target_type", "target_id", "created_at", "id"),
        Index("ix_admin_audit_actor_created", "actor_user_id", "created_at", "id"),
    )


class AdminOperation(Base):
    """Resumable target-specific administrator operation."""

    __tablename__ = "admin_operations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="pending", server_default="pending"
    )
    step: Mapped[str] = mapped_column(
        Text, nullable=False, default="requested", server_default="requested"
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    safe_state: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    last_error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=text("now()"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "action IN ('suspend', 'restore', 'delete', 'readmit', 'reset_entitlement', "
            "'promote', 'demote', 'project_delete', 'legacy_project_delete', "
            "'code_generator_retry', 'code_generator_regenerate')",
            name="ck_admin_operations_action",
        ),
        CheckConstraint(
            "target_type IN ('user', 'identity', 'project', 'legacy_project')",
            name="ck_admin_operations_target_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'retryable_failure', 'rejected')",
            name="ck_admin_operations_status",
        ),
        CheckConstraint(
            "step IN ('requested', 'local_committed', 'provider_pending', 'cleanup_pending', "
            "'finalizing', 'completed')",
            name="ck_admin_operations_step",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_admin_operations_attempt_count"),
        UniqueConstraint(
            "actor_user_id",
            "action",
            "target_type",
            "target_id",
            "idempotency_key",
            name="uq_admin_operations_idempotency",
        ),
        Index("ix_admin_operations_status_updated", "status", "updated_at", "id"),
        Index("ix_admin_operations_actor_created", "actor_user_id", "created_at", "id"),
    )


class DeletedIdentityTombstone(Base):
    """Minimal record preventing deleted provider identities from re-entry."""

    __tablename__ = "deleted_identity_tombstones"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    former_app_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    supabase_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    primary_email: Mapped[str] = mapped_column(Text, nullable=False)
    former_role: Mapped[str] = mapped_column(Text, nullable=False)
    deleted_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=text("now()")
    )
    readmission_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    readmission_approved_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    __table_args__ = (
        CheckConstraint(
            "primary_email = lower(primary_email)", name="ck_deleted_identity_email_lowercase"
        ),
        CheckConstraint("former_role IN ('user', 'admin')", name="ck_deleted_identity_former_role"),
        CheckConstraint("revision >= 0", name="ck_deleted_identity_revision"),
        CheckConstraint(
            "(readmission_approved_at IS NULL AND readmission_approved_by IS NULL) OR "
            "(readmission_approved_at IS NOT NULL AND readmission_approved_by IS NOT NULL)",
            name="ck_deleted_identity_readmission_consistency",
        ),
        Index(
            "ux_deleted_identity_active_subject",
            "supabase_user_id",
            unique=True,
            postgresql_where=text("readmission_approved_at IS NULL"),
        ),
        Index(
            "ux_deleted_identity_active_email",
            "primary_email",
            unique=True,
            postgresql_where=text("readmission_approved_at IS NULL"),
        ),
        Index("ix_deleted_identity_deleted_at", "deleted_at", "id"),
    )


class DeletedPortfolioTombstone(Base):
    """Safe historical marker for one deleted portfolio aggregate."""

    __tablename__ = "deleted_portfolio_tombstones"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    original_session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    former_owner_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    legacy_quarantined: Mapped[bool] = mapped_column(nullable=False)
    had_promoted_success: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    deleted_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint("original_session_id", name="uq_deleted_portfolio_session"),
        CheckConstraint(
            "(legacy_quarantined = true AND former_owner_user_id IS NULL) OR "
            "(legacy_quarantined = false)",
            name="ck_deleted_portfolio_legacy_owner",
        ),
        Index("ix_deleted_portfolio_deleted_at", "deleted_at", "id"),
    )
