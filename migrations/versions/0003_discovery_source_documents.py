"""Add immutable Discovery source snapshots.

Revision ID: 0003_discovery_source_documents
Revises: 0002_background_jobs
Create Date: 2026-08-05 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_discovery_source_documents"
down_revision: str | None = "0002_background_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_source_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "portfolio_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolio_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False, server_default="en"),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_discovery_source_session_created",
        "discovery_source_documents",
        ["portfolio_session_id", "created_at"],
    )
    op.create_index(
        "ix_discovery_source_kind",
        "discovery_source_documents",
        ["source_kind"],
    )
    op.create_index(
        "ux_discovery_source_current",
        "discovery_source_documents",
        ["portfolio_session_id", "source_kind"],
        unique=True,
        postgresql_where=sa.text("superseded_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_discovery_source_current", table_name="discovery_source_documents")
    op.drop_index("ix_discovery_source_kind", table_name="discovery_source_documents")
    op.drop_index("ix_discovery_source_session_created", table_name="discovery_source_documents")
    op.drop_table("discovery_source_documents")
