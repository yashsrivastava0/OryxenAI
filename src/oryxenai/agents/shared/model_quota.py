"""Quota-aware capacity observation and deterministic source selection."""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Iterable, Mapping
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
        previous = self._snapshots.get(snapshot.source_id)
        if previous is not None:
            # Provider reconciliation is a read-only observation and may not
            # know about in-flight reservations made by this process. Keep
            # those reservations (and any active cooldown) when replacing the
            # observed counters, otherwise a refresh could make the selector
            # dispatch an unaccounted duplicate.
            snapshot.reserved_requests = max(
                int(snapshot.reserved_requests), int(previous.reserved_requests)
            )
            snapshot.reserved_input_tokens = max(
                int(snapshot.reserved_input_tokens), int(previous.reserved_input_tokens)
            )
            if previous.cooldown_until is not None:
                snapshot.cooldown_until = max(
                    float(snapshot.cooldown_until or 0.0), float(previous.cooldown_until)
                )
            if snapshot.reset_at is None:
                snapshot.reset_at = previous.reset_at
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
                            client = ExperientialUsageClient(api_key=api_key)
                            provider_payloads: list[dict[str, Any]] = []
                            # Usage events carry request identity, actual/free
                            # consumption, and gateway attempt counts.  Daily
                            # usage is retained separately because it is a
                            # summary rather than a replacement for events.
                            for kind, loader in (
                                ("usage_events", client.get_usage_events),
                                ("usage_daily", client.get_daily_usage),
                            ):
                                try:
                                    payload = await loader()
                                except Exception as exc:
                                    logger.debug(
                                        "experiential observation unavailable kind=%s error=%s",
                                        kind,
                                        type(exc).__name__,
                                    )
                                    continue
                                provider_payloads.append(payload)
                                await self._store_observation(
                                    db,
                                    provider="experiential",
                                    source_id=source_id,
                                    kind=kind,
                                    payload=payload,
                                )
                                observations += 1
                            # A key-limit request is made only when the
                            # provider supplies a non-secret key identifier in
                            # an observation.  Never guess an ID from the API
                            # key itself or from an account email.
                            # Only an explicitly named key identifier is safe
                            # to pass to the key-limits endpoint.  Event IDs,
                            # request IDs, and organization IDs are useful
                            # observation cursors but are not API-key IDs.
                            key_id = _extract_key_identifier(provider_payloads)
                            if key_id:
                                try:
                                    limits = await client.get_key_limits(key_id)
                                except Exception as exc:
                                    logger.debug(
                                        "experiential key limits unavailable error=%s",
                                        type(exc).__name__,
                                    )
                                else:
                                    provider_payloads.append(limits)
                                    await self._store_observation(
                                        db,
                                        provider="experiential",
                                        source_id=source_id,
                                        kind="key_limits",
                                        payload=limits,
                                    )
                                    observations += 1
                            self._observe_capacity(
                                provider="experiential",
                                source_id=source_id,
                                models=_models_for_source(self._config, source_id),
                                payloads=provider_payloads,
                            )
                        elif source.provider.casefold() == "gemini":
                            models = await GeminiCatalogClient(api_key=api_key).list_models()
                            catalog_payload = {
                                "models": [
                                    {
                                        "name": item.get("name"),
                                        "supported_generation_methods": item.get(
                                            "supportedGenerationMethods", []
                                        ),
                                        # These are model context/output
                                        # capabilities, not RPM/TPM/RPD.
                                        # Keep them in the observation but do
                                        # not promote them to quota limits.
                                        "input_token_limit": item.get("inputTokenLimit"),
                                        "output_token_limit": item.get("outputTokenLimit"),
                                    }
                                    for item in models
                                ]
                            }
                            await self._store_observation(
                                db,
                                provider="gemini",
                                source_id=source_id,
                                kind="catalog",
                                payload=catalog_payload,
                            )
                            observations += 1
                            # Gemini's model catalog does not publish project
                            # RPM/TPM/RPD.  Keep the capacity snapshot unknown
                            # until a quota response or a configured provider
                            # observation supplies an explicit limit; never
                            # reintroduce dated hardcoded free-tier numbers.
                            self._observe_capacity(
                                provider="gemini",
                                source_id=source_id,
                                models=_models_for_source(self._config, source_id),
                                payloads=[],
                            )
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
        bounded = _bounded_metadata(payload)
        external_id = _extract_external_identifier([bounded]) or ""
        if not external_id and kind in {"catalog", "usage_daily", "key_limits"}:
            # Summary/catalog responses often have no provider cursor.  A
            # bounded-content fingerprint prevents the reconciler from
            # inserting an identical row on every refresh while still
            # retaining a new observation whenever the provider changes it.
            material = json.dumps(bounded, ensure_ascii=False, sort_keys=True, default=str)
            external_id = hashlib.sha256(material.encode("utf-8")).hexdigest()[:64]
        if external_id:
            from sqlalchemy import select

            existing = await db.execute(
                select(ModelProviderObservation.id).where(
                    ModelProviderObservation.provider == provider,
                    ModelProviderObservation.capacity_source_id == source_id,
                    ModelProviderObservation.observation_kind == kind,
                    ModelProviderObservation.external_id == external_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                return
        db.add(
            ModelProviderObservation(
                provider=provider,
                capacity_source_id=source_id,
                observation_kind=kind,
                external_id=external_id,
                observed_at=datetime.now(UTC),
                payload=bounded,
            )
        )

    def _observe_capacity(
        self,
        *,
        provider: str,
        source_id: str,
        models: list[str],
        payloads: Iterable[Mapping[str, Any]],
    ) -> None:
        """Mirror only explicitly reported limits/usage into the selector.

        A missing provider limit remains ``None``.  In particular, Gemini's
        model context window is never mistaken for a project RPM/TPM/RPD
        quota, and dated dashboard observations are not baked into code.
        """

        payload_list = [dict(payload) for payload in payloads if isinstance(payload, Mapping)]
        limits = _extract_capacity_limits(payload_list)
        usage = _extract_usage_totals(payload_list)
        reset_at = _extract_reset_at(payload_list)
        selected_model = models[0] if models else ""
        confidence = "observed" if limits or usage or reset_at is not None else "unknown"
        snapshot = CapacitySnapshot(
            provider=provider,
            source_id=source_id,
            model=selected_model,
            request_limit=limits.get("request_limit"),
            input_token_limit=limits.get("input_token_limit"),
            daily_request_limit=limits.get("daily_request_limit"),
            observed_requests=usage.get("requests", 0),
            observed_input_tokens=usage.get("input_tokens", 0),
            reset_at=reset_at,
            confidence=confidence,
        )
        self._registry.observe(snapshot)


_SENSITIVE_METADATA_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "access_token",
        "refresh_token",
        "client_secret",
        "secret_key",
        "password",
        "prompt",
        "input",
        "output",
        "content",
        "body",
    }
)


