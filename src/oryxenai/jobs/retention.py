"""Small, safe database retention sweep for replaceable output rows."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import Text, cast, delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.db.models.archived_output import ArchivedOutputRun
from oryxenai.db.models.model_call_cache import ModelCallCache
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.models.site_version import PortfolioSiteVersion


async def delete_expired_rows(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    version_ttl_days: int = 30,
    model_cache_ttl_days: int = 30,
    batch_size: int = 100,
) -> tuple[int, int, int]:
    """Delete expired model cache rows and old generated output records.

    The current active version and the newest ready version for each session
    are retained. Nonterminal versions, live cache leases, and recently updated
    retired-pipeline runs are not eligible. A single bounded transaction keeps
    the sweep safe for the small pilot DB.
    """
    current_time = now or datetime.now(UTC)
    cutoff = current_time - timedelta(days=max(1, version_ttl_days))
    cache_cutoff = current_time - timedelta(days=max(1, model_cache_ttl_days))
    limit = max(1, batch_size)

    expired_cache_ids = list(
        (
            await session.execute(
                select(ModelCallCache.id)
                .where(
                    or_(
                        (ModelCallCache.status == "ready")
                        & or_(
                            ModelCallCache.expires_at <= current_time,
                            func.coalesce(
                                ModelCallCache.last_hit_at,
                                ModelCallCache.created_at,
                            )
                            <= cache_cutoff,
                        ),
                        (ModelCallCache.status == "producing")
                        & ModelCallCache.lease_until.is_not(None)
                        & (ModelCallCache.lease_until <= current_time),
                    )
                )
                .order_by(ModelCallCache.expires_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        .scalars()
        .all()
    )
    if expired_cache_ids:
        await session.execute(
            delete(ModelCallCache).where(ModelCallCache.id.in_(expired_cache_ids))
        )

    newer_ready_version = PortfolioSiteVersion.__table__.alias("newer_ready_version")
    has_newer_ready = exists(
        select(newer_ready_version.c.id).where(
            newer_ready_version.c.portfolio_session_id == PortfolioSiteVersion.portfolio_session_id,
            newer_ready_version.c.status == "ready",
            newer_ready_version.c.seq > PortfolioSiteVersion.seq,
        )
    )
    active_version_id = PortfolioSession.current_state["code_generator"]["active_version_id"].astext
    expired_version_ids = list(
        (
            await session.execute(
                select(PortfolioSiteVersion.id)
                .join(
                    PortfolioSession,
                    PortfolioSession.id == PortfolioSiteVersion.portfolio_session_id,
                )
                .where(
                    func.coalesce(
                        PortfolioSiteVersion.completed_at,
                        PortfolioSiteVersion.updated_at,
                        PortfolioSiteVersion.created_at,
                    )
                    <= cutoff,
                    PortfolioSiteVersion.status.in_(("ready", "failed", "cancelled", "no_change")),
                    or_(
                        active_version_id.is_(None),
                        active_version_id == "",
                        active_version_id != cast(PortfolioSiteVersion.id, Text),
                    ),
                    or_(PortfolioSiteVersion.status != "ready", ~has_newer_ready),
                )
                .order_by(PortfolioSiteVersion.created_at)
                .limit(limit)
                .with_for_update(of=PortfolioSession, skip_locked=True)
            )
        )
        .scalars()
        .all()
    )
    if expired_version_ids:
        await session.execute(
            delete(PortfolioSiteVersion).where(PortfolioSiteVersion.id.in_(expired_version_ids))
        )

    expired_legacy_run_ids = list(
        (
            await session.execute(
                select(ArchivedOutputRun.id)
                .where(ArchivedOutputRun.updated_at <= cutoff)
                .order_by(ArchivedOutputRun.updated_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        .scalars()
        .all()
    )
    if expired_legacy_run_ids:
        # The retired pipeline's events and stage attempts reference runs with
        # ON DELETE CASCADE. Its file artifacts are VM-local and are never
        # migrated into the Render pilot.
        await session.execute(
            delete(ArchivedOutputRun).where(ArchivedOutputRun.id.in_(expired_legacy_run_ids))
        )

    await session.commit()
    return (
        len(expired_cache_ids),
        len(expired_version_ids),
        len(expired_legacy_run_ids),
    )
