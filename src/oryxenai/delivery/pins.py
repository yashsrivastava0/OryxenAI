"""Shared SQL predicate protecting live sources from either pruning path."""

from datetime import UTC, datetime

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.sql.elements import ColumnElement

from oryxenai.db.models.react_handoff import PENDING, ReactHandoff
from oryxenai.db.models.site_version import PortfolioSiteVersion


def live_source_pin(now: datetime | None = None) -> ColumnElement[bool]:
    return exists(
        select(ReactHandoff.id).where(
            ReactHandoff.source_version_id == PortfolioSiteVersion.id,
            or_(
                ReactHandoff.status.in_(PENDING),
                and_(
                    ReactHandoff.status == "ready",
                    ReactHandoff.expires_at > (now or datetime.now(UTC)),
                ),
            ),
        )
    )
