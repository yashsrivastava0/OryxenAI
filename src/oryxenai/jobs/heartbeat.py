"""Service heartbeat repository — worker liveness tracking."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.db.models.service_heartbeat import ServiceHeartbeat


class HeartbeatRepository:
    """Repository for service_heartbeats table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        instance_id: str,
        service_name: str,
        metadata: dict[str, object] | None = None,
    ) -> ServiceHeartbeat:
        now = datetime.now(UTC)
        stmt = select(ServiceHeartbeat).where(ServiceHeartbeat.instance_id == instance_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            row.last_seen_at = now
            if metadata is not None:
                row.service_metadata = metadata
            await self._session.flush()
            return row
        heartbeat = ServiceHeartbeat(
            instance_id=instance_id,
            service_name=service_name,
            started_at=now,
            last_seen_at=now,
            service_metadata=metadata or {},
        )
        self._session.add(heartbeat)
        await self._session.flush()
        await self._session.refresh(heartbeat)
        return heartbeat

    async def mark_stopped(self, instance_id: str) -> None:
        now = datetime.now(UTC)
        stmt = (
            update(ServiceHeartbeat)
            .where(ServiceHeartbeat.instance_id == instance_id)
            .values(stopped_at=now)
        )
        await self._session.execute(stmt)

    async def get_recent(
        self, service_name: str = "oryxenai-worker", limit: int = 10
    ) -> list[ServiceHeartbeat]:
        limit = max(1, min(limit, 50))
        stmt = (
            select(ServiceHeartbeat)
            .where(ServiceHeartbeat.service_name == service_name)
            .order_by(ServiceHeartbeat.last_seen_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest(self, service_name: str = "oryxenai-worker") -> ServiceHeartbeat | None:
        items = await self.get_recent(service_name=service_name, limit=1)
        return items[0] if items else None
