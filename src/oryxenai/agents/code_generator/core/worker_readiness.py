"""Durable readiness proof for the Code Generator worker boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from oryxenai.jobs.heartbeat import HeartbeatRepository


async def worker_contract_readiness(repository: Any, settings: Any) -> dict[str, Any]:
    """Return whether a fresh worker can claim the active Code Generator lane.

    The API and worker are separate processes.  A configured release ID is not
    enough: the durable heartbeat must show a recent worker with the same
    queue contract and the local execution capabilities required by the
    verifier.  Repositories used by pure unit tests do not expose a database
    session; those retain the historical optimistic result.
    """

    session = getattr(repository, "_session", None)
    expected_version = str(
        getattr(settings.code_generator_development, "pipeline_contract_version", "") or ""
    )
    expected_release = str(
        getattr(settings.code_generator_development, "worker_release_id", "") or ""
    )
    base = {
        "checked": False,
        "ready": True,
        "expected_pipeline_contract_version": expected_version,
        "expected_worker_release_id": expected_release,
        "active_workers": [],
        "blocker": "",
    }
    if session is None:
        return base

    try:
        rows = await HeartbeatRepository(session).get_recent(limit=25)
    except Exception:
        return {
            **base,
            "checked": True,
            "ready": False,
            "blocker": "code_generator_worker_heartbeat_unavailable",
        }

    try:
        stale_after = max(
            float(
                getattr(
                    getattr(settings, "diagnostics", None),
                    "heartbeat_staleness",
                    60.0,
                )
            ),
            float(
                getattr(getattr(settings, "worker", None), "heartbeat_interval", 30.0)
            )
            * 2,
        )
    except (TypeError, ValueError):
        stale_after = 60.0

    now = datetime.now(UTC)
    active_workers: list[dict[str, Any]] = []
    for row in rows:
        last_seen = getattr(row, "last_seen_at", None)
        if getattr(row, "stopped_at", None) is not None or last_seen is None:
            continue
        age = max(0.0, (now - last_seen).total_seconds())
        if age > stale_after:
            continue
        metadata = getattr(row, "service_metadata", {})
        metadata = metadata if isinstance(metadata, dict) else {}
        toolchain = metadata.get("code_generator_toolchain", {})
        toolchain = toolchain if isinstance(toolchain, dict) else {}
        active_workers.append(
            {
                "instance_id": str(getattr(row, "instance_id", "")),
                "release_id": str(metadata.get("release_id", "")),
                "pipeline_contract_version": str(metadata.get("pipeline_contract_version", "")),
                "code_generator_capability": bool(
                    metadata.get("code_generator_capability", False)
                ),
                "code_generator_toolchain": {
                    "node": bool(toolchain.get("node", False)),
                    "npm": bool(toolchain.get("npm", False)),
                    "browser": bool(toolchain.get("browser", False)),
                },
                "age_seconds": round(age, 1),
            }
        )

    compatible = [
        worker
        for worker in active_workers
        if worker["release_id"] == expected_release
        and worker["pipeline_contract_version"] == expected_version
    ]
    capability_ready = [
        worker
        for worker in compatible
        if worker["code_generator_capability"]
        and all(worker["code_generator_toolchain"].values())
    ]
    blocker = ""
    if not active_workers:
        blocker = "code_generator_worker_unavailable"
    elif not compatible:
        blocker = "code_generator_worker_contract_mismatch"
    elif not capability_ready:
        blocker = "code_generator_worker_toolchain_unavailable"
    elif len(compatible) != len(active_workers):
        # A legacy worker can still claim an old queue namespace.  Do not
        # admit new work until it has drained or been stopped.
        blocker = "code_generator_worker_contract_mismatch"

    return {
        "checked": True,
        "ready": bool(capability_ready) and not blocker,
        "expected_pipeline_contract_version": expected_version,
        "expected_worker_release_id": expected_release,
        "active_workers": active_workers,
        "blocker": blocker,
    }


__all__ = ["worker_contract_readiness"]