def _bounded_metadata(value: Any, *, depth: int = 0) -> Any:
    """Redact credentials/prompts and bound provider observation JSON."""

    if depth > 5:
        return "…"
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for raw_key, raw_value in list(value.items())[:100]:
            key = str(raw_key)
            if key.casefold() in _SENSITIVE_METADATA_KEYS:
                continue
            result[key] = _bounded_metadata(raw_value, depth=depth + 1)
        return result
    if isinstance(value, list):
        return [_bounded_metadata(item, depth=depth + 1) for item in value[:100]]
    if isinstance(value, tuple):
        return [_bounded_metadata(item, depth=depth + 1) for item in value[:100]]
    if isinstance(value, str):
        return value[:2000]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:2000]


def _models_for_source(config: Any, source_id: str) -> list[str]:
    models: list[str] = []
    for profile in getattr(config, "profiles", {}).values():
        if str(getattr(profile, "capacity_source_id", "") or "") != source_id:
            continue
        model = str(getattr(profile, "model", "") or "")
        if model and model not in models:
            models.append(model)
    return models


def _records(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    records: list[Mapping[str, Any]] = [payload]
    for key in (
        "events",
        "data",
        "items",
        "results",
        "usage",
        "daily",
        "rows",
        "limits",
        "limit",
        "quotas",
        "quota",
        "rate_limits",
        "rateLimits",
        "rate_limit",
    ):
        value = payload.get(key)
        if isinstance(value, list):
            records.extend(item for item in value if isinstance(item, Mapping))
        elif isinstance(value, Mapping):
            records.append(value)
    return records


def _number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float) and value.is_integer() and value >= 0:
        return int(value)
    if isinstance(value, str):
        try:
            parsed = int(float(value.strip()))
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None
    return None


