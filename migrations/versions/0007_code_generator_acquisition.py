"""Add standalone Code Generator Phase 2 acquisition persistence.

Revision ID: 0007_code_generator_acquisition
Revises: 0006_code_generator_development_runs
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_code_generator_acquisition"
down_revision: str | None = "0006_codegen_dev_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    table = "code_generator_development_runs"
    op.add_column(table, sa.Column("acquire_job_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(table, sa.Column("resource_ledger", postgresql.JSONB(), nullable=True))
    op.add_column(table, sa.Column("dependency_ledger", postgresql.JSONB(), nullable=True))
    op.add_column(table, sa.Column("acquire_receipt", postgresql.JSONB(), nullable=True))
    op.add_column(
        table,
        sa.Column(
            "acquire_summary",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        table,
        sa.Column("plan_delta_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    table = "code_generator_development_runs"
    op.drop_column(table, "plan_delta_count")
    op.drop_column(table, "acquire_summary")
    op.drop_column(table, "acquire_receipt")
    op.drop_column(table, "dependency_ledger")
    op.drop_column(table, "resource_ledger")
    op.drop_column(table, "acquire_job_id")
