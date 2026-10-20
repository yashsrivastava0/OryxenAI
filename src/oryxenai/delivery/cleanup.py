"""Bounded cleanup; retained foreign-key-null rows preserve deletion information."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import exists, or_, select

from oryxenai.auth.models import AppUser
from oryxenai.db.models.background_job import BackgroundJob
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.models.react_handoff import PENDING, TERMINAL, ReactHandoff
from oryxenai.db.models.site_version import PortfolioSiteVersion
from oryxenai.delivery.service import DeliveryRuntime
from oryxenai.storage.artifacts import ArtifactStorageError


async def sweep(runtime: DeliveryRuntime) -> None:
    now = datetime.now(UTC)
    async with runtime.sessionmaker() as db:
        # Select due/invalid records rather than repeatedly scanning the same
        # oldest live rows. Foreign-key-null rows survive aggregate deletion.
        valid_owner = exists(
            select(AppUser.id).where(
                AppUser.id == ReactHandoff.owner_user_id, AppUser.status == "active"
            )
        )
        valid_session = exists(
            select(PortfolioSession.id).where(
                PortfolioSession.id == ReactHandoff.portfolio_session_id,
                PortfolioSession.status == "active",
                PortfolioSession.owner_user_id == ReactHandoff.owner_user_id,
                PortfolioSession.legacy_quarantined.is_(False),
            )
        )
        valid_source = exists(
            select(PortfolioSiteVersion.id).where(
                PortfolioSiteVersion.id == ReactHandoff.source_version_id,
                PortfolioSiteVersion.status == "ready",
                PortfolioSiteVersion.restricted.is_(False),
            )
        )
        stopped_job = exists(
            select(BackgroundJob.id).where(
                BackgroundJob.id == ReactHandoff.job_id,
                BackgroundJob.status.in_(("failed", "cancelled", "succeeded")),
            )
        )
        present_job = exists(
            select(BackgroundJob.id).where(BackgroundJob.id == ReactHandoff.job_id)
        )
        rows = list(
            (
                await db.scalars(
                    select(ReactHandoff)
                    .where(
                        ReactHandoff.status.in_((*PENDING, "ready")),
                        or_(
                            ReactHandoff.expires_at <= now,
                            ~valid_owner,
                            ~valid_session,
                            ~valid_source,
                            ReactHandoff.status.in_(PENDING) & (stopped_job | ~present_job),
                        ),
                    )
                    .order_by(ReactHandoff.created_at)
                    .limit(100)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for row in rows:
            owner = await db.get(AppUser, row.owner_user_id) if row.owner_user_id else None
            portfolio = (
                await db.get(PortfolioSession, row.portfolio_session_id)
                if row.portfolio_session_id
                else None
            )
            source = (
                await db.get(PortfolioSiteVersion, row.source_version_id)
                if row.source_version_id
                else None
            )
            job = await db.get(BackgroundJob, row.job_id) if row.job_id else None
            if row.expires_at and row.expires_at <= now:
                row.status = "expired"
            elif (
                owner is None
                or owner.status != "active"
                or portfolio is None
                or portfolio.status != "active"
                or portfolio.legacy_quarantined
                or portfolio.owner_user_id != row.owner_user_id
                or source is None
                or source.restricted
                or source.status != "ready"
            ):
                row.status, row.revoked_at = "revoked", now
            elif row.status in PENDING and (
                job is None or job.status in {"failed", "cancelled", "succeeded"}
            ):
                row.status = "failed"
                row.error = {
                    "code": "JOB_FAILED",
                    "message": "Preparation stopped. Prepare the handoff again.",
                    "retryable": True,
                }
        await db.commit()
        terminal_ids = list(
            (
                await db.scalars(
                    select(ReactHandoff.id)
                    .where(ReactHandoff.status.in_(TERMINAL), ReactHandoff.cleaned_at.is_(None))
                    .order_by(ReactHandoff.created_at)
                    .limit(100)
                )
            ).all()
        )
    for identifier in terminal_ids:
        async with runtime.sessionmaker() as db:
            terminal_row = await db.get(ReactHandoff, identifier)
            if terminal_row is None or terminal_row.status not in TERMINAL:
                continue
            prefix = terminal_row.artifact_prefix
        try:
            await runtime.store.delete_prefix(prefix)
        except ArtifactStorageError:
            continue
        async with runtime.sessionmaker() as db:
            cleaned_row = await db.get(ReactHandoff, identifier, with_for_update=True)
            if cleaned_row is not None and cleaned_row.status in TERMINAL:
                cleaned_row.cleaned_at = now
                await db.commit()
    async with runtime.sessionmaker() as db:
        cutoff = now - timedelta(days=runtime.settings.react_delivery.metadata_retention_days)
        rows = list(
            (
                await db.scalars(
                    select(ReactHandoff)
                    .where(ReactHandoff.status.in_(TERMINAL), ReactHandoff.cleaned_at < cutoff)
                    .limit(100)
                )
            ).all()
        )
        for row in rows:
            await db.delete(row)
        await db.commit()


async def cleanup_loop(runtime: DeliveryRuntime) -> None:
    from oryxenai.core.logging import get_logger

    logger = get_logger("oryxenai.delivery.cleanup")
    while True:
        try:
            await sweep(runtime)
        except Exception as exc:
            logger.warning("handoff cleanup failed error=%s", type(exc).__name__)
        await asyncio.sleep(runtime.settings.react_delivery.cleanup_interval_seconds)
