"""Generated-portfolio versions and the Studio chat transcript.

A version is an immutable artifact: the approved content snapshot it was built
from, the sealed ``index.html`` (the theme's files are pinned by hash and live
in the application image), and its receipt. Rows are created by the worker when
generation starts; only the session's ``code_generator`` state decides which one
is live. Both tables cascade with their session so every existing hard-delete
path keeps working.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from oryxenai.db.base import Base

VERSION_STATUSES = (
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
VERSION_ORIGINS = ("initial", "change", "retry", "restore")
CHAT_ROLES = ("user", "assistant", "system")
CHAT_KINDS = ("message", "build", "notice")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _in_list(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class PortfolioSiteVersion(Base):
    """One generated page version for a portfolio session."""

    __tablename__ = "portfolio_site_versions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "portfolio_sessions.id",
            name="fk_site_versions_portfolio_session",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    # Creation order within the session (never reused). ``version_number`` is
    # the user-facing v1, v2... assigned only when a version becomes ready.
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origin: Mapped[str] = mapped_column(Text, nullable=False, default="initial")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    parent_version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "portfolio_site_versions.id",
            name="fk_site_versions_parent",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    instruction: Mapped[str] = mapped_column(Text, nullable=False, default="")
    change_plan: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    content_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    content_sha256: Mapped[str] = mapped_column(Text, nullable=False, default="")
    theme_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    theme_sha256: Mapped[str] = mapped_column(Text, nullable=False, default="")
    lang: Mapped[str] = mapped_column(Text, nullable=False, default="en")
    index_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    index_sha256: Mapped[str | None] = mapped_column(Text, nullable=True)
    manifest: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    receipt: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    trace: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    error: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    # Set when the user asked to remove information as private: this version is
    # no longer served or restorable.
    restricted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    run_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    job_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("portfolio_session_id", "seq", name="uq_site_versions_session_seq"),
        Index(
            "ux_site_versions_session_number",
            "portfolio_session_id",
            "version_number",
            unique=True,
            postgresql_where=text("version_number IS NOT NULL"),
        ),
        Index("ix_site_versions_session_status", "portfolio_session_id", "status"),
        CheckConstraint(_in_list("status", VERSION_STATUSES), name="ck_site_versions_status"),
        CheckConstraint(_in_list("origin", VERSION_ORIGINS), name="ck_site_versions_origin"),
        CheckConstraint(
            "version_number IS NULL OR version_number > 0",
            name="ck_site_versions_number_positive",
        ),
    )


class PortfolioChatMessage(Base):
    """Append-only Studio transcript row (user requests, replies, build events)."""

    __tablename__ = "portfolio_chat_messages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "portfolio_sessions.id",
            name="fk_chat_messages_portfolio_session",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False, default="message")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "portfolio_site_versions.id",
            name="fk_chat_messages_version",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    # Client-supplied idempotency token for user messages (retries are safe).
    client_message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        UniqueConstraint("portfolio_session_id", "seq", name="uq_chat_messages_session_seq"),
        Index(
            "ux_chat_messages_client_id",
            "portfolio_session_id",
            "client_message_id",
            unique=True,
            postgresql_where=text("client_message_id IS NOT NULL"),
        ),
        CheckConstraint(_in_list("role", CHAT_ROLES), name="ck_chat_messages_role"),
        CheckConstraint(_in_list("kind", CHAT_KINDS), name="ck_chat_messages_kind"),
    )
