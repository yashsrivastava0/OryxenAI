"""Keep OryxenAI's public-schema tables server-only on Supabase.

Revision ID: 0028_private_supabase_app_schema
Revises: 0027_site_versions
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0028_private_supabase_app_schema"
down_revision: str | None = "0027_site_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # This is deliberately idempotent: an Azure PostgreSQL instance does not
    # have Supabase API roles, while a Supabase restore can carry a current
    # Alembic revision that would otherwise skip the older privilege migration.
    op.execute(
        """
        DO $$
        DECLARE table_name text;
        DECLARE role_name text;
        BEGIN
            FOREACH table_name IN ARRAY ARRAY[
                'app_users', 'app_user_capacity', 'portfolio_sessions',
                'background_jobs', 'agent_runs', 'service_heartbeats',
                'model_operations', 'model_call_attempts',
                'model_budget_reservations', 'model_capacity_windows',
                'model_provider_observations', 'model_call_cache',
                'portfolio_site_versions', 'portfolio_chat_messages',
                'portfolio_entitlements', 'admin_audit_events',
                'admin_operations', 'deleted_identity_tombstones',
                'deleted_portfolio_tombstones',
                'code_generator_runs', 'code_generator_events',
                'code_generator_stage_attempts'
            ]
            LOOP
                IF to_regclass('public.' || table_name) IS NOT NULL THEN
                    EXECUTE format(
                        'ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',
                        table_name
                    );
                    FOR role_name IN
                        SELECT rolname FROM pg_roles
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

            FOR role_name IN
                SELECT rolname FROM pg_roles
                WHERE rolname IN ('anon', 'authenticated', 'service_role')
            LOOP
                EXECUTE format(
                    'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM %I',
                    role_name
                );
                EXECUTE format(
                    'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM %I',
                    role_name
                );
                EXECUTE format(
                    'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM %I',
                    role_name
                );
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    # Do not silently restore Supabase API access when rolling back application
    # code. These revocations remain in effect by design.
    pass
