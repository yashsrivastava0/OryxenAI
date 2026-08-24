"""Add Phase 3 entitlement bindings and durable worker authorization fencing.

Revision ID: 0016_auth_entitlements_worker_fencing
Revises: 0015_portfolio_ownership
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Identifiers are selected exclusively from the closed tuple above and are
# passed through PostgreSQL format(%I) inside the block.
# ruff: noqa: S608

revision: str = "0016_auth_entitlements_worker_fencing"
down_revision: str | None = "0015_portfolio_ownership"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Phase 2 already enabled RLS and revoked browser-role privileges for the
# existing business tables.  This revision owns only the new entitlement
# table; repeating the Phase 2 sweep would obscure migration ownership and
# needlessly rewrite existing security state.
_AUTH_TABLES = ("portfolio_entitlements",)


def _set_rls_and_privileges() -> None:
    tables = ", ".join(repr(table) for table in _AUTH_TABLES)
    op.execute(
        f"""
        DO $$
        DECLARE table_name text;
        DECLARE role_name text;
        BEGIN
            FOREACH table_name IN ARRAY ARRAY[{tables}]
            LOOP
                IF to_regclass('public.' || table_name) IS NOT NULL THEN
                    EXECUTE format(
                        'ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name
                    );
                    FOR role_name IN
                        SELECT rolname FROM pg_roles
                        WHERE rolname IN ('anon', 'authenticated', 'service_role')
                    LOOP
                        EXECUTE format(
                            'REVOKE ALL PRIVILEGES ON TABLE public.%I FROM %I',
                            table_name, role_name
                        );
                    END LOOP;
                END IF;
            END LOOP;
        END $$;
        """
    )


def upgrade() -> None:
    # Existing direct session FKs were permissive during Phase 2.  The
    # durable snapshot FKs introduced below must prevent deletion of a
    # referenced local identity or aggregate.
    op.execute(
        "ALTER TABLE code_generator_runs "
        "DROP CONSTRAINT IF EXISTS fk_codegen_runs_portfolio_session"
    )
    op.execute(
        "ALTER TABLE agent_runs DROP CONSTRAINT IF EXISTS agent_runs_portfolio_session_id_fkey"
    )

    op.add_column(
        "agent_runs",
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "agent_runs",
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "agent_runs",
        sa.Column(
            "authorization_context_version", sa.Integer(), nullable=False, server_default="0"
        ),
    )

    for name, column in (
        ("owner_user_id", postgresql.UUID(as_uuid=True)),
        ("actor_user_id", postgresql.UUID(as_uuid=True)),
        ("portfolio_session_id", postgresql.UUID(as_uuid=True)),
    ):
        if name != "portfolio_session_id":
            op.add_column(
                "code_generator_runs",
                sa.Column(name, column, nullable=True),
            )
    op.add_column(
        "code_generator_runs",
        sa.Column(
            "authorization_context_version", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "code_generator_runs",
        sa.Column("entitlement_revision", sa.Integer(), nullable=True),
    )

    op.add_column(
        "background_jobs",
        sa.Column("portfolio_session_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "background_jobs",
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "background_jobs",
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "background_jobs",
        sa.Column(
            "authorization_context_version", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "background_jobs",
        sa.Column("entitlement_revision", sa.Integer(), nullable=True),
    )
    op.add_column("background_jobs", sa.Column("execution_lane", sa.Text(), nullable=True))

    op.create_foreign_key(
        "fk_agent_runs_portfolio_session",
        "agent_runs",
        "portfolio_sessions",
        ["portfolio_session_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_agent_runs_owner_user",
        "agent_runs",
        "app_users",
        ["owner_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_agent_runs_actor_user",
        "agent_runs",
        "app_users",
        ["actor_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_codegen_runs_portfolio_session",
        "code_generator_runs",
        "portfolio_sessions",
        ["portfolio_session_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_codegen_runs_owner_user",
        "code_generator_runs",
        "app_users",
        ["owner_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_codegen_runs_actor_user",
        "code_generator_runs",
        "app_users",
        ["actor_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_background_jobs_portfolio_session",
        "background_jobs",
        "portfolio_sessions",
        ["portfolio_session_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_background_jobs_owner_user",
        "background_jobs",
        "app_users",
        ["owner_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_background_jobs_actor_user",
        "background_jobs",
        "app_users",
        ["actor_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    for table in ("agent_runs", "code_generator_runs", "background_jobs"):
        op.create_check_constraint(
            f"ck_{table}_authorization_context_version",
            table,
            "authorization_context_version IN (0, 1)",
        )
        op.create_check_constraint(
            f"ck_{table}_current_context_bindings",
            table,
            "authorization_context_version = 0 OR "
            "(portfolio_session_id IS NOT NULL AND owner_user_id IS NOT NULL "
            "AND actor_user_id IS NOT NULL)",
        )
        op.create_index(
            f"ix_{table}_authorization",
            table,
            ["portfolio_session_id", "owner_user_id", "actor_user_id"],
        )
    for table in ("code_generator_runs", "background_jobs"):
        op.create_check_constraint(
            f"ck_{table}_entitlement_revision",
            table,
            "entitlement_revision IS NULL OR entitlement_revision >= 0",
        )

    op.create_check_constraint(
        "ck_background_jobs_execution_lane",
        "background_jobs",
        "execution_lane IS NULL OR execution_lane IN ('model-generation')",
    )
    op.create_index(
        "ux_bgjobs_running_execution_lane",
        "background_jobs",
        ["execution_lane"],
        unique=True,
        postgresql_where=sa.text("status = 'running' AND execution_lane IS NOT NULL"),
    )

    op.create_table(
        "portfolio_entitlements",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("portfolio_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("generation_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("successful_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("user_id", name="pk_portfolio_entitlements"),
        sa.UniqueConstraint("portfolio_session_id", name="uq_portfolio_entitlements_session"),
        sa.UniqueConstraint("generation_run_id", name="uq_portfolio_entitlements_generation"),
        sa.UniqueConstraint("successful_run_id", name="uq_portfolio_entitlements_success"),
    )
    op.create_foreign_key(
        "fk_portfolio_entitlements_user",
        "portfolio_entitlements",
        "app_users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_portfolio_entitlements_session",
        "portfolio_entitlements",
        "portfolio_sessions",
        ["portfolio_session_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_portfolio_entitlements_generation",
        "portfolio_entitlements",
        "code_generator_runs",
        ["generation_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_portfolio_entitlements_success",
        "portfolio_entitlements",
        "code_generator_runs",
        ["successful_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_portfolio_entitlements_revision",
        "portfolio_entitlements",
        "revision >= 0",
    )
    op.create_check_constraint(
        "ck_portfolio_entitlements_generation_requires_session",
        "portfolio_entitlements",
        "generation_run_id IS NULL OR portfolio_session_id IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_portfolio_entitlements_success_requires_generation",
        "portfolio_entitlements",
        "successful_run_id IS NULL OR generation_run_id IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_portfolio_entitlements_success_matches_generation",
        "portfolio_entitlements",
        "successful_run_id IS NULL OR successful_run_id = generation_run_id",
    )
    op.create_check_constraint(
        "ck_portfolio_entitlements_consumed_consistency",
        "portfolio_entitlements",
        "(consumed_at IS NULL AND successful_run_id IS NULL) OR "
        "(consumed_at IS NOT NULL AND successful_run_id IS NOT NULL)",
    )
    # Fail the migration with an actionable message if the Phase 2 database
    # already has more than one non-legacy owned session for one normal user.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM portfolio_sessions AS ps
                JOIN app_users AS u ON u.id = ps.owner_user_id
                WHERE ps.owner_user_id IS NOT NULL
                  AND ps.legacy_quarantined = false
                  AND u.role = 'user'
                GROUP BY ps.owner_user_id
                HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'Phase 3 entitlement migration found more than one owned portfolio session for a normal user; reconcile before upgrading';
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        INSERT INTO portfolio_entitlements (user_id, portfolio_session_id)
        SELECT u.id, s.id
        FROM app_users AS u
        LEFT JOIN LATERAL (
            SELECT ps.id
            FROM portfolio_sessions AS ps
            WHERE ps.owner_user_id = u.id AND ps.legacy_quarantined = false
            ORDER BY ps.created_at ASC, ps.id ASC
            LIMIT 1
        ) AS s ON true
        WHERE u.role = 'user'
        ON CONFLICT (user_id) DO NOTHING
        """
    )

    # Old queued/running portfolio jobs have no durable actor/owner snapshot.
    # They must not silently execute after this migration.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM background_jobs
                WHERE status IN ('queued', 'running')
                  AND authorization_context_version = 0
                  AND (
                    payload ? 'portfolio_session_id'
                    OR payload ? 'session_id'
                    OR payload ? 'agent_run_id'
                    OR (
                        (payload ? 'code_generator_run_id' OR payload ? 'development_run_id')
                        AND NOT EXISTS (
                            SELECT 1
                            FROM code_generator_runs AS cgr
                            WHERE cgr.id = CASE
                                WHEN payload ? 'code_generator_run_id'
                                     AND payload->>'code_generator_run_id' ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                                THEN (payload->>'code_generator_run_id')::uuid
                                WHEN payload ? 'development_run_id'
                                     AND payload->>'development_run_id' ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                                THEN (payload->>'development_run_id')::uuid
                                ELSE NULL
                            END
                            AND cgr.run_mode = 'development'
                        )
                    )
                  )
            ) THEN
                RAISE EXCEPTION
                    'Phase 3 migration found queued/running portfolio jobs without durable authorization context; stop and reconcile them before upgrading';
            END IF;
        END $$;
        """
    )

    _set_rls_and_privileges()


def downgrade() -> None:
    # This downgrade is intended only for the dedicated test database.  It
    # reverses this revision without touching earlier ownership protections.
    op.drop_constraint(
        "ck_portfolio_entitlements_consumed_consistency", "portfolio_entitlements", type_="check"
    )
    op.drop_constraint(
        "ck_portfolio_entitlements_success_matches_generation",
        "portfolio_entitlements",
        type_="check",
    )
    op.drop_constraint(
        "ck_portfolio_entitlements_success_requires_generation",
        "portfolio_entitlements",
        type_="check",
    )
    op.drop_constraint(
        "ck_portfolio_entitlements_generation_requires_session",
        "portfolio_entitlements",
        type_="check",
    )
    op.drop_constraint(
        "ck_portfolio_entitlements_revision", "portfolio_entitlements", type_="check"
    )
    for name in (
        "fk_portfolio_entitlements_success",
        "fk_portfolio_entitlements_generation",
        "fk_portfolio_entitlements_session",
        "fk_portfolio_entitlements_user",
    ):
        op.drop_constraint(name, "portfolio_entitlements", type_="foreignkey")
    op.drop_table("portfolio_entitlements")
    op.drop_index("ux_bgjobs_running_execution_lane", table_name="background_jobs")
    op.drop_constraint("ck_background_jobs_execution_lane", "background_jobs", type_="check")
    for table in ("agent_runs", "code_generator_runs", "background_jobs"):
        op.drop_index(f"ix_{table}_authorization", table_name=table)
        op.drop_constraint(f"ck_{table}_current_context_bindings", table, type_="check")
        op.drop_constraint(f"ck_{table}_authorization_context_version", table, type_="check")
    for table in ("code_generator_runs", "background_jobs"):
        op.drop_constraint(f"ck_{table}_entitlement_revision", table, type_="check")
    for name, table in (
        ("fk_background_jobs_actor_user", "background_jobs"),
        ("fk_background_jobs_owner_user", "background_jobs"),
        ("fk_background_jobs_portfolio_session", "background_jobs"),
        ("fk_codegen_runs_actor_user", "code_generator_runs"),
        ("fk_codegen_runs_owner_user", "code_generator_runs"),
        ("fk_codegen_runs_portfolio_session", "code_generator_runs"),
        ("fk_agent_runs_actor_user", "agent_runs"),
        ("fk_agent_runs_owner_user", "agent_runs"),
        ("fk_agent_runs_portfolio_session", "agent_runs"),
    ):
        op.drop_constraint(name, table, type_="foreignkey")
    for column, table in (
        ("execution_lane", "background_jobs"),
        ("entitlement_revision", "background_jobs"),
        ("authorization_context_version", "background_jobs"),
        ("actor_user_id", "background_jobs"),
        ("owner_user_id", "background_jobs"),
        ("portfolio_session_id", "background_jobs"),
        ("entitlement_revision", "code_generator_runs"),
        ("authorization_context_version", "code_generator_runs"),
        ("actor_user_id", "code_generator_runs"),
        ("owner_user_id", "code_generator_runs"),
        ("authorization_context_version", "agent_runs"),
        ("actor_user_id", "agent_runs"),
        ("owner_user_id", "agent_runs"),
    ):
        op.drop_column(table, column)
    op.create_foreign_key(
        "fk_codegen_runs_portfolio_session",
        "code_generator_runs",
        "portfolio_sessions",
        ["portfolio_session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "agent_runs_portfolio_session_id_fkey",
        "agent_runs",
        "portfolio_sessions",
        ["portfolio_session_id"],
        ["id"],
        ondelete="CASCADE",
    )
