"""ServiceHeartbeat ORM model — worker liveness tracking."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from oryxenai.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ServiceHeartbeat(Base):
    """Tracks worker process liveness.

    No secrets, host credentials, or environment contents are stored here.
    """

    __tablename__ = "service_heartbeats"

    instance_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    service_name: Mapped[str] = mapped_column(Text, nullable=False, default="oryxenai-worker")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    service_metadata: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict, name="metadata"
    )
