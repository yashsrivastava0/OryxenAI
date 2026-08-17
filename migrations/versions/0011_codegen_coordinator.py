"""Persist standalone Code Generator coordinator state."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_codegen_coordinator"
down_revision: str | None = "0010_job_lease_fencing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "code_generator_development_runs",
        sa.Column("auto_advance", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "code_generator_development_runs",
        sa.Column("coordinator_stage", sa.Text(), nullable=False, server_default="plan"),
    )
    op.add_column(
        "code_generator_development_runs",
        sa.Column("selected_pack_receipt", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("code_generator_development_runs", "selected_pack_receipt")
    op.drop_column("code_generator_development_runs", "coordinator_stage")
    op.drop_column("code_generator_development_runs", "auto_advance")
