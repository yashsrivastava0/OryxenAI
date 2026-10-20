"""Fenced deterministic preparation, independent of all model agents."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select

from oryxenai.auth.worker_fence import WorkerAuthorizationFence
from oryxenai.core.settings import get_settings
from oryxenai.db.models.background_job import BackgroundJob
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.models.react_handoff import PENDING, ReactHandoff
from oryxenai.db.models.site_version import PortfolioSiteVersion
from oryxenai.db.session import get_sessionmaker
from oryxenai.delivery.contracts import KIND, DeliveryError, sha256
from oryxenai.delivery.project import assemble_project, viewer_fingerprint
from oryxenai.delivery.service import DeliveryRuntime
from oryxenai.storage.artifacts import ArtifactStorageError


class ReactDeliveryHandler:
    kind = KIND

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        settings = get_settings()
        if not settings.react_delivery.enabled:
            return {
                "status": "failed",
                "error": {
                    "code": "HANDOFF_DISABLED",
                    "message": "React sharing is disabled.",
                    "retryable": False,
                },
            }
        runtime = DeliveryRuntime(settings, get_sessionmaker(settings))
        try:
            async with asyncio.timeout(settings.react_delivery.preparation_timeout_seconds):
                return await prepare(runtime, payload)
        except TimeoutError:
            return {
                "status": "failed",
                "error": {
                    "code": "HANDOFF_TIMEOUT",
                    "message": "React preparation exceeded its time limit.",
                    "retryable": True,
                },
            }
        except ArtifactStorageError as exc:
            return {
                "status": "failed",
                "error": {"code": exc.code, "message": exc.message, "retryable": exc.retryable},
            }
        except DeliveryError as exc:
            await self.on_terminal_failure(payload, exc.envelope())
            return {"status": "failed", "error": exc.envelope()}

    async def on_terminal_failure(self, payload: dict[str, Any], error: dict[str, Any]) -> None:
        async with get_sessionmaker(get_settings())() as db:
            job = await db.get(BackgroundJob, UUID(str(payload["job_id"])), with_for_update=True)
            if (
                job is None
                or job.attempt != payload.get("attempt")
                or job.lease_token != payload.get("lease_token")
            ):
                return
            row = await db.get(ReactHandoff, UUID(str(payload["handoff_id"])), with_for_update=True)
            if row and row.status in PENDING and str(row.job_id) == str(payload.get("job_id")):
                row.status = "failed"
                row.error = {
                    "code": str(error.get("code", "HANDOFF_FAILED"))[:80],
                    "message": str(error.get("message", "Preparation failed."))[:400],
                    "retryable": bool(error.get("retryable")),
                }
                await db.commit()


async def prepare(runtime: DeliveryRuntime, payload: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    identifier = UUID(str(payload["handoff_id"]))
    async with runtime.sessionmaker() as db:
        await WorkerAuthorizationFence(db).validate_payload(payload)
        row = await db.get(ReactHandoff, identifier, with_for_update=True)
        if (
            row is None
            or row.status not in PENDING
            or str(row.job_id) != str(payload.get("job_id"))
        ):
            return {"status": "cancelled"}
        source = await db.get(PortfolioSiteVersion, row.source_version_id)
        if row.viewer_version != viewer_fingerprint():
            raise DeliveryError(
                "VIEWER_COMPATIBILITY_REQUIRED",
                "The queued handoff requires the previous viewer build. Prepare it again after the deployment completes.",
            )
        if (
            source is None
            or source.status != "ready"
            or not source.index_html
            or source.restricted
            or source.portfolio_session_id != row.portfolio_session_id
            or sha256(source.index_html.encode()) != row.source_sha256
        ):
            raise DeliveryError(
                "SOURCE_UNAVAILABLE", "The selected Studio version cannot be shared."
            )
        content, theme_id, theme_sha, source_sha = (
            dict(source.content_snapshot),
            row.theme_id,
            source.theme_sha256,
            row.source_sha256,
        )
        prefix = (
            row.artifact_prefix + "/" + str(payload.get("lease_token") or payload.get("attempt", 1))
        )
        row.status = "preparing"
        queue_wait = max(0, (datetime.now(UTC) - row.created_at).total_seconds())
        row.error = None
        await db.commit()

    project = await asyncio.to_thread(
        assemble_project,
        content,
        theme_id,
        theme_sha,
        source_sha,
        max_bytes=runtime.settings.react_delivery.max_project_bytes,
    )
    async with runtime.sessionmaker() as db:
        await WorkerAuthorizationFence(db).validate_payload(payload)
        row = await db.get(ReactHandoff, identifier, with_for_update=True)
        if row is None or row.status not in PENDING:
            return {"status": "cancelled"}
        row.status = "validating"
        await db.commit()
    entries: list[dict[str, Any]] = []
    safety_expiry = datetime.now(UTC) + timedelta(days=2)
    semaphore = asyncio.Semaphore(4)

    async def upload(path: str, data: bytes) -> None:
        async with semaphore:
            reference = await runtime.store.put_verified(
                key=f"{prefix}/{path}",
                data=data,
                sha256=sha256(data),
                expires_at=safety_expiry.isoformat(),
                content_type="application/octet-stream",
            )
            entries.append(
                {
                    "path": path,
                    "bytes": len(data),
                    "sha256": reference.sha256,
                    "scope": "project",
                    "reference": reference.model_dump(mode="json"),
                }
            )

    tasks = [
        asyncio.create_task(upload(path, data)) for path, data in sorted(project.files.items())
    ]
    try:
        await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    entries.sort(key=lambda item: item["path"])

    async with runtime.sessionmaker() as db:
        # Serialize promotion with Studio edits, restrictions and owner operations.
        await db.scalar(
            select(PortfolioSession)
            .where(PortfolioSession.id == UUID(str(payload["portfolio_session_id"])))
            .with_for_update()
        )
        # Keep claim/reclaim from changing the lease until promotion commits.
        await db.get(BackgroundJob, UUID(str(payload["job_id"])), with_for_update=True)
        await WorkerAuthorizationFence(db).validate_payload(payload)
        row = await db.get(ReactHandoff, identifier, with_for_update=True)
        source = await db.get(PortfolioSiteVersion, row.source_version_id) if row else None
        if (
            row is None
            or row.status not in PENDING
            or source is None
            or source.restricted
            or source.status != "ready"
            or source.index_sha256 != source_sha
        ):
            return {"status": "cancelled"}
        previous = list(
            (
                await db.scalars(
                    select(ReactHandoff).where(
                        ReactHandoff.portfolio_session_id == row.portfolio_session_id,
                        ReactHandoff.status == "ready",
                    )
                )
            ).all()
        )
        now = datetime.now(UTC)
        for old in previous:
            old.status = "revoked"
            old.revoked_at = now
        await db.flush()
        row.status = "ready"
        row.ready_at = now
        row.expires_at = now + timedelta(seconds=runtime.settings.react_delivery.ttl_seconds)
        row.manifest = {"files": entries}
        row.receipt = {
            **project.receipt,
            "timings": {
                "queue_wait_seconds": round(queue_wait, 3),
                "preparation_seconds": round(time.monotonic() - started, 3),
            },
        }
        await db.commit()
    return {"status": "succeeded", "handoff_id": str(identifier), "model_calls": 0}
