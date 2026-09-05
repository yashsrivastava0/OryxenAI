"""Provider-neutral structured model-result caching and cost telemetry.

The cache sits after provider JSON decoding but before agent-specific business
validation.  Callers provide that validator, so a malformed provider response
is never persisted and every cache hit is checked by the same contract as a
fresh response.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import time
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from oryxenai.agents.shared.contracts import ModelClient
from oryxenai.db.models.model_call_cache import ModelCallCache

MODEL_CACHE_VERSION = "structured-model-result-v1"
DEFAULT_RESULT_CACHE_TTL_SECONDS = 30 * 24 * 60 * 60
DEFAULT_RESULT_CACHE_LEASE_SECONDS = 15 * 60
DEFAULT_RESULT_CACHE_WAIT_SECONDS = 60.0
DEFAULT_PROMPT_CACHE_TTL = "30m"

Validator = Callable[[dict[str, Any]], None]
Compute = Callable[[], Awaitable[Any]]


def _canonical(value: Any) -> Any:
    """Convert JSON-like values into stable, JSON-serializable data."""

    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if hasattr(value, "model_dump"):
        return _canonical(value.model_dump(mode="json"))
    if hasattr(value, "value") and not isinstance(value, (str, bytes, int, float, bool)):
        return _canonical(value.value)
    return value


def canonical_json(value: Any) -> str:
    """Return the canonical JSON representation used by cache fingerprints."""

    return json.dumps(
        _canonical(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def prompt_manifest_fingerprint(manifest: Mapping[str, str]) -> str:
    """Fingerprint a prompt manifest without putting its contents in a key."""

    return sha256_hex(dict(manifest))[:32]


def prompt_cache_context(
    agent_key: str,
    operation: str,
    manifest: Mapping[str, str],
) -> dict[str, Any]:
    """Build a stable provider-prefix-cache hint for one prompt contract.

    The key intentionally excludes owner/session/run identifiers.  Only the
    stable trusted prefix is marked for provider caching; the dynamic payload
    follows it in a separate message and is never selected as the explicit
    cache breakpoint.
    """

    fingerprint = prompt_manifest_fingerprint(manifest)
    return {
        "prompt_cache_key": f"oryxenai:{agent_key}:{operation}:{fingerprint}",
        "prompt_cache_mode": "explicit",
        "prompt_cache_breakpoint": True,
        "prompt_cache_ttl": DEFAULT_PROMPT_CACHE_TTL,
    }


def estimate_model_cost(usage: Mapping[str, Any], pricing: Any) -> float | None:
    """Estimate configured billing units from normalized token usage.

    The rate card is configuration, not business logic.  Returning ``None``
    when a profile has no complete rate card is deliberate: token and
    character telemetry remains useful without pretending to know a price.
    """

    if pricing is None:
        return None
    values = pricing.model_dump(mode="json") if hasattr(pricing, "model_dump") else dict(pricing)
    rates = {
        key: values.get(key)
        for key in (
            "input_per_million",
            "cached_input_per_million",
            "cache_write_per_million",
            "output_per_million",
        )
    }
    if any(not isinstance(value, (int, float)) for value in rates.values()):
        return None
    input_rate = float(cast(int | float, rates["input_per_million"]))
    cached_input_rate = float(cast(int | float, rates["cached_input_per_million"]))
    cache_write_rate = float(cast(int | float, rates["cache_write_per_million"]))
    output_rate = float(cast(int | float, rates["output_per_million"]))

    prompt_tokens = max(0, int(usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0))
    cached_tokens = max(
        0,
        int(
            usage.get(
                "cached_prompt_tokens",
                usage.get("cache_read_input_tokens", 0),
            )
            or 0
        ),
    )
    cache_write_tokens = max(
        0,
        int(
            usage.get(
                "cache_write_tokens",
                usage.get("cache_creation_input_tokens", 0),
            )
            or 0
        ),
    )
    uncached_tokens = max(0, prompt_tokens - cached_tokens - cache_write_tokens)
    output_tokens = max(0, int(usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0))
    return (
        uncached_tokens * input_rate
        + cached_tokens * cached_input_rate
        + cache_write_tokens * cache_write_rate
        + output_tokens * output_rate
    ) / 1_000_000.0


class StructuredResultCache:
    """Durable, scoped cache for validated structured model calls."""

    def __init__(
        self,
        sessionmaker: Any,
        *,
        owner_user_id: UUID | None,
        portfolio_session_id: UUID,
        enabled: bool = True,
        ttl_seconds: int = DEFAULT_RESULT_CACHE_TTL_SECONDS,
        lease_seconds: int = int(DEFAULT_RESULT_CACHE_LEASE_SECONDS),
        wait_seconds: float = DEFAULT_RESULT_CACHE_WAIT_SECONDS,
    ) -> None:
        if owner_user_id is None and portfolio_session_id is None:
            raise ValueError("A result cache requires an owner or portfolio session scope")
        self._sessionmaker = sessionmaker
        self._owner_user_id = owner_user_id
        self._portfolio_session_id = None if owner_user_id is not None else portfolio_session_id
        self._enabled = bool(enabled)
        self._ttl_seconds = max(1, int(ttl_seconds))
        self._lease_seconds = max(1, int(lease_seconds))
        self._wait_seconds = max(0.0, float(wait_seconds))

    @property
    def scope(self) -> str:
        return "owner" if self._owner_user_id is not None else "session"

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def generate(
        self,
        *,
        client: ModelClient,
        agent_key: str,
        operation: str,
        system_prompt: str,
        instructions: str,
        input_payload: Mapping[str, object],
        output_model: type[Any],
        model_profile: str,
        profile_fingerprint: str,
        request_context: Mapping[str, Any] | None,
        strict_schema: bool,
        validator: Validator,
        compute: Compute | None = None,
    ) -> Any:
        """Return a fresh or cached validated ``StructuredModelResult``."""

        if compute is None:

            async def compute_default() -> Any:
                return await client.generate_structured(
                    operation=operation,
                    system_prompt=system_prompt,
                    instructions=instructions,
                    input_payload=input_payload,
                    output_model=output_model,
                    model_profile=model_profile,
                    request_context=request_context,
                    strict_schema=strict_schema,
                )

            compute = compute_default

        cache_key, prompt_fingerprint, input_fingerprint = build_model_call_key(
            agent_key=agent_key,
            operation=operation,
            system_prompt=system_prompt,
            instructions=instructions,
            input_payload=input_payload,
            output_model=output_model,
            model_profile=model_profile,
            profile_fingerprint=profile_fingerprint,
            request_context=request_context,
            strict_schema=strict_schema,
        )

        if not self._enabled:
            result = await compute()
            validator(dict(result.parsed_output))
            return _with_cache_metadata(
                result,
                {
                    "enabled": False,
                    "cache_hit": False,
                    "cache_key": cache_key,
                    "scope": self.scope,
                },
            )

        deadline = time.monotonic() + self._wait_seconds
        lease_token: str | None = None
        cache_entry: ModelCallCache | None = None
        while lease_token is None:
            action, cache_entry, lease_token = await self._claim_or_wait(
                cache_key=cache_key,
                agent_key=agent_key,
                operation=operation,
                prompt_fingerprint=prompt_fingerprint,
                input_fingerprint=input_fingerprint,
                profile_fingerprint=profile_fingerprint,
            )
            if action == "hit" and cache_entry is not None:
                cached_payload = dict(cache_entry.output_payload or {})
                try:
                    validator(copy.deepcopy(cached_payload))
                except Exception:
                    await self._invalidate(cache_key)
                    continue
                return _result_from_cache(
                    cache_entry, cache_key, input_payload, instructions, system_prompt
                )
            if action == "owner":
                break
            if time.monotonic() >= deadline:
                result = await compute()
                validator(dict(result.parsed_output))
                return _with_cache_metadata(
                    result,
                    {
                        "enabled": True,
                        "cache_hit": False,
                        "cache_key": cache_key,
                        "scope": self.scope,
                        "wait_timeout": True,
                        "stored": False,
                    },
                )
            await asyncio.sleep(0.25)

        assert lease_token is not None
        try:
            result = await compute()
            validator(dict(result.parsed_output))
        except BaseException:
            await self._release(cache_key, lease_token)
            raise

        stored = await self._store(
            cache_key=cache_key,
            lease_token=lease_token,
            result=result,
            agent_key=agent_key,
            operation=operation,
            prompt_fingerprint=prompt_fingerprint,
            input_fingerprint=input_fingerprint,
            profile_fingerprint=profile_fingerprint,
        )
        return _with_cache_metadata(
            result,
            {
                "enabled": True,
                "cache_hit": False,
                "cache_key": cache_key,
                "scope": self.scope,
                "stored": stored,
            },
        )

    async def _claim_or_wait(
        self,
        *,
        cache_key: str,
        agent_key: str,
        operation: str,
        prompt_fingerprint: str,
        input_fingerprint: str,
        profile_fingerprint: str,
    ) -> tuple[str, ModelCallCache | None, str | None]:
        now = datetime.now(UTC)
        async with self._sessionmaker() as db:
            result = await db.execute(
                select(ModelCallCache)
                .where(self._scope_filter(), ModelCallCache.cache_key == cache_key)
                .with_for_update()
            )
            entry = result.scalar_one_or_none()
            if (
                entry is not None
                and entry.status == "ready"
                and entry.agent_key == agent_key
                and entry.operation == operation
                and entry.prompt_fingerprint == prompt_fingerprint
                and entry.input_fingerprint == input_fingerprint
                and entry.profile_fingerprint == profile_fingerprint
                and entry.expires_at > now
            ):
                entry.last_hit_at = now
                entry.hit_count += 1
                await db.commit()
                return "hit", entry, None
            if (
                entry is not None
                and entry.status == "producing"
                and entry.lease_until is not None
                and entry.lease_until > now
            ):
                await db.commit()
                return "wait", None, None

            token = uuid4().hex
            lease_until = now + timedelta(seconds=self._lease_seconds)
            if entry is None:
                entry = ModelCallCache(
                    owner_user_id=self._owner_user_id,
                    portfolio_session_id=self._portfolio_session_id,
                    agent_key=agent_key,
                    operation=operation,
                    cache_key=cache_key,
                    prompt_fingerprint=prompt_fingerprint,
                    input_fingerprint=input_fingerprint,
                    profile_fingerprint=profile_fingerprint,
                    status="producing",
                    provider_metadata={},
                    lease_token=token,
                    lease_until=lease_until,
                    created_at=now,
                    expires_at=now + timedelta(seconds=self._ttl_seconds),
                )
                db.add(entry)
                try:
                    await db.flush()
                except IntegrityError:
                    await db.rollback()
                    return "wait", None, None
            else:
                entry.status = "producing"
                entry.output_payload = None
                entry.provider_metadata = {}
                entry.lease_token = token
                entry.lease_until = lease_until
                entry.agent_key = agent_key
                entry.operation = operation
                entry.prompt_fingerprint = prompt_fingerprint
                entry.input_fingerprint = input_fingerprint
                entry.profile_fingerprint = profile_fingerprint
                entry.expires_at = now + timedelta(seconds=self._ttl_seconds)
            await db.commit()
            return "owner", None, token

    async def _store(
        self,
        *,
        cache_key: str,
        lease_token: str,
        result: Any,
        agent_key: str,
        operation: str,
        prompt_fingerprint: str,
        input_fingerprint: str,
        profile_fingerprint: str,
    ) -> bool:
        now = datetime.now(UTC)
        provider_metadata = {
            "model": str(getattr(result, "model", "") or ""),
            "usage": dict(getattr(result, "usage", {}) or {}),
            "finish_reason": str(getattr(result, "finish_reason", "") or ""),
            "latency_ms": float(getattr(result, "latency_ms", 0.0) or 0.0),
            "telemetry": dict(getattr(result, "telemetry", {}) or {}),
        }
        async with self._sessionmaker() as db:
            statement = (
                update(ModelCallCache)
                .where(
                    self._scope_filter(),
                    ModelCallCache.cache_key == cache_key,
                    ModelCallCache.status == "producing",
                    ModelCallCache.lease_token == lease_token,
                )
                .values(
                    agent_key=agent_key,
                    operation=operation,
                    prompt_fingerprint=prompt_fingerprint,
                    input_fingerprint=input_fingerprint,
                    profile_fingerprint=profile_fingerprint,
                    status="ready",
                    output_payload=dict(result.parsed_output),
                    provider_metadata=provider_metadata,
                    lease_token=None,
                    lease_until=None,
                    expires_at=now + timedelta(seconds=self._ttl_seconds),
                )
            )
            updated = await db.execute(statement)
            await db.commit()
            return bool(updated.rowcount)

    async def _release(self, cache_key: str, lease_token: str) -> None:
        async with self._sessionmaker() as db:
            await db.execute(
                delete(ModelCallCache).where(
                    self._scope_filter(),
                    ModelCallCache.cache_key == cache_key,
                    ModelCallCache.status == "producing",
                    ModelCallCache.lease_token == lease_token,
                )
            )
            await db.commit()

    async def _invalidate(self, cache_key: str) -> None:
        async with self._sessionmaker() as db:
            await db.execute(
                delete(ModelCallCache).where(
                    self._scope_filter(),
                    ModelCallCache.cache_key == cache_key,
                    ModelCallCache.status == "ready",
                )
            )
            await db.commit()

    def _scope_filter(self) -> Any:
        if self._owner_user_id is not None:
            return ModelCallCache.owner_user_id == self._owner_user_id
        return ModelCallCache.portfolio_session_id == self._portfolio_session_id


def build_model_call_key(
    *,
    agent_key: str,
    operation: str,
    system_prompt: str,
    instructions: str,
    input_payload: Mapping[str, object],
    output_model: type[Any],
    model_profile: str,
    profile_fingerprint: str,
    request_context: Mapping[str, Any] | None,
    strict_schema: bool,
) -> tuple[str, str, str]:
    """Build the cache key and the component fingerprints used for auditing."""

    schema = output_model.model_json_schema()
    prompt_material = {
        "system_prompt": system_prompt,
        "instructions": instructions,
        "schema": schema,
        "strict_schema": strict_schema,
    }
    input_material = {
        "input_payload": input_payload,
        "key_order": (
            request_context.get("key_order") if isinstance(request_context, Mapping) else None
        ),
    }
    prompt_fingerprint = sha256_hex(prompt_material)
    input_fingerprint = sha256_hex(input_material)
    key_material = {
        "cache_version": MODEL_CACHE_VERSION,
        "agent_key": agent_key,
        "operation": operation,
        "prompt_fingerprint": prompt_fingerprint,
        "input_fingerprint": input_fingerprint,
        "model_profile": model_profile,
        "profile_fingerprint": profile_fingerprint,
    }
    return sha256_hex(key_material), prompt_fingerprint, input_fingerprint


def _with_cache_metadata(result: Any, metadata: dict[str, Any]) -> Any:
    current = dict(getattr(result, "cache_metadata", {}) or {})
    current.update(metadata)
    return result.model_copy(update={"cache_metadata": current})


def _result_from_cache(
    entry: ModelCallCache,
    cache_key: str,
    input_payload: Mapping[str, object],
    instructions: str,
    system_prompt: str,
) -> Any:
    from oryxenai.agents.discovery.schemas import StructuredModelResult

    metadata = dict(entry.provider_metadata or {})
    raw_usage = metadata.get("usage")
    raw_telemetry = metadata.get("telemetry")
    saved_usage = dict(raw_usage) if isinstance(raw_usage, Mapping) else {}
    saved_telemetry = dict(raw_telemetry) if isinstance(raw_telemetry, Mapping) else {}
    current_input_chars = (
        len(system_prompt) + len(instructions) + len(canonical_json(input_payload))
    )
    current_telemetry: dict[str, Any] = {
        "input_characters": current_input_chars,
        "output_characters": int(saved_telemetry.get("output_characters", 0) or 0),
        "charged_input_characters": 0,
        "charged_output_characters": 0,
        "estimated_cost": 0.0,
    }
    if saved_telemetry.get("cost_unit"):
        current_telemetry["cost_unit"] = saved_telemetry["cost_unit"]
    cache_metadata = {
        "enabled": True,
        "cache_hit": True,
        "cache_key": cache_key,
        "scope": "owner" if entry.owner_user_id is not None else "session",
        "cache_age_seconds": max(0.0, (datetime.now(UTC) - entry.created_at).total_seconds()),
        "saved_usage": saved_usage,
        "saved_telemetry": saved_telemetry,
        "avoided_input_characters": int(saved_telemetry.get("input_characters", 0) or 0),
        "avoided_output_characters": int(saved_telemetry.get("output_characters", 0) or 0),
        "avoided_cost": saved_telemetry.get("estimated_cost", 0.0),
        "cost_unit": saved_telemetry.get("cost_unit", ""),
    }
    return StructuredModelResult(
        parsed_output=copy.deepcopy(dict(entry.output_payload or {})),
        response_id=None,
        model=str(metadata.get("model", "") or ""),
        usage={},
        finish_reason=str(metadata.get("finish_reason", "") or ""),
        latency_ms=0.0,
        telemetry=current_telemetry,
        cache_metadata=cache_metadata,
    )


async def generate_with_cache(
    *,
    client: ModelClient,
    result_cache: StructuredResultCache | None,
    agent_key: str,
    operation: str,
    system_prompt: str,
    instructions: str,
    input_payload: Mapping[str, object],
    output_model: type[Any],
    model_profile: str,
    profile_fingerprint: str,
    request_context: Mapping[str, Any] | None,
    strict_schema: bool,
    validator: Validator,
) -> Any:
    """Generate once, or use the durable cache while preserving validation.

    The same validator runs after a provider response and after a cache hit.
    This keeps the cache an optimization layer rather than a second source of
    truth for agent contracts.
    """

    if result_cache is None:
        result = await client.generate_structured(
            operation=operation,
            system_prompt=system_prompt,
            instructions=instructions,
            input_payload=input_payload,
            output_model=output_model,
            model_profile=model_profile,
            request_context=request_context,
            strict_schema=strict_schema,
        )
        validator(dict(result.parsed_output))
        return result

    return await result_cache.generate(
        client=client,
        agent_key=agent_key,
        operation=operation,
        system_prompt=system_prompt,
        instructions=instructions,
        input_payload=input_payload,
        output_model=output_model,
        model_profile=model_profile,
        profile_fingerprint=profile_fingerprint,
        request_context=request_context,
        strict_schema=strict_schema,
        validator=validator,
    )


def build_result_cache(
    settings: Any,
    *,
    owner_user_id: UUID | None,
    portfolio_session_id: UUID,
) -> StructuredResultCache:
    """Build a cache instance using committed app policy and DB wiring."""

    from oryxenai.db.session import get_sessionmaker

    config = settings.model_cache
    return StructuredResultCache(
        get_sessionmaker(settings),
        owner_user_id=owner_user_id,
        portfolio_session_id=portfolio_session_id,
        enabled=config.enabled,
        ttl_seconds=config.ttl_seconds,
        lease_seconds=config.lease_seconds,
        wait_seconds=config.wait_seconds,
    )
