"""Local, privacy-safe browser test trace ingestion."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from oryxenai.api.errors import PayloadTooLargeError
from oryxenai.core.logging import get_logger

router = APIRouter(prefix="/client-diagnostics", tags=["client diagnostics"])
logger = get_logger("oryxenai.api.client_diagnostics")


class ClientDiagnosticEvent(BaseModel):
    """Allow-listed browser metadata; no request or response body is accepted."""

    model_config = ConfigDict(extra="ignore")

    at: str | None = Field(default=None, max_length=40)
    kind: str = Field(min_length=1, max_length=64)
    route: str | None = Field(default=None, max_length=200)
    method: str | None = Field(default=None, max_length=10)
    status: int | None = Field(default=None, ge=0, le=599)
    duration_ms: int | None = Field(default=None, ge=0, le=600000)
    code: str | None = Field(default=None, max_length=80)
    stage: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=80)
    action: str | None = Field(default=None, max_length=80)
    input_characters: int | None = Field(default=None, ge=0, le=300000)
    message: str | None = Field(default=None, max_length=200)
    meta: dict[str, Any] | None = Field(default=None, max_length=32)


class ClientDiagnosticBatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    client_run_id: UUID
    events: list[ClientDiagnosticEvent] = Field(min_length=1, max_length=100)


class ClientDiagnosticResponse(BaseModel):
    client_run_id: str
    accepted: int
    stored: bool


def _trace_path(request: Request, client_run_id: UUID) -> Path:
    root = Path(request.app.state.settings.client_diagnostics.output_root)
    if not root.is_absolute():
        # routes/client_diagnostics.py -> api -> oryxenai -> src -> repo root
        root = Path(__file__).resolve().parents[4] / root
    return root / str(client_run_id) / "events.jsonl"


def _write_events(path: Path, client_run_id: UUID, events: list[ClientDiagnosticEvent]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    received_at = datetime.now(UTC).isoformat()
    with path.open("a", encoding="utf-8") as handle:
        for event in events:
            record: dict[str, Any] = {
                "client_run_id": str(client_run_id),
                "received_at": received_at,
                **event.model_dump(mode="json", exclude_none=True),
            }
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")


@router.post("/events", response_model=ClientDiagnosticResponse, status_code=202)
async def ingest_client_events(
    body: ClientDiagnosticBatch,
    request: Request,
) -> ClientDiagnosticResponse:
    """Persist a bounded local test trace without requiring an auth token.

    The route is mounted only when the local development UI and the explicit
    client-diagnostics setting are enabled. A failed trace write is reported
    without making the user's actual workflow fail.
    """

    settings = request.app.state.settings
    max_events = int(settings.client_diagnostics.max_events_per_batch)
    if len(body.events) > max_events:
        raise PayloadTooLargeError(f"A diagnostic batch may contain at most {max_events} events.")

    path = _trace_path(request, body.client_run_id)
    try:
        await asyncio.to_thread(_write_events, path, body.client_run_id, body.events)
    except OSError as exc:
        logger.warning("client trace write unavailable error=%s", type(exc).__name__)
        return ClientDiagnosticResponse(
            client_run_id=str(body.client_run_id),
            accepted=len(body.events),
            stored=False,
        )
    return ClientDiagnosticResponse(
        client_run_id=str(body.client_run_id),
        accepted=len(body.events),
        stored=True,
    )
