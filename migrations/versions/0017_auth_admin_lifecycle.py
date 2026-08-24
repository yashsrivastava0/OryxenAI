"""Add the Phase 4 administrator lifecycle and deletion ledger.

This revision deliberately stores only local identifiers and safe operational
metadata.  Provider identities, provider response bodies, portfolio content,
and object-store credentials never cross the database boundary.
"""

from __future__ import annotations

# The private-table names below are a fixed module constant; this is not
# user-controlled SQL construction.
# ruff: noqa: S608
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017_auth_admin_lifecycle"
down_revision: str | None = "0016_auth_entitlements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PRIVATE_TABLES = (
    "admin_audit_events",
    "admin_operations",
    "deleted_identity_tombstones",
    "deleted_portfolio_tombstones",
)


def _secure_private_tables() -> None:
    tables = ", ".join(repr(table) for table in _PRIVATE_TABLES)
    op.execute(
        f"""
        DO $$
        DECLARE table_name text;
        DECLARE role_name text;
        BEGIN
            FOREACH table_name IN ARRAY ARRAY[{tables}]
            LOOP
                EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
                FOR role_name IN
                    SELECT rolname FROM pg_roles
                    WHERE rolname IN ('anon', 'authenticated', 'service_role')
                LOOP
                    EXECUTE format(
                        'REVOKE ALL PRIVILEGES ON TABLE public.%I FROM %I',
                        table_name, role_name
                    );
                END LOOP;
            END LOOP;
        END $$;
        """
    )


