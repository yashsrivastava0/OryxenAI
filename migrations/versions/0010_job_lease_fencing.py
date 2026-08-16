"""Add durable lease fencing for stale worker recovery.

Revision ID: 0010_job_lease_fencing
Revises: 0009_codegen_verify_preview
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_job_lease_fencing"
down_revision: str | None = "0009_codegen_verify_preview"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("background_jobs", sa.Column("lease_token", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("background_jobs", "lease_token")
