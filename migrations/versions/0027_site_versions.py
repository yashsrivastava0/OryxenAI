"""Add generated-portfolio versions and the Studio chat transcript."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027_site_versions"
down_revision: str | None = "0026_model_lane_slots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUSES = (
    "queued",
    "planning",
    "generating",
    "validating",
    "verifying",
    "ready",
    "failed",
    "cancelled",
    "no_change",
)
_ORIGINS = ("initial", "change", "retry", "restore")


def _in_list(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def upgrade() -> None:
    op.create_table(
        "portfolio_site_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("portfolio_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=True),
        sa.Column("origin", sa.Text(), nullable=False, server_default="initial"),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column("parent_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("instruction", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "change_plan", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "content_snapshot",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("content_sha256", sa.Text(), nullable=False, server_default=""),
        sa.Column("theme_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("theme_sha256", sa.Text(), nullable=False, server_default=""),
        sa.Column("lang", sa.Text(), nullable=False, server_default="en"),
        sa.Column("index_html", sa.Text(), nullable=True),
        sa.Column("index_sha256", sa.Text(), nullable=True),
        sa.Column(
            "manifest", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "receipt", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "trace", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("error", postgresql.JSONB(), nullable=True),
        sa.Column("restricted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["portfolio_session_id"],
            ["portfolio_sessions.id"],
            name="fk_site_versions_portfolio_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["portfolio_site_versions.id"],
            name="fk_site_versions_parent",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("portfolio_session_id", "seq", name="uq_site_versions_session_seq"),
        sa.CheckConstraint(_in_list("status", _STATUSES), name="ck_site_versions_status"),
        sa.CheckConstraint(_in_list("origin", _ORIGINS), name="ck_site_versions_origin"),
        sa.CheckConstraint(
            "version_number IS NULL OR version_number > 0", name="ck_site_versions_number_positive"
        ),
    )
    op.create_index(
        "ux_site_versions_session_number",
        "portfolio_site_versions",
        ["portfolio_session_id", "version_number"],
        unique=True,
        postgresql_where=sa.text("version_number IS NOT NULL"),
    )
    op.create_index(
        "ix_site_versions_session_status",
        "portfolio_site_versions",
        ["portfolio_session_id", "status"],
    )

    op.create_table(
        "portfolio_chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("portfolio_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False, server_default="message"),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_message_id", sa.Text(), nullable=True),
        sa.Column(
            "meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["portfolio_session_id"],
            ["portfolio_sessions.id"],
            name="fk_chat_messages_portfolio_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["portfolio_site_versions.id"],
            name="fk_chat_messages_version",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("portfolio_session_id", "seq", name="uq_chat_messages_session_seq"),
        sa.CheckConstraint(
            _in_list("role", ("user", "assistant", "system")), name="ck_chat_messages_role"
        ),
        sa.CheckConstraint(
            _in_list("kind", ("message", "build", "notice")), name="ck_chat_messages_kind"
        ),
    )
    op.create_index(
        "ux_chat_messages_client_id",
        "portfolio_chat_messages",
        ["portfolio_session_id", "client_message_id"],
        unique=True,
        postgresql_where=sa.text("client_message_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_chat_messages_client_id", table_name="portfolio_chat_messages")
    op.drop_table("portfolio_chat_messages")
    op.drop_index("ix_site_versions_session_status", table_name="portfolio_site_versions")
    op.drop_index("ux_site_versions_session_number", table_name="portfolio_site_versions")
    op.drop_table("portfolio_site_versions")
