"""Authenticated, explicit owner actions; source bytes are available only via MCP."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.api.dependencies import (
    get_db_session,
    require_pipeline_mutable,
    require_pipeline_session,
)
from oryxenai.api.errors import AppError
from oryxenai.auth.authorization import PortfolioAccess
from oryxenai.db.models.react_handoff import ReactHandoff
from oryxenai.delivery.contracts import DeliveryError
from oryxenai.delivery.service import DeliveryRuntime

router = APIRouter(prefix="/sessions/{session_id}/handoffs", tags=["react-handoffs"])


class PrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version_id: UUID


def get_delivery(request: Request) -> DeliveryRuntime:
    runtime = getattr(request.app.state, "delivery", None)
    if not isinstance(runtime, DeliveryRuntime):
        raise AppError("React sharing is not enabled.", code="HANDOFF_DISABLED", status_code=503)
    return runtime


def translate(exc: DeliveryError) -> AppError:
    return AppError(exc.message, code=exc.code, status_code=exc.status_code)


@router.get("")
async def latest_handoffs(
    access: PortfolioAccess = Depends(require_pipeline_session),
    db: AsyncSession = Depends(get_db_session),
    delivery: DeliveryRuntime = Depends(get_delivery),
) -> dict[str, Any]:
    rows = (
        await db.scalars(
            select(ReactHandoff)
            .where(ReactHandoff.portfolio_session_id == access.session.id)
            .order_by(
                case(
                    (ReactHandoff.status.in_(("queued", "preparing", "validating")), 0),
                    (ReactHandoff.status == "ready", 1),
                    else_=2,
                ),
                ReactHandoff.created_at.desc(),
            )
            .limit(3)
        )
    ).all()
    return {"handoffs": [delivery.status(row) for row in rows]}


@router.post("", status_code=202)
async def prepare_handoff(
    body: PrepareRequest,
    access: PortfolioAccess = Depends(require_pipeline_mutable),
    db: AsyncSession = Depends(get_db_session),
    delivery: DeliveryRuntime = Depends(get_delivery),
) -> dict[str, Any]:
    try:
        return await delivery.create(db, access, body.version_id)
    except DeliveryError as exc:
        raise translate(exc) from exc


@router.get("/{handoff_id}")
async def handoff_status(
    handoff_id: UUID,
    access: PortfolioAccess = Depends(require_pipeline_session),
    db: AsyncSession = Depends(get_db_session),
    delivery: DeliveryRuntime = Depends(get_delivery),
) -> dict[str, Any]:
    try:
        return delivery.status(await delivery.owner_row(db, access, handoff_id))
    except DeliveryError as exc:
        raise translate(exc) from exc


@router.delete("/{handoff_id}")
async def revoke_handoff(
    handoff_id: UUID,
    access: PortfolioAccess = Depends(require_pipeline_mutable),
    db: AsyncSession = Depends(get_db_session),
    delivery: DeliveryRuntime = Depends(get_delivery),
) -> dict[str, Any]:
    try:
        row = await delivery.owner_row(db, access, handoff_id)
        if row.status in {"queued", "preparing", "validating", "ready"}:
            row.status, row.revoked_at = "revoked", datetime.now(UTC)
            await db.flush()
        return delivery.status(row)
    except DeliveryError as exc:
        raise translate(exc) from exc
