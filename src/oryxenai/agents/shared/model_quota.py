"""Quota-aware capacity observation and deterministic source selection."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from oryxenai.core.logging import get_logger

logger = get_logger("oryxenai.agents.model_quota")


@dataclass
class CapacitySnapshot:
    provider: str
    source_id: str
    model: str = ""
    request_limit: int | None = None
    input_token_limit: int | None = None
    daily_request_limit: int | None = None
    observed_requests: int = 0
    reserved_requests: int = 0
    observed_input_tokens: int = 0
    reserved_input_tokens: int = 0
    reset_at: float | None = None
    cooldown_until: float | None = None
    confidence: str = "unknown"
    updated_at: float = field(default_factory=time.time)

    def remaining_score(self, utilization_ceiling: float = 0.8) -> float:
        limits: list[float] = []
        for limit, used in (
            (self.request_limit, self.observed_requests + self.reserved_requests),
            (self.input_token_limit, self.observed_input_tokens + self.reserved_input_tokens),
            (self.daily_request_limit, self.observed_requests + self.reserved_requests),
        ):
            if isinstance(limit, int) and limit > 0:
                limits.append(max(0.0, (limit * utilization_ceiling - used) / limit))
        return min(limits) if limits else 0.5

    def available(
        self, *, estimated_input_tokens: int = 0, utilization_ceiling: float = 0.8
    ) -> bool:
        if self.cooldown_until is not None and self.cooldown_until > time.time():
            return False
        if self.request_limit is not None and (
            self.observed_requests + self.reserved_requests + 1
            > self.request_limit * utilization_ceiling
        ):
            return False
        if self.input_token_limit is not None and (
            self.observed_input_tokens + self.reserved_input_tokens + max(0, estimated_input_tokens)
            > self.input_token_limit * utilization_ceiling
        ):
            return False
        return not (
            self.daily_request_limit is not None
            and self.observed_requests + self.reserved_requests + 1
            > self.daily_request_limit * utilization_ceiling
        )


class CapacityRegistry:
    """In-process mirror of durable capacity observations.

    The database ledger remains authoritative across workers.  This registry
    makes a safe decision between calls in one process and deliberately uses
    least-loaded proportional capacity, never blind round-robin.
    """

    def __init__(self, utilization_ceiling: float = 0.8) -> None:
        self.utilization_ceiling = max(0.01, min(1.0, float(utilization_ceiling)))
        self._snapshots: dict[str, CapacitySnapshot] = {}
        self._failures: dict[str, tuple[int, float]] = {}

    def observe(self, snapshot: CapacitySnapshot) -> None:
        self._snapshots[snapshot.source_id] = snapshot

    def snapshot(self, source_id: str) -> CapacitySnapshot | None:
        return self._snapshots.get(source_id)

    def reserve(self, source_id: str, *, input_tokens: int = 0) -> None:
        snapshot = self._snapshots.setdefault(
            source_id, CapacitySnapshot(provider="", source_id=source_id)
        )
        snapshot.reserved_requests += 1
        snapshot.reserved_input_tokens += max(0, int(input_tokens))

    def settle(self, source_id: str, *, input_tokens: int = 0) -> None:
        snapshot = self._snapshots.get(source_id)
        if snapshot is None:
            return
        snapshot.reserved_requests = max(0, snapshot.reserved_requests - 1)
        snapshot.reserved_input_tokens = max(
            0, snapshot.reserved_input_tokens - max(0, int(input_tokens))
        )

    def mark_success(self, source_id: str, *, input_tokens: int = 0) -> None:
        snapshot = self._snapshots.setdefault(
            source_id, CapacitySnapshot(provider="", source_id=source_id)
        )
        self.settle(source_id, input_tokens=input_tokens)
        snapshot.observed_requests += 1
        snapshot.observed_input_tokens += max(0, int(input_tokens))
        snapshot.updated_at = time.time()
        self._failures.pop(source_id, None)

    def mark_failure(self, source_id: str, *, cooldown_seconds: float = 0.0) -> None:
        snapshot = self._snapshots.setdefault(
            source_id, CapacitySnapshot(provider="", source_id=source_id)
        )
        self.settle(source_id)
        count, _ = self._failures.get(source_id, (0, 0.0))
        self._failures[source_id] = (count + 1, time.time())
        if cooldown_seconds > 0:
            snapshot.cooldown_until = max(
                snapshot.cooldown_until or 0.0, time.time() + cooldown_seconds
            )
        snapshot.updated_at = time.time()

    def order_profiles(
        self,
        profiles: list[tuple[str, str]],
        *,
        estimated_input_tokens: int = 0,
    ) -> list[str]:
        """Order profiles by observed remaining capacity with stable ties."""

        scored: list[tuple[float, int, str]] = []
        for index, (profile_name, source_id) in enumerate(profiles):
            snapshot = self._snapshots.get(source_id)
            if snapshot is None:
                score = 0.5
                available = True
            else:
                score = snapshot.remaining_score(self.utilization_ceiling)
                available = snapshot.available(
                    estimated_input_tokens=estimated_input_tokens,
                    utilization_ceiling=self.utilization_ceiling,
                )
            if available:
                scored.append((-score, index, profile_name))
        return [name for _score, _index, name in sorted(scored)]


class GeminiCatalogClient:
    """Bounded model-catalog probe; it never sends portfolio content."""

    def __init__(
        self, *, api_key: str, base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def list_models(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{self._base_url}/models",
                headers={"x-goog-api-key": self._api_key},
            )
            response.raise_for_status()
            payload = response.json()
        values = payload.get("models", []) if isinstance(payload, dict) else []
        return [dict(item) for item in values if isinstance(item, dict)]


class ExperientialUsageClient:
    """Read-only Experiential usage/limits surfaces."""

    def __init__(
        self, *, api_key: str, management_base_url: str = "https://platform.experientiallabs.ai"
    ) -> None:
        self._api_key = api_key
        self._base_url = management_base_url.rstrip("/")

    async def get_usage_events(self, org_id: str = "") -> dict[str, Any]:
        params = {"org_id": org_id} if org_id else {}
        return await self._get("/api/gateway/usage/events", params=params)

    async def get_daily_usage(
        self, org_id: str = "", group_by: str = "day_model"
    ) -> dict[str, Any]:
        params = {"group_by": group_by}
        if org_id:
            params["org_id"] = org_id
        return await self._get("/api/gateway/usage/daily", params=params)

    async def get_key_limits(self, api_key_id: str) -> dict[str, Any]:
        return await self._get(f"/api/gateway/keys/{api_key_id}/limits")

    async def _get(self, path: str, *, params: dict[str, str] | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{self._base_url}{path}",
                headers={"authorization": f"Bearer {self._api_key}"},
                params=params,
            )
            response.raise_for_status()
            payload = response.json()
        return dict(payload) if isinstance(payload, dict) else {}


class ModelUsageReconciler:
    """Single-worker, read-only provider observation reconciler.

    Provider APIs are queried for telemetry and capability observations only;
    no prompt or model output is ever sent.  PostgreSQL's advisory lock keeps
    multiple workers from importing the same window concurrently.
    """

    def __init__(
        self, *, sessionmaker: Any, model_config: Any, capacity_registry: CapacityRegistry
    ):
        self._sessionmaker = sessionmaker
        self._config = model_config
        self._registry = capacity_registry

    async def reconcile(self) -> dict[str, int]:
        from sqlalchemy import text

        async with self._sessionmaker() as db:
            lock = await db.execute(
                text("SELECT pg_try_advisory_lock(hashtext('oryxenai:model-usage-reconcile'))")
            )
            acquired = bool(lock.scalar())
            if not acquired:
                return {"observations": 0, "sources": 0}
            observations = 0
            sources = 0
            try:
                for source_id, source in self._config.routing.capacity.sources.items():
                    if not source.enabled:
                        continue
                    api_key = os.environ.get(source.api_key_env, "")
                    if not api_key:
                        continue
                    sources += 1
                    try:
                        if source.provider.casefold() == "experiential":
                            payload = await ExperientialUsageClient(
                                api_key=api_key
                            ).get_daily_usage()
                            await self._store_observation(
                                db,
                                provider="experiential",
                                source_id=source_id,
                                kind="usage_daily",
                                payload=payload,
                            )
                            observations += 1
                        elif source.provider.casefold() == "gemini":
                            models = await GeminiCatalogClient(api_key=api_key).list_models()
                            await self._store_observation(
                                db,
                                provider="gemini",
                                source_id=source_id,
                                kind="catalog",
                                payload={
                                    "models": [
                                        {
                                            "name": item.get("name"),
                                            "supported_generation_methods": item.get(
                                                "supportedGenerationMethods", []
                                            ),
                                            "input_token_limit": item.get("inputTokenLimit"),
                                            "output_token_limit": item.get("outputTokenLimit"),
                                        }
                                        for item in models
                                    ]
                                },
                            )
                            observations += 1
                    except Exception as exc:
                        # Provider observation failures must not stop model
                        # work; the last known capacity remains in place.
                        logger.debug(
                            "provider observation unavailable error=%s", type(exc).__name__
                        )
                        continue
                await db.commit()
            finally:
                await db.execute(
                    text("SELECT pg_advisory_unlock(hashtext('oryxenai:model-usage-reconcile'))")
                )
                await db.commit()
            return {"observations": observations, "sources": sources}

    async def _store_observation(
        self,
        db: Any,
        *,
        provider: str,
        source_id: str,
        kind: str,
        payload: dict[str, Any],
    ) -> None:
        from oryxenai.db.models.model_usage import ModelProviderObservation

        # Keep only response metadata and cap the JSON payload so a provider
        # catalog/usage response cannot become an unbounded application log.
        bounded = dict(payload)
        db.add(
            ModelProviderObservation(
                provider=provider,
                capacity_source_id=source_id,
                observation_kind=kind,
                external_id="",
                observed_at=datetime.now(UTC),
                payload=bounded,
            )
        )