def _first_number(records: Iterable[Mapping[str, Any]], keys: set[str]) -> int | None:
    for record in records:
        for raw_key, raw_value in record.items():
            if str(raw_key).casefold().replace("-", "_") in keys:
                value = _number(raw_value)
                if value is not None:
                    return value
    return None


def _extract_capacity_limits(payloads: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    records = [record for payload in payloads for record in _records(payload)]
    result: dict[str, int] = {}
    aliases = {
        "request_limit": {
            "rpm",
            "requests_per_minute",
            "request_limit",
            "requests_limit",
            "rate_limit_rpm",
            "requestsperminute",
        },
        "input_token_limit": {
            "tpm",
            "tokens_per_minute",
            "input_token_limit",
            "input_tokens_per_minute",
            "rate_limit_tpm",
        },
        "daily_request_limit": {
            "rpd",
            "requests_per_day",
            "daily_request_limit",
            "daily_requests",
            "rate_limit_rpd",
        },
    }
    for target, keys in aliases.items():
        value = _first_number(records, keys)
        if value is not None and value > 0:
            result[target] = value
    return result


def _extract_usage_totals(payloads: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    payload_list = [dict(payload) for payload in payloads if isinstance(payload, Mapping)]
    records = [record for payload in payload_list for record in _records(payload)]
    request_keys = {
        "requests",
        "request_count",
        "requests_used",
        "total_requests",
        "inference_count",
    }
    token_keys = {
        "input_tokens",
        "input_token_count",
        "prompt_tokens",
        "prompt_token_count",
        "tokens_in",
    }

    def direct_total(keys: set[str]) -> int | None:
        for payload in payload_list:
            for raw_key, raw_value in payload.items():
                if str(raw_key).casefold().replace("-", "_") in keys:
                    parsed = _number(raw_value)
                    if parsed is not None:
                        return parsed
        return None

    requests = direct_total(request_keys)
    input_tokens = direct_total(token_keys)
    # Event streams are often arrays. Sum per-event values only when the
    # response did not provide a summary, avoiding double counting a daily
    # summary alongside its event rows.
    if requests is None:
        requests = sum(
            _first_number([item], request_keys) or 0
            for item in records
            if isinstance(item, Mapping)
        )
    if input_tokens is None:
        input_tokens = sum(
            _first_number([item], token_keys) or 0
            for item in records
            if isinstance(item, Mapping)
        )
    return {"requests": max(0, requests or 0), "input_tokens": max(0, input_tokens or 0)}


def _extract_reset_at(payloads: Iterable[Mapping[str, Any]]) -> float | None:
    keys = {"reset_at", "resetat", "resets_at", "reset_time", "window_end", "period_end"}
    for payload in payloads:
        for record in _records(payload):
            for raw_key, raw_value in record.items():
                if str(raw_key).casefold().replace("-", "_") not in keys:
                    continue
                if isinstance(raw_value, (int, float)) and raw_value >= 0:
                    return float(raw_value)
                if isinstance(raw_value, str):
                    try:
                        return datetime.fromisoformat(raw_value.replace("Z", "+00:00")).timestamp()
                    except ValueError:
                        continue
    return None


def _extract_external_identifier(payloads: Iterable[Mapping[str, Any]]) -> str:
    keys = {"event_id", "id", "request_id", "requestid", "api_key_id", "key_id"}
    for payload in payloads:
        for record in _records(payload):
            for raw_key, raw_value in record.items():
                if str(raw_key).casefold().replace("-", "_") not in keys:
                    continue
                if isinstance(raw_value, (str, int)) and str(raw_value):
                    return str(raw_value)[:200]
    return ""


def _extract_key_identifier(payloads: Iterable[Mapping[str, Any]]) -> str:
    """Find only an explicit provider API-key identifier.

    The usage/events and usage/daily responses can contain generic ``id`` or
    request identifiers.  Treating one of those as a key ID would issue a
    misleading limits request, so this helper intentionally accepts only
    unambiguous key-field spellings.
    """

    keys = {"api_key_id", "apikey_id", "key_id", "keyid"}
    for payload in payloads:
        for record in _records(payload):
            for raw_key, raw_value in record.items():
                if str(raw_key).casefold().replace("-", "_") not in keys:
                    continue
                if isinstance(raw_value, (str, int)) and str(raw_value):
                    return str(raw_value)[:200]
    return ""
