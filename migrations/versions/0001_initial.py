"""Initial schema: portfolio_sessions and agent_runs.

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # portfolio_sessions
    op.create_table(
        "portfolio_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False, server_default="Untitled session"),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column(
            "current_state",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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
    )

    # agent_runs
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "portfolio_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolio_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_key", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column(
            "input_payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("output_payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "state_before",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("state_after", postgresql.JSONB(), nullable=True),
        sa.Column(
            "model_metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_payload", postgresql.JSONB(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Indexes
    op.create_index(
        "ix_agent_runs_session_created", "agent_runs", ["portfolio_session_id", "created_at"]
    )
    op.create_index("ix_agent_runs_agent_created", "agent_runs", ["agent_key", "created_at"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])
    op.create_index(
        "ux_agent_runs_idempotency",
        "agent_runs",
        ["portfolio_session_id", "agent_key", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_agent_runs_idempotency", table_name="agent_runs")
    op.drop_index("ix_agent_runs_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_agent_created", table_name="agent_runs")
    op.drop_index("ix_agent_runs_session_created", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_table("portfolio_sessions")
