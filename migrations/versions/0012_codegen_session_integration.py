"""Promote Code Generator runs to the production session pipeline.

Revision ID: 0012_codegen_session
Revises: 0011_codegen_coordinator
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_codegen_session"
down_revision: str | None = "0011_codegen_coordinator"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table("code_generator_development_runs", "code_generator_runs")
    op.rename_table("code_generator_development_events", "code_generator_events")

    op.execute(
        "ALTER INDEX ix_codegen_development_runs_status_created "
        "RENAME TO ix_codegen_runs_status_created"
    )
    op.execute(
        "ALTER INDEX ux_codegen_development_runs_idempotency "
        "RENAME TO ux_codegen_runs_idempotency_legacy"
    )
    op.execute(
        "ALTER INDEX ix_codegen_development_events_run_sequence "
        "RENAME TO ix_codegen_events_run_sequence"
    )
    op.execute(
        "ALTER TABLE code_generator_events "
        "RENAME CONSTRAINT ux_codegen_development_event_sequence "
        "TO ux_codegen_event_sequence"
    )

    table = "code_generator_runs"
    op.add_column(
        table,
        sa.Column("run_mode", sa.Text(), nullable=False, server_default="development"),
    )
    op.add_column(table, sa.Column("portfolio_session_id", postgresql.UUID(), nullable=True))
    op.add_column(
        table,
        sa.Column("idempotency_scope", sa.Text(), nullable=False, server_default="development"),
    )
    for name in (
        "build_preparation_source_ref",
        "artifact_reference",
        "artifact_receipt",
        "preflight_receipt",
        "creative_direction",
        "integration_review",
    ):
        op.add_column(table, sa.Column(name, postgresql.JSONB(), nullable=True))

    op.create_foreign_key(
        "fk_codegen_runs_portfolio_session",
        table,
        "portfolio_sessions",
        ["portfolio_session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_codegen_runs_session_created",
        table,
        ["portfolio_session_id", "created_at"],
    )
    op.drop_index("ux_codegen_runs_idempotency_legacy", table_name=table)
    op.create_index(
        "ux_codegen_runs_idempotency",
        table,
        ["idempotency_scope", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    table = "code_generator_runs"
    op.drop_index("ux_codegen_runs_idempotency", table_name=table)
    op.create_index(
        "ux_codegen_development_runs_idempotency",
        table,
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.drop_index("ix_codegen_runs_session_created", table_name=table)
    op.drop_constraint("fk_codegen_runs_portfolio_session", table, type_="foreignkey")
    for name in (
        "integration_review",
        "creative_direction",
        "preflight_receipt",
        "artifact_receipt",
        "artifact_reference",
        "build_preparation_source_ref",
        "idempotency_scope",
        "portfolio_session_id",
        "run_mode",
    ):
        op.drop_column(table, name)

    op.execute(
        "ALTER TABLE code_generator_events RENAME CONSTRAINT ux_codegen_event_sequence "
        "TO ux_codegen_development_event_sequence"
    )
    op.execute(
        "ALTER INDEX ix_codegen_events_run_sequence "
        "RENAME TO ix_codegen_development_events_run_sequence"
    )
    op.execute(
        "ALTER INDEX ix_codegen_runs_status_created "
        "RENAME TO ix_codegen_development_runs_status_created"
    )
    op.rename_table("code_generator_events", "code_generator_development_events")
    op.rename_table("code_generator_runs", "code_generator_development_runs")
