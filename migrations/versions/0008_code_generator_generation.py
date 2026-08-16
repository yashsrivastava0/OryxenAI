"""Add standalone Code Generator Phase 3 generation persistence.

Revision ID: 0008_code_generator_generation
Revises: 0007_code_generator_acquisition
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_code_generator_generation"
down_revision: str | None = "0007_code_generator_acquisition"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    table = "code_generator_development_runs"
    op.add_column(
        table, sa.Column("generation_job_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(table, sa.Column("generation_projection", postgresql.JSONB(), nullable=True))
    op.add_column(table, sa.Column("source_checkpoint", postgresql.JSONB(), nullable=True))
    op.add_column(
        table,
        sa.Column(
            "source_summary",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    table = "code_generator_development_runs"
    op.drop_column(table, "source_summary")
    op.drop_column(table, "source_checkpoint")
    op.drop_column(table, "generation_projection")
    op.drop_column(table, "generation_job_id")
