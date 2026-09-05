"""Add durable scoped cache for validated structured model calls."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021_model_call_cache"
down_revision: str | None = "0020_codegen_export_receipt"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_call_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app_users.id", name="fk_model_call_cache_owner", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "portfolio_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "portfolio_sessions.id",
                name="fk_model_call_cache_session",
                ondelete="CASCADE",
            ),
            nullable=True,
        ),
        sa.Column("agent_key", sa.Text(), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("cache_key", sa.Text(), nullable=False),
        sa.Column("prompt_fingerprint", sa.Text(), nullable=False),
        sa.Column("input_fingerprint", sa.Text(), nullable=False),
        sa.Column("profile_fingerprint", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="producing"),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "provider_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("lease_token", sa.Text(), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint(
            "(owner_user_id IS NOT NULL AND portfolio_session_id IS NULL) OR "
            "(owner_user_id IS NULL AND portfolio_session_id IS NOT NULL)",
            name="ck_model_call_cache_scope",
        ),
        sa.CheckConstraint(
            "status IN ('producing', 'ready')",
            name="ck_model_call_cache_status",
        ),
        sa.CheckConstraint("hit_count >= 0", name="ck_model_call_cache_hit_count"),
    )
    op.create_index(
        "ux_model_call_cache_owner_key",
        "model_call_cache",
        ["owner_user_id", "cache_key"],
        unique=True,
        postgresql_where=sa.text("owner_user_id IS NOT NULL"),
    )
    op.create_index(
        "ux_model_call_cache_session_key",
        "model_call_cache",
        ["portfolio_session_id", "cache_key"],
        unique=True,
        postgresql_where=sa.text("portfolio_session_id IS NOT NULL"),
    )
    op.create_index(
        "ix_model_call_cache_expiry",
        "model_call_cache",
        ["status", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_model_call_cache_expiry", table_name="model_call_cache")
    op.drop_index("ux_model_call_cache_session_key", table_name="model_call_cache")
    op.drop_index("ux_model_call_cache_owner_key", table_name="model_call_cache")
    op.drop_table("model_call_cache")
