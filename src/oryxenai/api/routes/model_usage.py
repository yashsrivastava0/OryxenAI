"""Administrator-only global model usage and capacity reporting."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from oryxenai.agents.shared.contracts import AgentKey
from oryxenai.api.dependencies import get_db_session, require_admin
from oryxenai.auth.domain import CurrentUser
from oryxenai.db.models.model_usage import ModelCallAttempt, ModelCapacityWindow

router = APIRouter(
    prefix="/admin/model-usage",
    tags=["model-usage"],
    dependencies=[Depends(require_admin)],
)


@router.get("/attempts")
async def list_attempts(
    provider: str | None = Query(default=None),
    model: str | None = Query(default=None),
    agent: str | None = Query(default=None),
    operation: str | None = Query(default=None),
    alias: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    # Explicit names are useful to API clients that prefer the column's
    # meaning; date_from/date_to remain the documented compact aliases.
    started_after: datetime | None = Query(default=None, include_in_schema=False),
    started_before: datetime | None = Query(default=None, include_in_schema=False),
    limit: int = Query(default=100, ge=1, le=500),
    _admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    del _admin
    filters: list[ColumnElement[bool]] = [
        ModelCallAttempt.agent.in_([key.value for key in AgentKey])
    ]
    for column, value in (
        (ModelCallAttempt.provider, provider),
        (ModelCallAttempt.model, model),
        (ModelCallAttempt.agent, agent),
        (ModelCallAttempt.operation, operation),
        (ModelCallAttempt.credential_alias, alias),
    ):
        if value:
            filters.append(column == value)
    lower = _utc_bound(date_from or started_after)
    upper = _utc_bound(date_to or started_before)
    if lower is not None:
        filters.append(ModelCallAttempt.started_at >= lower)
    if upper is not None:
        filters.append(ModelCallAttempt.started_at <= upper)
    rows = list(
        (
            await db.execute(
                select(ModelCallAttempt)
                .where(*filters)
                .order_by(ModelCallAttempt.started_at.desc())
                .limit(limit)
            )
        ).scalars()
    )
    return {
        "items": [_attempt_payload(row) for row in rows],
        "generated_at": datetime.now(UTC).isoformat(),
    }


@router.get("/capacity")
async def list_capacity(
    provider: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    model: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    observed_after: datetime | None = Query(default=None, include_in_schema=False),
    observed_before: datetime | None = Query(default=None, include_in_schema=False),
    limit: int = Query(default=100, ge=1, le=500),
    _admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    del _admin
    filters = []
    if provider:
        filters.append(ModelCapacityWindow.provider == provider)
    if source_id:
        filters.append(ModelCapacityWindow.capacity_source_id == source_id)
    if model:
        filters.append(ModelCapacityWindow.model == model)
    lower = _utc_bound(date_from or observed_after)
    upper = _utc_bound(date_to or observed_before)
    if lower is not None:
        filters.append(ModelCapacityWindow.observed_at >= lower)
    if upper is not None:
        filters.append(ModelCapacityWindow.observed_at <= upper)
    rows = list(
        (
            await db.execute(
                select(ModelCapacityWindow)
                .where(*filters)
                .order_by(ModelCapacityWindow.observed_at.desc())
                .limit(limit)
            )
        ).scalars()
    )
    return {
        "items": [_capacity_payload(row) for row in rows],
        "generated_at": datetime.now(UTC).isoformat(),
    }


def _utc_bound(value: datetime | None) -> datetime | None:
    """Normalize admin filter bounds before comparing timezone-aware columns."""

    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _attempt_payload(row: ModelCallAttempt) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "provider": row.provider,
        "model": row.model,
        "profile": row.profile_name,
        "credential_alias": row.credential_alias,
        "capacity_source_id": row.capacity_source_id,
        "quota_group": row.quota_group,
        "agent": row.agent,
        "stage": row.stage,
        "operation": row.operation,
        "job_attempt": row.job_attempt,
        "request_attempt": row.request_attempt,
        "fallback_attempt": row.fallback_attempt,
        "attempt_kind": row.attempt_kind,
        "status": row.status,
        "error_class": row.error_class,
        "error_code": row.error_code,
        "provider_request_id": row.provider_request_id,
        "usage": {
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "cached_input_tokens": row.cached_input_tokens,
            "cache_write_tokens": row.cache_write_tokens,
            "reasoning_tokens": row.reasoning_tokens,
            "total_tokens": row.total_tokens,
        },
        "estimated_cost_micro_usd": row.estimated_cost_micro_usd,
        "actual_cost_micro_usd": row.actual_cost_micro_usd,
        "promotional_micro_usd": row.promotional_micro_usd,
        "wallet_micro_usd": row.wallet_micro_usd,
        "started_at": row.started_at.isoformat(),
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        "details": dict(row.details or {}),
    }


def _capacity_payload(row: ModelCapacityWindow) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "provider": row.provider,
        "capacity_source_id": row.capacity_source_id,
        "model": row.model,
        "quota_group": row.quota_group,
        "window_kind": row.window_kind,
        "window_start": row.window_start.isoformat(),
        "window_end": row.window_end.isoformat(),
        "limits": {
            "requests": row.request_limit,
            "input_tokens": row.input_token_limit,
            "daily_requests": row.daily_request_limit,
        },
        "observed": {
            "requests": row.observed_requests,
            "input_tokens": row.observed_input_tokens,
        },
        "reserved": {
            "requests": row.reserved_requests,
            "input_tokens": row.reserved_input_tokens,
        },
        "cooldown_until": row.cooldown_until.isoformat() if row.cooldown_until else None,
        "confidence": row.confidence,
        "observed_at": row.observed_at.isoformat(),
    }
