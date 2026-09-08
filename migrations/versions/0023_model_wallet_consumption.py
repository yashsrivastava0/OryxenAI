"""Track provider wallet consumption separately from promotional usage."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_model_wallet_consumption"
down_revision: str | None = "0022_model_usage_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "model_call_attempts",
        sa.Column("wallet_micro_usd", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("model_call_attempts", "wallet_micro_usd")