def upgrade() -> None:
    # Deleted local identities retain their subject and email until the
    # tombstone is complete.  The nullable subject is therefore a deliberate
    # tombstone-only state, never a way to admit an incomplete active account.
    op.alter_column("app_users", "supabase_user_id", nullable=True)
    op.create_check_constraint(
        "ck_app_users_subject_required_unless_deleted",
        "app_users",
        "status = 'deleted' OR supabase_user_id IS NOT NULL",
    )

    op.add_column(
        "portfolio_sessions",
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_portfolio_sessions_lifecycle_status",
        "portfolio_sessions",
        "status IN ('active', 'deletion_pending', 'deleted')",
    )

    op.add_column(
        "portfolio_entitlements",
        sa.Column("deleted_portfolio_session_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "portfolio_entitlements",
        sa.Column("project_deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "portfolio_entitlements",
        sa.Column("reset_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "portfolio_entitlements",
        sa.Column("last_reset_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_portfolio_entitlements_deleted_session",
        "portfolio_entitlements",
        ["deleted_portfolio_session_id"],
    )
    op.drop_constraint(
        "ck_portfolio_entitlements_consumed_consistency",
        "portfolio_entitlements",
        type_="check",
    )
    op.create_check_constraint(
        "ck_portfolio_entitlements_consumed_consistency",
        "portfolio_entitlements",
        "(consumed_at IS NULL AND successful_run_id IS NULL) OR "
        "(consumed_at IS NOT NULL AND successful_run_id IS NOT NULL) OR "
        "(consumed_at IS NOT NULL AND deleted_portfolio_session_id IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_portfolio_entitlements_deleted_project_consistency",
        "portfolio_entitlements",
        "deleted_portfolio_session_id IS NULL OR "
        "(project_deleted_at IS NOT NULL AND portfolio_session_id IS NULL "
        "AND generation_run_id IS NULL AND successful_run_id IS NULL)",
    )
    op.create_check_constraint(
        "ck_portfolio_entitlements_deleted_at_consistency",
        "portfolio_entitlements",
        "project_deleted_at IS NULL OR deleted_portfolio_session_id IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_portfolio_entitlements_reset_count",
        "portfolio_entitlements",
        "reset_count >= 0",
    )
    op.create_index(
        "ix_portfolio_entitlements_deleted_project",
        "portfolio_entitlements",
        ["deleted_portfolio_session_id", "project_deleted_at"],
    )

    uuid = postgresql.UUID(as_uuid=True)
    timestamp = sa.DateTime(timezone=True)
    jsonb = postgresql.JSONB(astext_type=sa.Text())

    op.create_table(
        "admin_audit_events",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("actor_user_id", uuid, nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", uuid, nullable=True),
        sa.Column("operation_id", uuid, nullable=True),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("safe_details", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", timestamp, nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "action IN ('suspend', 'restore', 'delete', 'readmit', 'reset_entitlement', "
            "'promote', 'demote', 'project_delete', 'legacy_project_delete', "
            "'code_generator_retry', 'code_generator_regenerate', 'operation_resume')",
            name="ck_admin_audit_action",
        ),
        sa.CheckConstraint(
            "target_type IN ('user', 'identity', 'project', 'legacy_project', 'operation')",
            name="ck_admin_audit_target_type",
        ),
        sa.CheckConstraint(
            "outcome IN ('requested', 'completed', 'retryable', 'failed')",
            name="ck_admin_audit_outcome",
        ),
    )
    op.create_index(
        "ix_admin_audit_created_id",
        "admin_audit_events",
        ["created_at", "id"],
    )
    op.create_index(
        "ix_admin_audit_target_created",
        "admin_audit_events",
        ["target_type", "target_id", "created_at", "id"],
    )
    op.create_index(
        "ix_admin_audit_actor_created",
        "admin_audit_events",
        ["actor_user_id", "created_at", "id"],
    )

    op.create_table(
        "admin_operations",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("actor_user_id", uuid, nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", uuid, nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("request_fingerprint", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("step", sa.Text(), nullable=False, server_default="requested"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("safe_state", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_error_code", sa.Text(), nullable=True),
        sa.Column("created_at", timestamp, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", timestamp, nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", timestamp, nullable=True),
        sa.CheckConstraint(
            "action IN ('suspend', 'restore', 'delete', 'readmit', 'reset_entitlement', "
            "'promote', 'demote', 'project_delete', 'legacy_project_delete', "
            "'code_generator_retry', 'code_generator_regenerate')",
            name="ck_admin_operations_action",
        ),
        sa.CheckConstraint(
            "target_type IN ('user', 'identity', 'project', 'legacy_project')",
            name="ck_admin_operations_target_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'retryable_failure', 'rejected')",
            name="ck_admin_operations_status",
        ),
        sa.CheckConstraint(
            "step IN ('requested', 'local_committed', 'provider_pending', 'cleanup_pending', "
            "'finalizing', 'completed')",
            name="ck_admin_operations_step",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_admin_operations_attempt_count"),
        sa.UniqueConstraint(
            "actor_user_id",
            "action",
            "target_type",
            "target_id",
            "idempotency_key",
            name="uq_admin_operations_idempotency",
        ),
    )
    op.create_index(
        "ix_admin_operations_status_updated",
        "admin_operations",
        ["status", "updated_at", "id"],
    )
    op.create_index(
        "ix_admin_operations_actor_created",
        "admin_operations",
        ["actor_user_id", "created_at", "id"],
    )

    op.create_table(
        "deleted_identity_tombstones",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("former_app_user_id", uuid, nullable=False),
        sa.Column("supabase_user_id", uuid, nullable=False),
        sa.Column("primary_email", sa.Text(), nullable=False),
        sa.Column("former_role", sa.Text(), nullable=False),
        sa.Column("deleted_by", uuid, nullable=False),
        sa.Column("deleted_at", timestamp, nullable=False, server_default=sa.text("now()")),
        sa.Column("readmission_approved_at", timestamp, nullable=True),
        sa.Column("readmission_approved_by", uuid, nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint(
            "primary_email = lower(primary_email)", name="ck_deleted_identity_email_lowercase"
        ),
        sa.CheckConstraint(
            "former_role IN ('user', 'admin')", name="ck_deleted_identity_former_role"
        ),
        sa.CheckConstraint("revision >= 0", name="ck_deleted_identity_revision"),
        sa.CheckConstraint(
            "(readmission_approved_at IS NULL AND readmission_approved_by IS NULL) OR "
            "(readmission_approved_at IS NOT NULL AND readmission_approved_by IS NOT NULL)",
            name="ck_deleted_identity_readmission_consistency",
        ),
    )
    op.create_index(
        "ux_deleted_identity_active_subject",
        "deleted_identity_tombstones",
        ["supabase_user_id"],
        unique=True,
        postgresql_where=sa.text("readmission_approved_at IS NULL"),
    )
    op.create_index(
        "ux_deleted_identity_active_email",
        "deleted_identity_tombstones",
        ["primary_email"],
        unique=True,
        postgresql_where=sa.text("readmission_approved_at IS NULL"),
    )
    op.create_index(
        "ix_deleted_identity_deleted_at",
        "deleted_identity_tombstones",
        ["deleted_at", "id"],
    )

    op.create_table(
        "deleted_portfolio_tombstones",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("original_session_id", uuid, nullable=False),
        sa.Column("former_owner_user_id", uuid, nullable=True),
        sa.Column("legacy_quarantined", sa.Boolean(), nullable=False),
        sa.Column("had_promoted_success", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_by", uuid, nullable=False),
        sa.Column("deleted_at", timestamp, nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("original_session_id", name="uq_deleted_portfolio_session"),
        sa.CheckConstraint(
            "(legacy_quarantined = true AND former_owner_user_id IS NULL) OR "
            "(legacy_quarantined = false)",
            name="ck_deleted_portfolio_legacy_owner",
        ),
    )
    op.create_index(
        "ix_deleted_portfolio_deleted_at",
        "deleted_portfolio_tombstones",
        ["deleted_at", "id"],
    )

    _secure_private_tables()


def downgrade() -> None:
    for _table, name in (
        ("deleted_portfolio_tombstones", "ix_deleted_portfolio_deleted_at"),
        ("deleted_identity_tombstones", "ix_deleted_identity_deleted_at"),
        ("deleted_identity_tombstones", "ux_deleted_identity_active_email"),
        ("deleted_identity_tombstones", "ux_deleted_identity_active_subject"),
        ("admin_operations", "ix_admin_operations_actor_created"),
        ("admin_operations", "ix_admin_operations_status_updated"),
        ("admin_audit_events", "ix_admin_audit_actor_created"),
        ("admin_audit_events", "ix_admin_audit_target_created"),
        ("admin_audit_events", "ix_admin_audit_created_id"),
    ):
        op.execute(sa.text(f"DROP INDEX IF EXISTS public.{name}"))
    # The dedicated integration database may be reconstructed by its test
    # fixture while retaining Alembic's version row.  Keep downgrade
    # recoverable in that case; production migrations still create all four
    # tables deterministically on upgrade.
    for table in _PRIVATE_TABLES[::-1]:
        op.execute(sa.text(f"DROP TABLE IF EXISTS public.{table}"))
    op.execute(sa.text("DROP INDEX IF EXISTS public.ix_portfolio_entitlements_deleted_project"))
    for name in (
        "ck_portfolio_entitlements_reset_count",
        "ck_portfolio_entitlements_deleted_at_consistency",
        "ck_portfolio_entitlements_deleted_project_consistency",
        "ck_portfolio_entitlements_consumed_consistency",
    ):
        op.drop_constraint(name, "portfolio_entitlements", type_="check")
    op.create_check_constraint(
        "ck_portfolio_entitlements_consumed_consistency",
        "portfolio_entitlements",
        "(consumed_at IS NULL AND successful_run_id IS NULL) OR "
        "(consumed_at IS NOT NULL AND successful_run_id IS NOT NULL)",
    )
    op.drop_constraint(
        "uq_portfolio_entitlements_deleted_session", "portfolio_entitlements", type_="unique"
    )
    for column in (
        "last_reset_at",
        "reset_count",
        "project_deleted_at",
        "deleted_portfolio_session_id",
    ):
        op.drop_column("portfolio_entitlements", column)
    op.drop_constraint(
        "ck_portfolio_sessions_lifecycle_status", "portfolio_sessions", type_="check"
    )
    op.drop_column("portfolio_sessions", "deletion_requested_at")
    op.drop_constraint("ck_app_users_subject_required_unless_deleted", "app_users", type_="check")
    op.alter_column("app_users", "supabase_user_id", nullable=False)
