"""Add background_jobs and service_heartbeats.

Revision ID: 0002_background_jobs
Revises: 0001_initial
Create Date: 2025-06-01 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_background_jobs"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # background_jobs
    op.create_table(
        "background_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_kind", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column(
            "payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error_payload", postgresql.JSONB(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("locked_by", sa.Text(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_scope", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
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
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    # service_heartbeats
    op.create_table(
        "service_heartbeats",
        sa.Column("instance_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("service_name", sa.Text(), nullable=False, server_default="oryxenai-worker"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )

    # Indexes — background_jobs
    op.create_index(
        "ix_bgjobs_claim",
        "background_jobs",
        ["status", "available_at", "priority", "created_at"],
        postgresql_where=sa.text("status = 'queued'"),
    )
    op.create_index(
        "ix_bgjobs_stale",
        "background_jobs",
        ["status", "heartbeat_at"],
        postgresql_where=sa.text("status = 'running'"),
    )
    op.create_index("ix_bgjobs_kind_created", "background_jobs", ["job_kind", "created_at"])
    op.create_index("ix_bgjobs_status", "background_jobs", ["status"])
    op.create_index(
        "ux_bgjobs_idempotency",
        "background_jobs",
        ["idempotency_scope", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_scope IS NOT NULL AND idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_bgjobs_idempotency", table_name="background_jobs")
    op.drop_index("ix_bgjobs_status", table_name="background_jobs")
    op.drop_index("ix_bgjobs_kind_created", table_name="background_jobs")
    op.drop_index("ix_bgjobs_stale", table_name="background_jobs")
    op.drop_index("ix_bgjobs_claim", table_name="background_jobs")
    op.drop_table("background_jobs")
    op.drop_table("service_heartbeats")
