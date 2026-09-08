"""Durable model-call attribution and provider usage reconciliation helpers."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from oryxenai.agents.shared.contracts import ModelCallContext, ResolvedModelRoute
from oryxenai.agents.shared.providers.errors import (
    ModelCapacityUnavailableError,
    ModelUsagePersistenceError,
    ProviderError,
    ProviderTimeoutError,
)
from oryxenai.core.logging import get_logger

logger = get_logger("oryxenai.agents.model_usage")


class UsageTrackingModelClient:
    """Instrument a concrete profile for callers outside RoutedModelClient."""

    def __init__(self, client: Any, route: ResolvedModelRoute, ledger: ModelUsageLedger) -> None:
        self._client = client
        self._route = route
        self._ledger = ledger

    async def complete(
        self, system_prompt: str, task_prompt: str, request_params: dict[str, Any] | None = None
    ) -> str:
        context = context_from_request(
            engine="",
            operation="complete",
            request_context=request_params,
            input_classification="unknown",
        )
        context.metadata.setdefault(
            "operation_id",
            str(request_params.get("operation_id", "") if request_params else "")
            or f"direct:{self._route.profile_name}:complete:{uuid4().hex}",
        )
        context.metadata.setdefault("normal_calls", 1)
        context.metadata.setdefault("recovery_allowance", 0)
        attempt_id = await self._ledger.reserve(
            route=self._route,
            context=context,
            attempt_kind="normal",
            request_attempt=1,
            fallback_attempt=0,
        )
        started = time.monotonic()
        try:
            value = await self._client.complete(system_prompt, task_prompt, request_params)
        except BaseException as exc:
            await self._ledger.finish(
                attempt_id,
                route=self._route,
                context=context,
                error=exc,
                elapsed_ms=(time.monotonic() - started) * 1000.0,
            )
            raise
        await self._ledger.finish(
            attempt_id,
            route=self._route,
            context=context,
            elapsed_ms=(time.monotonic() - started) * 1000.0,
        )
        return str(value)

    async def generate_structured(self, **kwargs: Any) -> Any:
        context = context_from_request(
            engine="",
            operation=str(kwargs.get("operation", "")),
            request_context=kwargs.get("request_context"),
            input_classification="unknown",
        )
        raw_context = kwargs.get("request_context")
        if isinstance(raw_context, Mapping) and raw_context.get("operation_id"):
            operation_id = str(raw_context["operation_id"])
        else:
            operation_id = f"direct:{self._route.profile_name}:{context.operation}:{uuid4().hex}"
        context.metadata.setdefault("operation_id", operation_id)
        context.metadata.setdefault("normal_calls", 1)
        context.metadata.setdefault("recovery_allowance", 0)
        attempt_id = await self._ledger.reserve(
            route=self._route,
            context=context,
            attempt_kind="normal",
            request_attempt=int(context.request_attempt or 1),
            fallback_attempt=0,
        )
        started = time.monotonic()
        try:
            result = await self._client.generate_structured(**kwargs)
        except BaseException as exc:
            await self._ledger.finish(
                attempt_id,
                route=self._route,
                context=context,
                error=exc,
                elapsed_ms=(time.monotonic() - started) * 1000.0,
            )
            raise
        await self._ledger.finish(
            attempt_id,
            route=self._route,
            context=context,
            result=result,
            elapsed_ms=(time.monotonic() - started) * 1000.0,
        )
        return result

    async def aclose(self) -> None:
        # The runtime owns the underlying adapter lifecycle.
        return None


def pseudonymous_owner(value: str) -> str:
    """Hash an owner identifier before it reaches telemetry."""

    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


class ModelUsageLedger:
    """Write-safe ledger facade.

    A runtime can be used by unit tests or a process without a database.  In
    that case events remain available in ``events`` for diagnostics.  When a
    sessionmaker is attached, each attempt is persisted in PostgreSQL and a
    database failure is isolated from the provider response path.
    """

    def __init__(self, sessionmaker: Any = None, utilization_ceiling: float = 0.8) -> None:
        self.sessionmaker = sessionmaker
        self.utilization_ceiling = max(0.01, min(1.0, float(utilization_ceiling)))
        self.events: list[dict[str, Any]] = []

    async def reserve(
        self,
        *,
        route: ResolvedModelRoute,
        context: ModelCallContext,
        attempt_kind: str,
        request_attempt: int,
        fallback_attempt: int,
        input_tokens_reserved: int | None = None,
    ) -> str:
        attempt_id = uuid4().hex
        operation_key = str(
            context.metadata.get("operation_id")
            or hashlib.sha256(
                ":".join(
                    (
                        context.session_id,
                        context.run_id,
                        context.job_id,
                        context.agent,
                        context.operation,
                        context.request_id,
                    )
                ).encode("utf-8")
            ).hexdigest()
        )
        event = {
            "attempt_id": attempt_id,
            "operation_id": operation_key,
            "provider": route.provider,
            "model": route.model,
            "profile": route.profile_name,
            "credential_alias": route.credential_alias,
            "capacity_source_id": route.capacity_source_id,
            "quota_group": route.quota_group,
            "agent": context.agent,
            "stage": context.stage,
            "operation": context.operation,
            "request_attempt": request_attempt,
            "fallback_attempt": fallback_attempt,
            "attempt_kind": attempt_kind,
            "status": "reserved",
            "started_at": datetime.now(UTC).isoformat(),
            "input_tokens_reserved": input_tokens_reserved,
        }
        self.events.append(event)
        try:
            await self._persist_reservation(event, context)
        except (ModelCapacityUnavailableError, ModelUsagePersistenceError):
            # Do not allow a provider request when the durable pre-send
            # accounting transaction did not commit.
            self.events.pop()
            raise
        return attempt_id

    async def finish(
        self,
        attempt_id: str,
        *,
        route: ResolvedModelRoute,
        context: ModelCallContext,
        result: Any = None,
        error: BaseException | None = None,
        elapsed_ms: float | None = None,
    ) -> None:
        usage = dict(getattr(result, "usage", {}) or {}) if result is not None else {}
        telemetry = dict(getattr(result, "telemetry", {}) or {}) if result is not None else {}
        provider_request_id = str(
            telemetry.get("provider_request_id") or getattr(result, "response_id", "") or ""
        )
        estimated_cost = telemetry.get("estimated_cost")
        actual_cost = telemetry.get("actual_cost")
        if actual_cost is None and isinstance(telemetry.get("cost_micro_usd"), (int, float)):
            actual_cost = float(telemetry["cost_micro_usd"]) / 1_000_000
        promotional_cost = telemetry.get("promotional_micro_usd")
        gateway_attempt_count = _int_or_none(telemetry.get("gateway_attempt_count"))
        payload: dict[str, Any] = {
            "status": "succeeded" if error is None else "failed",
            "provider_request_id": provider_request_id,
            "usage": usage,
            "telemetry": telemetry,
            "input_tokens": _int_or_none(usage.get("input_tokens", usage.get("prompt_tokens"))),
            "output_tokens": _int_or_none(
                usage.get("output_tokens", usage.get("completion_tokens"))
            ),
            "cached_input_tokens": _int_or_none(
                usage.get("cached_input_tokens", usage.get("cached_prompt_tokens"))
            ),
            "cache_write_tokens": _int_or_none(usage.get("cache_write_tokens")),
            "reasoning_tokens": _int_or_none(usage.get("reasoning_tokens")),
            "total_tokens": _int_or_none(usage.get("total_tokens")),
            "estimated_cost": estimated_cost if isinstance(estimated_cost, (int, float)) else None,
            "actual_cost": actual_cost if isinstance(actual_cost, (int, float)) else None,
            "promotional_micro_usd": (
                int(promotional_cost) if isinstance(promotional_cost, (int, float)) else None
            ),
            "gateway_attempt_count": gateway_attempt_count,
            "latency_ms": elapsed_ms,
            "finished_at": datetime.now(UTC).isoformat(),
            "accepted_result_ref": (
                dict(getattr(result, "cache_metadata", {}) or {}).get("cache_key")
                if result is not None
                else None
            ),
        }
        if isinstance(error, ProviderTimeoutError) or bool(
            isinstance(error, ProviderError) and error.details.get("acceptance_uncertain")
        ):
            payload["acceptance_uncertain"] = True
        if isinstance(error, ProviderError):
            payload.update(
                {
                    "error_class": type(error).__name__,
                    "error_code": error.code,
                    "retryable": error.retryable,
                    "details": _safe_details(error.details),
                }
            )
        for event in reversed(self.events):
            if event.get("attempt_id") == attempt_id:
                event.update(payload)
                break
        await self._persist_finish(attempt_id, payload)

    async def _persist_reservation(self, event: dict[str, Any], context: ModelCallContext) -> None:
        if self.sessionmaker is None:
            return
        try:
            from sqlalchemy import select

            from oryxenai.db.models.model_usage import (
                ModelBudgetReservation,
                ModelCallAttempt,
                ModelCapacityWindow,
                ModelOperation,
            )

            async with self.sessionmaker() as db:
                operation_key = str(event["operation_id"])
                operation = (
                    await db.execute(
                        select(ModelOperation)
                        .where(ModelOperation.operation_key == operation_key)
                        .with_for_update()
                    )
                ).scalar_one_or_none()
                if operation is None:
                    operation = ModelOperation(
                        operation_key=operation_key,
                        owner_id_hash=context.owner_id_hash,
                        session_id=context.session_id,
                        run_id=context.run_id,
                        job_id=context.job_id,
                        agent=context.agent,
                        stage=context.stage,
                        operation=context.operation,
                        routing_policy_version=context.routing_policy_version,
                        input_classification=context.input_classification,
                        input_fingerprint=str(context.metadata.get("input_fingerprint", "") or ""),
                        normal_calls=int(context.metadata.get("normal_calls", 1) or 1),
                        recovery_allowance=int(context.metadata.get("recovery_allowance", 1) or 1),
                        policy_snapshot={
                            "input_classification": context.input_classification,
                            "routing_policy_version": context.routing_policy_version,
                        },
                    )
                    db.add(operation)
                    await db.flush()
                is_recovery = str(event.get("attempt_kind", "normal")) != "normal"
                if is_recovery:
                    if operation.recovery_used >= operation.recovery_allowance:
                        raise ModelUsagePersistenceError(
                            "The durable model recovery allowance is exhausted."
                        )
                    operation.recovery_used += 1
                else:
                    if operation.normal_used >= operation.normal_calls:
                        raise ModelUsagePersistenceError(
                            "The durable model-call allowance is exhausted."
                        )
                    operation.normal_used += 1
                operation.updated_at = datetime.now(UTC)
                row = ModelCallAttempt(
                    operation_id=operation.id,
                    provider=str(event["provider"]),
                    model=str(event["model"]),
                    profile_name=str(event["profile"]),
                    credential_alias=str(event["credential_alias"]),
                    capacity_source_id=str(event["capacity_source_id"]),
                    quota_group=str(event["quota_group"]),
                    agent=context.agent,
                    stage=context.stage,
                    operation=context.operation,
                    job_attempt=context.job_attempt,
                    request_attempt=context.request_attempt or int(event["request_attempt"]),
                    fallback_attempt=context.fallback_attempt or int(event["fallback_attempt"]),
                    attempt_kind=str(event["attempt_kind"]),
                    status="reserved",
                    client_request_id=context.request_id,
                    details={"operation_id": context.metadata.get("operation_id", "")},
                )
                db.add(row)
                await db.flush()
                now = datetime.now(UTC)
                input_reserved = int(event.get("input_tokens_reserved") or 0)
                for (
                    window_kind,
                    window_start,
                    window_end,
                    request_units,
                    token_units,
                ) in _quota_windows(now, input_reserved):
                    window = (
                        await db.execute(
                            select(ModelCapacityWindow)
                            .where(
                                ModelCapacityWindow.capacity_source_id
                                == str(event["capacity_source_id"]),
                                ModelCapacityWindow.model == str(event["model"]),
                                ModelCapacityWindow.window_kind == window_kind,
                                ModelCapacityWindow.window_start == window_start,
                            )
                            .with_for_update()
                        )
                    ).scalar_one_or_none()
                    if window is None:
                        window = ModelCapacityWindow(
                            capacity_source_id=str(event["capacity_source_id"]),
                            provider=str(event["provider"]),
                            model=str(event["model"]),
                            quota_group=str(event["quota_group"]),
                            window_kind=window_kind,
                            window_start=window_start,
                            window_end=window_end,
                            confidence="unknown",
                        )
                        db.add(window)
                        await db.flush()
                    request_limit = window.request_limit
                    token_limit = window.input_token_limit
                    daily_limit = window.daily_request_limit
                    request_used = window.observed_requests + window.reserved_requests
                    token_used = window.observed_input_tokens + window.reserved_input_tokens
                    if window_kind in {"rpm", "daily"}:
                        limit = request_limit if window_kind == "rpm" else daily_limit
                        if limit is not None and request_used + 1 > int(
                            limit * self.utilization_ceiling
                        ):
                            raise ModelCapacityUnavailableError(
                                f"No free capacity remains for {event['capacity_source_id']} {window_kind}."
                            )
                    if (
                        window_kind == "tpm"
                        and token_limit is not None
                        and (
                            token_used + input_reserved
                            > int(token_limit * self.utilization_ceiling)
                        )
                    ):
                        raise ModelCapacityUnavailableError(
                            f"No free input-token capacity remains for {event['capacity_source_id']}."
                        )
                    window.reserved_requests += request_units
                    window.reserved_input_tokens += token_units
                    window.observed_at = now
                    db.add(
                        ModelBudgetReservation(
                            attempt_id=row.id,
                            capacity_source_id=str(event["capacity_source_id"]),
                            quota_group=str(event["quota_group"]),
                            window_kind=window_kind,
                            window_start=window_start,
                            window_end=window_end,
                            requests_reserved=request_units,
                            input_tokens_reserved=token_units,
                        )
                    )
                await db.commit()
                event["db_attempt_id"] = str(row.id)
                event["db_operation_id"] = str(operation.id)
        except ModelUsagePersistenceError:
            raise
        except Exception as exc:  # pragma: no cover - exercised with DB faults
            logger.warning(
                "model usage reservation persistence failed error=%s", type(exc).__name__
            )
            raise ModelUsagePersistenceError() from exc

    async def _persist_finish(self, attempt_id: str, payload: Mapping[str, Any]) -> None:
        if self.sessionmaker is None:
            return
        db_id = next(
            (
                event.get("db_attempt_id")
                for event in reversed(self.events)
                if event.get("attempt_id") == attempt_id
            ),
            None,
        )
        if not db_id:
            return
        try:
            from sqlalchemy import select, update

            from oryxenai.db.models.model_usage import (
                ModelBudgetReservation,
                ModelCallAttempt,
                ModelCapacityWindow,
                ModelOperation,
            )

            async with self.sessionmaker() as db:
                row = await db.get(ModelCallAttempt, UUID(str(db_id)))
                if row is None:
                    return
                row.status = str(payload.get("status", "failed"))
                row.error_class = str(payload.get("error_class", "")) or None
                row.error_code = str(payload.get("error_code", "")) or None
                row.provider_request_id = str(payload.get("provider_request_id", "")) or None
                for source, target in (
                    ("input_tokens", "input_tokens"),
                    ("output_tokens", "output_tokens"),
                    ("cached_input_tokens", "cached_input_tokens"),
                    ("cache_write_tokens", "cache_write_tokens"),
                    ("reasoning_tokens", "reasoning_tokens"),
                    ("total_tokens", "total_tokens"),
                ):
                    value = payload.get(source)
                    if isinstance(value, int):
                        setattr(row, target, value)
                estimated = payload.get("estimated_cost")
                if isinstance(estimated, (int, float)):
                    row.estimated_cost_micro_usd = round(float(estimated) * 1_000_000)
                actual = payload.get("actual_cost")
                if isinstance(actual, (int, float)):
                    row.actual_cost_micro_usd = round(float(actual) * 1_000_000)
                promotional = payload.get("promotional_micro_usd")
                if isinstance(promotional, int):
                    row.promotional_micro_usd = promotional
                gateway_attempts = payload.get("gateway_attempt_count")
                if isinstance(gateway_attempts, int):
                    row.gateway_attempt_count = gateway_attempts
                row.details = _safe_details(
                    {
                        "telemetry": payload.get("telemetry", {}),
                        "error": payload.get("details", {}),
                        "acceptance_uncertain": bool(payload.get("acceptance_uncertain")),
                    }
                )
                row.finished_at = datetime.now(UTC)
                reservations = list(
                    (
                        await db.execute(
                            select(ModelBudgetReservation)
                            .where(
                                ModelBudgetReservation.attempt_id == row.id,
                                ModelBudgetReservation.status == "reserved",
                            )
                            .with_for_update()
                        )
                    ).scalars()
                )
                reservation_status = (
                    "unresolved" if payload.get("acceptance_uncertain") else "settled"
                )
                for reservation in reservations:
                    window = (
                        await db.execute(
                            select(ModelCapacityWindow)
                            .where(
                                ModelCapacityWindow.capacity_source_id
                                == reservation.capacity_source_id,
                                ModelCapacityWindow.window_kind == reservation.window_kind,
                                ModelCapacityWindow.window_start == reservation.window_start,
                            )
                            .with_for_update()
                        )
                    ).scalar_one_or_none()
                    if window is not None and reservation_status == "settled":
                        window.reserved_requests = max(
                            0, window.reserved_requests - reservation.requests_reserved
                        )
                        window.reserved_input_tokens = max(
                            0,
                            window.reserved_input_tokens - reservation.input_tokens_reserved,
                        )
                        if str(payload.get("status", "")) == "succeeded":
                            window.observed_requests += reservation.requests_reserved
                            observed_input = payload.get("input_tokens")
                            if isinstance(observed_input, int):
                                window.observed_input_tokens += observed_input
                        window.observed_at = datetime.now(UTC)
                    reservation.status = reservation_status
                    if reservation_status == "settled":
                        reservation.settled_at = datetime.now(UTC)
                if row.operation_id is not None:
                    operation_values: dict[str, Any] = {
                        "status": (
                            "unresolved"
                            if payload.get("acceptance_uncertain")
                            else str(payload.get("status", "failed"))
                        ),
                        "updated_at": datetime.now(UTC),
                    }
                    if str(payload.get("status", "")) == "succeeded" and payload.get(
                        "accepted_result_ref"
                    ):
                        operation_values["accepted_result_ref"] = str(
                            payload["accepted_result_ref"]
                        )
                        operation_values["accepted_attempt_id"] = row.id
                    await db.execute(
                        update(ModelOperation)
                        .where(ModelOperation.id == row.operation_id)
                        .values(**operation_values)
                    )
                await db.commit()
        except Exception as exc:  # pragma: no cover - exercised with DB faults
            logger.warning("model usage completion persistence failed error=%s", type(exc).__name__)


def _safe_details(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    excluded = {"key", "api_key", "authorization", "prompt", "input", "output", "content", "body"}
    result: dict[str, Any] = {}
    for key, item in value.items():
        if str(key).casefold() in excluded:
            continue
        if isinstance(item, Mapping):
            nested = _safe_details(item)
            if nested:
                result[str(key)] = nested
        elif isinstance(item, (str, int, float, bool)) or item is None:
            result[str(key)] = item
    return result


def _quota_windows(
    now: datetime, input_tokens: int
) -> list[tuple[str, datetime, datetime, int, int]]:
    """Return the simultaneous request/token/daily windows for one attempt."""

    minute = now.replace(second=0, microsecond=0)
    pacific = ZoneInfo("America/Los_Angeles")
    local = now.astimezone(pacific)
    local_start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    local_end = local_start + timedelta(days=1)
    daily_start = local_start.astimezone(UTC)
    daily_end = local_end.astimezone(UTC)
    return [
        ("rpm", minute, minute + timedelta(minutes=1), 1, 0),
        ("tpm", minute, minute + timedelta(minutes=1), 0, max(0, input_tokens)),
        ("daily", daily_start, daily_end, 1, 0),
    ]


def context_from_request(
    *,
    engine: str,
    operation: str,
    request_context: Any,
    input_classification: str,
) -> ModelCallContext:
    raw = request_context if isinstance(request_context, Mapping) else {}
    return ModelCallContext(
        session_id=str(raw.get("session_id", "") or ""),
        run_id=str(raw.get("run_id", "") or ""),
        job_id=str(raw.get("job_id", "") or ""),
        owner_id_hash=pseudonymous_owner(str(raw.get("owner_id", "") or "")),
        agent=str(raw.get("agent", engine) or engine),
        stage=str(raw.get("stage", engine) or engine),
        operation=operation,
        request_id=str(raw.get("request_id", "") or ""),
        routing_policy_version=str(raw.get("routing_policy_version", "") or ""),
        input_classification=input_classification,
        job_attempt=int(raw.get("job_attempt", 0) or 0),
        request_attempt=int(raw.get("request_attempt", 0) or 0),
        fallback_attempt=int(raw.get("fallback_attempt", 0) or 0),
        metadata={
            str(k): v
            for k, v in raw.items()
            if str(k)
            in {
                "operation_id",
                "support_reference",
                "input_fingerprint",
                "normal_calls",
                "recovery_allowance",
            }
        },
    )
