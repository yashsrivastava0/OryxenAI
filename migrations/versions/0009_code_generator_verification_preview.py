"""Add standalone Code Generator Phase 4 verification and preview state.

Revision ID: 0009_codegen_verify_preview
Revises: 0008_code_generator_generation
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_codegen_verify_preview"
down_revision: str | None = "0008_code_generator_generation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    table = "code_generator_development_runs"
    op.add_column(
        table, sa.Column("verification_job_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(table, sa.Column("verification_projection", postgresql.JSONB(), nullable=True))
    op.add_column(table, sa.Column("candidate_artifact", postgresql.JSONB(), nullable=True))
    op.add_column(table, sa.Column("pending_promotion", postgresql.JSONB(), nullable=True))
    op.add_column(table, sa.Column("active_preview", postgresql.JSONB(), nullable=True))
    op.add_column(table, sa.Column("terminal_failure", postgresql.JSONB(), nullable=True))
    op.add_column(table, sa.Column("preview_host", sa.Text(), nullable=True))


def downgrade() -> None:
    table = "code_generator_development_runs"
    op.drop_column(table, "preview_host")
    op.drop_column(table, "terminal_failure")
    op.drop_column(table, "active_preview")
    op.drop_column(table, "pending_promotion")
    op.drop_column(table, "candidate_artifact")
    op.drop_column(table, "verification_projection")
    op.drop_column(table, "verification_job_id")
