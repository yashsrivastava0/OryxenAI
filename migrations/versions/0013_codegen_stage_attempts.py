"""Add normalized Code Generator stage attempts and execution metadata.

Revision ID: 0013_codegen_stage_attempts
Revises: 0012_codegen_session
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_codegen_stage_attempts"
down_revision: str | None = "0012_codegen_session"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "code_generator_runs",
        sa.Column(
            "pipeline_contract_version",
            sa.Text(),
            nullable=False,
            server_default="code-generator-v3",
        ),
    )
    op.add_column("code_generator_runs", sa.Column("trace_id", sa.Text(), nullable=True))
    op.add_column(
        "code_generator_runs",
        sa.Column("active_attempt_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_codegen_runs_active_attempt", "code_generator_runs", ["active_attempt_id"])

    op.create_table(
        "code_generator_stage_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("code_generator_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("expected_run_revision", sa.Integer(), nullable=False),
        sa.Column("input_fingerprint", sa.Text(), nullable=False),
        sa.Column("worker_instance", sa.Text(), nullable=True),
        sa.Column("worker_version", sa.Text(), nullable=True),
        sa.Column("trace_id", sa.Text(), nullable=True),
        sa.Column(
            "artifact_references",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("safe_error", postgresql.JSONB(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "stage", "attempt_no", name="ux_codegen_stage_attempt_no"),
    )
    op.create_index(
        "ix_codegen_stage_attempts_run_stage",
        "code_generator_stage_attempts",
        ["run_id", "stage", "attempt_no"],
    )
    op.create_index(
        "ux_codegen_stage_attempts_active",
        "code_generator_stage_attempts",
        ["run_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running', 'retrying')"),
    )

    op.add_column(
        "code_generator_events",
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "code_generator_events",
        sa.Column(
            "pipeline_contract_version",
            sa.Text(),
            nullable=False,
            server_default="code-generator-v3",
        ),
    )
    op.add_column("code_generator_events", sa.Column("trace_id", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_codegen_events_attempt",
        "code_generator_events",
        "code_generator_stage_attempts",
        ["attempt_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_codegen_events_attempt", "code_generator_events", ["attempt_id"])


def downgrade() -> None:
    op.drop_index("ix_codegen_events_attempt", table_name="code_generator_events")
    op.drop_constraint("fk_codegen_events_attempt", "code_generator_events", type_="foreignkey")
    op.drop_column("code_generator_events", "trace_id")
    op.drop_column("code_generator_events", "pipeline_contract_version")
    op.drop_column("code_generator_events", "attempt_id")
    op.drop_index("ux_codegen_stage_attempts_active", table_name="code_generator_stage_attempts")
    op.drop_index("ix_codegen_stage_attempts_run_stage", table_name="code_generator_stage_attempts")
    op.drop_table("code_generator_stage_attempts")
    op.drop_index("ix_codegen_runs_active_attempt", table_name="code_generator_runs")
    op.drop_column("code_generator_runs", "active_attempt_id")
    op.drop_column("code_generator_runs", "trace_id")
    op.drop_column("code_generator_runs", "pipeline_contract_version")
