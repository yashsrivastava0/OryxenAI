"""Add provider-observability columns to agent_runs.

Revision ID: 0004_discovery_run_metadata
Revises: 0003_discovery_source_documents
Create Date: 2026-08-05 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_discovery_run_metadata"
down_revision: str | None = "0003_discovery_source_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("finish_reason", sa.Text(), nullable=True))
    op.add_column("agent_runs", sa.Column("latency_ms", sa.Double(), nullable=True))
    op.add_column(
        "agent_runs",
        sa.Column("usage", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_runs", "usage")
    op.drop_column("agent_runs", "latency_ms")
    op.drop_column("agent_runs", "finish_reason")
