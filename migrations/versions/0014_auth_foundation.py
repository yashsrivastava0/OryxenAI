"""Add the Phase 1 local identity and normal-user capacity foundation.

Revision ID: 0014_auth_foundation
Revises: 0013_codegen_stage_attempts
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_auth_foundation"
down_revision: str | None = "0013_codegen_stage_attempts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("supabase_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("primary_email", sa.Text(), nullable=False),
        sa.Column("username", sa.Text(), nullable=True),
        sa.Column("role", sa.Text(), nullable=False, server_default="user"),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("supabase_user_id", name="uq_app_users_supabase_user_id"),
        sa.UniqueConstraint("primary_email", name="uq_app_users_primary_email"),
        sa.UniqueConstraint("username", name="uq_app_users_username"),
        sa.CheckConstraint(
            "primary_email = lower(primary_email)",
            name="ck_app_users_email_lowercase",
        ),
        sa.CheckConstraint("role IN ('user', 'admin')", name="ck_app_users_role"),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'deletion_pending', 'deleted')",
            name="ck_app_users_status",
        ),
        sa.CheckConstraint(
            "username IS NULL OR username ~ '^[a-z0-9](?:[a-z0-9_-]{1,28})[a-z0-9]$'",
            name="ck_app_users_username_format",
        ),
        sa.CheckConstraint(
            "username IS NULL OR username NOT IN "
            "('admin', 'api', 'app', 'auth', 'health', 'preview', 'settings', "
            "'static', 'support', 'system')",
            name="ck_app_users_username_reserved",
        ),
        sa.CheckConstraint(
            "(username IS NULL AND onboarding_completed_at IS NULL) OR "
            "(username IS NOT NULL AND onboarding_completed_at IS NOT NULL)",
            name="ck_app_users_onboarding_consistency",
        ),
    )
    op.create_index("ix_app_users_role_status", "app_users", ["role", "status"])
    op.create_index("ix_app_users_email_status", "app_users", ["primary_email", "status"])

    op.create_table(
        "app_user_capacity",
        sa.Column("scope", sa.Text(), primary_key=True, nullable=False),
        sa.Column("normal_user_limit", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("scope = 'normal-users'", name="ck_capacity_scope"),
        sa.CheckConstraint(
            "normal_user_limit > 0 AND normal_user_limit <= 15",
            name="ck_capacity_limit",
        ),
        sa.CheckConstraint("revision >= 0", name="ck_capacity_revision"),
    )
    op.execute(
        "INSERT INTO app_user_capacity "
        "(scope, normal_user_limit, revision, created_at, updated_at) "
        "VALUES ('normal-users', 15, 0, now(), now())"
    )

    op.execute("ALTER TABLE app_users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app_user_capacity ENABLE ROW LEVEL SECURITY")
    # The FastAPI/SQLAlchemy service is the only Phase 1 business-data path.
    # Revoke browser roles when this is running against a Supabase/Postgres
    # cluster that has those roles; ordinary PostgreSQL installations do not.
    op.execute(
        """
        DO $$
        DECLARE role_name text;
        BEGIN
            FOR role_name IN
                SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')
            LOOP
                EXECUTE format(
                    'REVOKE ALL PRIVILEGES ON TABLE app_users, app_user_capacity FROM %I',
                    role_name
                );
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_app_users_email_status", table_name="app_users")
    op.drop_index("ix_app_users_role_status", table_name="app_users")
    op.drop_table("app_user_capacity")
    op.drop_table("app_users")
