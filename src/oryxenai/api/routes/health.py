"""Health endpoints.

/health/live  — process liveness; never depends on PostgreSQL.
/health/ready — dependency readiness; includes a lightweight DB query.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from oryxenai.core.lifecycle import check_database_ready
from oryxenai.core.logging import get_logger

router = APIRouter()
logger = get_logger("oryxenai.api.health")


@router.get("/live")
async def liveness() -> dict[str, str]:
    """Process liveness — always 200 if the process is running."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness(request: Request) -> JSONResponse:
    """Dependency readiness — includes a lightweight PostgreSQL query."""
    engine = request.app.state.engine
    ready = True
    if engine is not None:
        ready = await check_database_ready(engine)
    status_code = 200 if ready else 503
    body: dict[str, object] = {
        "status": "ready" if ready else "not_ready",
        "database": "up" if ready else "down",
    }
    return JSONResponse(status_code=status_code, content=body)
