"""Add standalone Code Generator Phase 1 development persistence.

Revision ID: 0006_codegen_dev_runs
Revises: 0005_drop_discovery_docs
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_codegen_dev_runs"
down_revision: str | None = "0005_drop_discovery_docs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "code_generator_development_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_reference", postgresql.JSONB(), nullable=False),
        sa.Column("input_receipt", postgresql.JSONB(), nullable=True),
        sa.Column("context_receipt", postgresql.JSONB(), nullable=True),
        sa.Column("planner_receipt", postgresql.JSONB(), nullable=True),
        sa.Column("plan", postgresql.JSONB(), nullable=True),
        sa.Column("plan_summary", postgresql.JSONB(), nullable=False),
        sa.Column("issues", postgresql.JSONB(), nullable=False),
        sa.Column("admitted_identity", sa.Text(), nullable=True),
        sa.Column("background_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_codegen_development_runs_status_created",
        "code_generator_development_runs",
        ["status", "created_at"],
    )
    op.create_index(
        "ux_codegen_development_runs_idempotency",
        "code_generator_development_runs",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.create_table(
        "code_generator_development_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("code_generator_development_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("level", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "sequence", name="ux_codegen_development_event_sequence"),
    )
    op.create_index(
        "ix_codegen_development_events_run_sequence",
        "code_generator_development_events",
        ["run_id", "sequence"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_codegen_development_events_run_sequence", table_name="code_generator_development_events"
    )
    op.drop_table("code_generator_development_events")
    op.drop_index(
        "ux_codegen_development_runs_idempotency", table_name="code_generator_development_runs"
    )
    op.drop_index(
        "ix_codegen_development_runs_status_created", table_name="code_generator_development_runs"
    )
    op.drop_table("code_generator_development_runs")
