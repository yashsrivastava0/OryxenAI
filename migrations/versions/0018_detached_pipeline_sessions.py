"""Add explicit session classification for temporary detached pipelines."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_detached_pipeline_sessions"
down_revision: str | None = "0017_auth_admin_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "portfolio_sessions",
        sa.Column("session_mode", sa.Text(), nullable=True, server_default="legacy"),
    )
    op.execute(
        "UPDATE portfolio_sessions SET session_mode = "
        "CASE WHEN owner_user_id IS NULL THEN 'legacy' ELSE 'owned' END"
    )
    op.alter_column("portfolio_sessions", "session_mode", nullable=False, server_default="legacy")
    op.create_check_constraint(
        "ck_portfolio_sessions_session_mode",
        "portfolio_sessions",
        "session_mode IN ('owned', 'detached', 'legacy')",
    )
    op.create_check_constraint(
        "ck_portfolio_sessions_session_mode_consistency",
        "portfolio_sessions",
        "(session_mode = 'owned' AND owner_user_id IS NOT NULL AND legacy_quarantined = false) OR "
        "(session_mode IN ('detached', 'legacy') AND owner_user_id IS NULL AND legacy_quarantined = true)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_portfolio_sessions_session_mode_consistency",
        "portfolio_sessions",
        type_="check",
    )
    op.drop_constraint("ck_portfolio_sessions_session_mode", "portfolio_sessions", type_="check")
    op.drop_column("portfolio_sessions", "session_mode")
