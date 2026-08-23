"""Add the Phase 2 portfolio ownership boundary and harden table access.

Revision ID: 0015_portfolio_ownership
Revises: 0014_auth_foundation
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# The migration iterates a closed, checked-in table-name set and uses
# PostgreSQL format(%I) for every identifier; Ruff cannot infer that boundary.
# ruff: noqa: S608

revision: str = "0015_portfolio_ownership"
down_revision: str | None = "0014_auth_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BUSINESS_TABLES = (
    "portfolio_sessions",
    "agent_runs",
    "background_jobs",
    "service_heartbeats",
    "app_users",
    "app_user_capacity",
    "code_generator_runs",
    "code_generator_events",
    "code_generator_stage_attempts",
)
_PHASE1_RLS_TABLES = ("app_users", "app_user_capacity")


def _set_business_table_rls(enabled: bool, tables: tuple[str, ...] = _BUSINESS_TABLES) -> None:
    action = "ENABLE" if enabled else "DISABLE"
    op.execute(
        f"""
        DO $$
        DECLARE table_name text;
        BEGIN
            FOREACH table_name IN ARRAY ARRAY[
                {", ".join(repr(table) for table in tables)}
            ]
            LOOP
                IF to_regclass('public.' || table_name) IS NOT NULL THEN
                    EXECUTE format(
                        'ALTER TABLE public.%I {action} ROW LEVEL SECURITY',
                        table_name
                    );
                END IF;
            END LOOP;
        END $$;
        """
    )


def _revoke_business_table_privileges() -> None:
    op.execute(
        f"""
        DO $$
        DECLARE table_name text;
        DECLARE role_name text;
        BEGIN
            FOREACH table_name IN ARRAY ARRAY[
                {", ".join(repr(table) for table in _BUSINESS_TABLES)}
            ]
            LOOP
                IF to_regclass('public.' || table_name) IS NOT NULL THEN
                    FOR role_name IN
                        SELECT rolname
                        FROM pg_roles
                        WHERE rolname IN ('anon', 'authenticated', 'service_role')
                    LOOP
                        EXECUTE format(
                            'REVOKE ALL PRIVILEGES ON TABLE public.%I FROM %I',
                            table_name,
                            role_name
                        );
                    END LOOP;
                END IF;
            END LOOP;
        END $$;
        """
    )


def _revoke_default_privileges() -> None:
    # Supabase role names are not present on ordinary local PostgreSQL.  Keep
    # the migration portable by issuing each default-privilege statement only
    # when its target role exists.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM anon;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM authenticated;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM authenticated;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM authenticated;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
                ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM service_role;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM service_role;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM service_role;
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    op.add_column(
        "portfolio_sessions",
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "portfolio_sessions",
        sa.Column(
            "legacy_quarantined",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    # Existing rows are deliberately quarantined.  No legacy record receives
    # an inferred owner from email, name, JSONB, or any other mutable field.
    op.execute("UPDATE portfolio_sessions SET owner_user_id = NULL, legacy_quarantined = TRUE")
    op.create_foreign_key(
        "fk_portfolio_sessions_owner_user_id",
        "portfolio_sessions",
        "app_users",
        ["owner_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_portfolio_sessions_owner_legacy_consistency",
        "portfolio_sessions",
        "(owner_user_id IS NOT NULL AND legacy_quarantined = false) OR "
        "(owner_user_id IS NULL AND legacy_quarantined = true)",
    )
    op.create_index(
        "ix_portfolio_sessions_owner_created",
        "portfolio_sessions",
        ["owner_user_id", "created_at"],
    )

    _set_business_table_rls(True)
    _revoke_business_table_privileges()
    _revoke_default_privileges()


def downgrade() -> None:
    # 0014 already enables RLS on the two auth tables.  Leave that protection
    # intact while restoring the pre-Phase-2 session schema.
    _set_business_table_rls(
        False,
        tables=tuple(table for table in _BUSINESS_TABLES if table not in _PHASE1_RLS_TABLES),
    )
    op.drop_index("ix_portfolio_sessions_owner_created", table_name="portfolio_sessions")
    op.drop_constraint(
        "ck_portfolio_sessions_owner_legacy_consistency",
        "portfolio_sessions",
        type_="check",
    )
    op.drop_constraint(
        "fk_portfolio_sessions_owner_user_id",
        "portfolio_sessions",
        type_="foreignkey",
    )
    op.drop_column("portfolio_sessions", "legacy_quarantined")
    op.drop_column("portfolio_sessions", "owner_user_id")
