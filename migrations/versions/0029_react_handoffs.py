"""Temporary React delivery records, independent cleanup lifetime.

Revision ID: 0029_react_handoffs
Revises: 0028_private_supabase_app_schema
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0029_react_handoffs"
down_revision = "0028_private_supabase_app_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_background_jobs_execution_lane", "background_jobs", type_="check")
    op.create_check_constraint(
        "ck_background_jobs_execution_lane",
        "background_jobs",
        "execution_lane IS NULL OR execution_lane IN ('model-generation', 'react-delivery')",
    )
    op.create_table(
        "react_handoffs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app_users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "portfolio_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolio_sessions.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "source_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolio_site_versions.id", ondelete="SET NULL"),
        ),
        sa.Column("job_id", postgresql.UUID(as_uuid=True)),
        *[
            sa.Column(name, sa.Text(), nullable=False)
            for name in (
                "status",
                "source_sha256",
                "theme_id",
                "adapter_revision",
                "viewer_version",
                "artifact_prefix",
            )
        ],
        sa.Column("manifest", postgresql.JSONB(), nullable=False),
        sa.Column("receipt", postgresql.JSONB(), nullable=False),
        sa.Column("error", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        *[
            sa.Column(name, sa.DateTime(timezone=True))
            for name in ("ready_at", "expires_at", "revoked_at", "cleaned_at")
        ],
        sa.CheckConstraint(
            "status IN ('queued','preparing','validating','ready','failed','revoked','expired')",
            name="ck_react_handoff_status",
        ),
    )
    op.create_index("ix_react_handoff_expiry", "react_handoffs", ["status", "expires_at"])
    op.create_index("ix_react_handoff_source", "react_handoffs", ["source_version_id"])
    op.create_index(
        "uq_react_handoff_pending",
        "react_handoffs",
        ["portfolio_session_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued','preparing','validating')"),
    )
    op.create_index(
        "uq_react_handoff_ready",
        "react_handoffs",
        ["portfolio_session_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ready'"),
    )
    # Match the existing server-only Supabase boundary for the new table.
    op.execute("ALTER TABLE react_handoffs ENABLE ROW LEVEL SECURITY")
    op.execute(
        "DO $$ DECLARE role_name text; BEGIN FOR role_name IN SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated', 'service_role') LOOP EXECUTE format('REVOKE ALL ON TABLE public.react_handoffs FROM %I', role_name); END LOOP; END $$"
    )


def downgrade() -> None:
    op.drop_table("react_handoffs")
    op.execute(
        "UPDATE background_jobs SET execution_lane = NULL WHERE execution_lane = 'react-delivery'"
    )
    op.drop_constraint("ck_background_jobs_execution_lane", "background_jobs", type_="check")
    op.create_check_constraint(
        "ck_background_jobs_execution_lane",
        "background_jobs",
        "execution_lane IS NULL OR execution_lane IN ('model-generation')",
    )
