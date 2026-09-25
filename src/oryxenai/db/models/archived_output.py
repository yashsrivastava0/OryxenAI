"""Minimal mappings for retained output rows used by account cleanup only.

The table names are fixed by the deployed database schema. These mappings do
not register jobs, expose routes, or execute portfolio generation workflows.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from oryxenai.db.base import Base


class ArchivedOutputRun(Base):
    __tablename__ = "code_generator_runs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    portfolio_session_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    artifact_reference: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    active_preview: Mapped[dict[str, object] | None] = mapped_column(JSONB)


class ArchivedOutputAttempt(Base):
    __tablename__ = "code_generator_stage_attempts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    artifact_references: Mapped[list[dict[str, object]] | None] = mapped_column(JSONB)


class ArchivedOutputEvent(Base):
    __tablename__ = "code_generator_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)


__all__ = ["ArchivedOutputAttempt", "ArchivedOutputEvent", "ArchivedOutputRun"]
