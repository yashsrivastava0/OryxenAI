"""Safe job metadata shared by the user-facing stage responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _iso(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def public_job_status(job: Any) -> dict[str, object]:
    """Return enough lifecycle metadata for a client to explain a stall.

    Job payloads, lock owners, and internal worker details deliberately stay
    out of the product response.  Timestamps let the browser distinguish a
    queued request from a running request whose lease stopped renewing.
    """

    return {
        "id": str(job.id),
        "kind": job.job_kind,
        "status": job.status,
        "execution_lane": getattr(job, "execution_lane", None),
        "attempt": job.attempt,
        "max_attempts": job.max_attempts,
        "created_at": _iso(getattr(job, "created_at", None)),
        "started_at": _iso(getattr(job, "started_at", None)),
        "heartbeat_at": _iso(getattr(job, "heartbeat_at", None)),
        "finished_at": _iso(getattr(job, "finished_at", None)),
        "error": job.error_payload,
    }
