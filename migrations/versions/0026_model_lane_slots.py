"""Replace the single running model lane index with configurable slots."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_model_lane_slots"
down_revision: str | None = "0025_retire_generation_pipeline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ux_bgjobs_running_execution_lane", table_name="background_jobs")
    op.create_index(
        "ix_bgjobs_running_execution_lane",
        "background_jobs",
        ["execution_lane"],
        postgresql_where=sa.text("status = 'running' AND execution_lane IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_bgjobs_running_execution_lane", table_name="background_jobs")
    op.create_index(
        "ux_bgjobs_running_execution_lane",
        "background_jobs",
        ["execution_lane"],
        unique=True,
        postgresql_where=sa.text("status = 'running' AND execution_lane IS NOT NULL"),
    )
