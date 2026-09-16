"""Persist observed per-stage duration data for standalone Code Generator runs."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024_codegen_stage_durations"
down_revision: str | None = "0023_model_wallet_consumption"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "code_generator_runs",
        sa.Column(
            "stage_durations_ms",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("code_generator_runs", "stage_durations_ms")
