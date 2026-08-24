"""SQLAlchemy models for the Phase 1 local identity boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from oryxenai.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AppUser(Base):
    """Database-authoritative mapping from a Supabase subject to OryxenAI."""

    __tablename__ = "app_users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    supabase_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, unique=True
    )
    primary_email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    username: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
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
        CheckConstraint(
            "primary_email = lower(primary_email)", name="ck_app_users_email_lowercase"
        ),
        CheckConstraint("role IN ('user', 'admin')", name="ck_app_users_role"),
        CheckConstraint(
            "status IN ('active', 'suspended', 'deletion_pending', 'deleted')",
            name="ck_app_users_status",
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
        ForeignKey("app_users.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    portfolio_session_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("portfolio_sessions.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
    )
    generation_run_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("code_generator_runs.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
    )
    successful_run_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("code_generator_runs.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
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
            "(consumed_at IS NOT NULL AND successful_run_id IS NOT NULL)",
            name="ck_portfolio_entitlements_consumed_consistency",
        ),
    )
