"""Owner actions and capability-scoped MCP reads; no public source HTTP routes."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryxenai.auth.authorization import PortfolioAccess
from oryxenai.auth.models import AppUser, PortfolioEntitlement
from oryxenai.core.settings import Settings
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.models.react_handoff import PENDING, ReactHandoff
from oryxenai.db.models.site_version import PortfolioSiteVersion
from oryxenai.delivery.contracts import KIND, DeliveryError, ShareSigner, safe_path, sha256
from oryxenai.delivery.project import viewer_fingerprint
from oryxenai.jobs.repository import JobRepository
from oryxenai.storage.artifacts import (
    ArtifactReference,
    ArtifactStorageError,
    ArtifactStore,
    S3ArtifactStore,
    create_artifact_store,
)


class DeliveryRuntime:
    def __init__(
        self,
        settings: Settings,
        sessionmaker: async_sessionmaker[AsyncSession],
        store: ArtifactStore | None = None,
    ) -> None:
        self.settings = settings
        self.sessionmaker = sessionmaker
        self.signer = ShareSigner(settings.handoff_signing_secret.get_secret_value())
        self.store = store or create_artifact_store(
            SimpleNamespace(artifact_storage=settings.react_delivery.storage)
        )

    async def validate_storage(self) -> None:
        await self.validate_compatibility()
        if (
            isinstance(self.store, S3ArtifactStore)
            and self.settings.react_delivery.storage.require_lifecycle
        ):
            await self.store.require_lifecycle(self.settings.react_delivery.storage.prefix + "/")

    async def validate_compatibility(self) -> None:
        fingerprint = viewer_fingerprint()
        async with self.sessionmaker() as db:
            incompatible = await db.scalar(
                select(ReactHandoff.id)
                .where(
                    ReactHandoff.viewer_version != fingerprint,
                    (ReactHandoff.status.in_(PENDING))
                    | (
                        (ReactHandoff.status == "ready")
                        & (ReactHandoff.expires_at > datetime.now(UTC))
                    ),
                )
                .limit(1)
            )
        if incompatible:
            raise DeliveryError(
                "VIEWER_COMPATIBILITY_REQUIRED",
                "This deployment changes a viewer required by a live handoff. Retain the compatible build or wait for handoffs to expire before deploying.",
                status_code=503,
            )

    def status(self, row: ReactHandoff) -> dict[str, Any]:
        status = row.status
        if status == "ready" and row.expires_at and row.expires_at <= datetime.now(UTC):
            status = "expired"
        link = None
        if status == "ready" and row.expires_at:
            link = (
                self.settings.auth.primary_origin.rstrip("/")
                + "/share/"
                + self.signer.token(row.id, row.expires_at)
            )
        return {
            "id": str(row.id),
            "source_version_id": str(row.source_version_id or ""),
            "status": status,
            "created_at": row.created_at.isoformat(),
            "ready_at": row.ready_at.isoformat() if row.ready_at else None,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "share_link": link,
            "mcp_url": self.settings.auth.primary_origin.rstrip("/") + "/mcp",
            "error": row.error,
            "receipt": row.receipt,
        }

    async def create(
        self, db: AsyncSession, access: PortfolioAccess, version_id: UUID
    ) -> dict[str, Any]:
        if access.actor is None or access.session.owner_user_id is None:
            raise DeliveryError(
                "AUTH_REQUIRED", "Sign in to prepare a React handoff.", status_code=401
            )
        portfolio = await db.scalar(
            select(PortfolioSession)
            .where(PortfolioSession.id == access.session.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if portfolio is None or portfolio.status != "active" or portfolio.legacy_quarantined:
            raise DeliveryError("SOURCE_UNAVAILABLE", "This portfolio cannot be shared.")
        source = await db.scalar(
            select(PortfolioSiteVersion).where(
                PortfolioSiteVersion.id == version_id,
                PortfolioSiteVersion.portfolio_session_id == portfolio.id,
            )
        )
        if (
            source is None
            or source.status != "ready"
            or source.restricted
            or not source.index_sha256
        ):
            raise DeliveryError("SOURCE_UNAVAILABLE", "Select an available, ready Studio version.")
        now = datetime.now(UTC)
        existing = list(
            (
                await db.scalars(
                    select(ReactHandoff).where(
                        ReactHandoff.portfolio_session_id == portfolio.id,
                        ReactHandoff.status.in_((*PENDING, "ready")),
                    )
                )
            ).all()
        )
        for row in existing:
            if row.status == "ready" and row.expires_at and row.expires_at <= now:
                row.status = "expired"
            elif row.source_version_id == version_id:
                return self.status(row)
            elif row.status in PENDING:
                raise DeliveryError(
                    "HANDOFF_PREPARING",
                    "Another version is being prepared. Wait for it to finish before replacing it.",
                )
        await db.flush()
        identifier = uuid4()
        row = ReactHandoff(
            id=identifier,
            owner_user_id=portfolio.owner_user_id,
            portfolio_session_id=portfolio.id,
            source_version_id=source.id,
            source_sha256=source.index_sha256,
            theme_id=source.theme_id,
            viewer_version=viewer_fingerprint(),
            status="queued",
            created_at=now,
            artifact_prefix=f"{self.settings.react_delivery.storage.prefix.strip('/')}/{identifier.hex}",
        )
        db.add(row)
        await db.flush()
        entitlement = await db.scalar(
            select(PortfolioEntitlement).where(
                PortfolioEntitlement.user_id == portfolio.owner_user_id
            )
        )
        job = await JobRepository(db).enqueue(
            KIND,
            {"portfolio_session_id": str(portfolio.id), "handoff_id": str(identifier)},
            priority=-10,
            max_attempts=self.settings.react_delivery.max_attempts,
            idempotency_scope="react-handoff",
            idempotency_key=str(identifier),
            portfolio_session_id=portfolio.id,
            owner_user_id=portfolio.owner_user_id,
            actor_user_id=access.actor.id,
            authorization_context_version=1,
            entitlement_revision=entitlement.revision if entitlement else None,
            execution_lane="react-delivery",
        )
        row.job_id = job.id
        await db.flush()
        return self.status(row)

    async def owner_row(
        self, db: AsyncSession, access: PortfolioAccess, identifier: UUID
    ) -> ReactHandoff:
        row = await db.scalar(
            select(ReactHandoff).where(
                ReactHandoff.id == identifier,
                ReactHandoff.portfolio_session_id == access.session.id,
            )
        )
        if row is None or access.actor is None:
            raise DeliveryError(
                "HANDOFF_NOT_FOUND", "This handoff does not exist.", status_code=404
            )
        return row

    async def resolve(self, share_link: str) -> ReactHandoff:
        identifier, timestamp = self.signer.parse(share_link)
        now = datetime.now(UTC)
        if timestamp <= now.timestamp():
            raise DeliveryError(
                "EXPIRED",
                "This handoff has expired. Ask its owner to prepare a new one.",
                status_code=410,
            )
        async with self.sessionmaker() as db:
            row = await db.get(ReactHandoff, identifier)
            if row is None:
                raise DeliveryError(
                    "INVALID_SHARE_LINK", "This share link is unavailable.", status_code=404
                )
            if row.status in {"revoked", "failed"}:
                raise DeliveryError(
                    "REVOKED", "This handoff is no longer available.", status_code=410
                )
            if row.status == "expired" or (row.expires_at and row.expires_at <= now):
                raise DeliveryError("EXPIRED", "This handoff has expired.", status_code=410)
            if row.status != "ready" or not row.expires_at:
                raise DeliveryError(
                    "NOT_READY", "This React handoff is still being prepared.", retryable=True
                )
            if int(row.expires_at.timestamp()) != timestamp:
                raise DeliveryError(
                    "INVALID_SHARE_LINK", "This share link is invalid.", status_code=404
                )
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
            if (
                owner is None
                or owner.status != "active"
                or portfolio is None
                or portfolio.status != "active"
                or portfolio.legacy_quarantined
                or portfolio.owner_user_id != owner.id
                or source is None
                or source.portfolio_session_id != portfolio.id
                or source.status != "ready"
                or source.restricted
                or source.index_sha256 != row.source_sha256
            ):
                raise DeliveryError(
                    "REVOKED", "The source portfolio is no longer available.", status_code=410
                )
            db.expunge(row)
            return row

    async def project(self, share_link: str) -> dict[str, Any]:
        row = await self.resolve(share_link)
        return {
            "schema": "ReactProjectManifest/v1",
            "handoff_id": str(row.id),
            "theme_id": row.theme_id,
            "viewer_version": row.viewer_version,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "files": [
                {key: value for key, value in item.items() if key != "reference"}
                for item in row.manifest["files"]
                if item["scope"] == "project"
            ],
            "receipt": row.receipt,
            "instructions": "Import all files through MCP, verify SHA-256, run npm ci, npm run typecheck and npm run build, then preview and enhance the React project. Never overwrite an existing directory.",
        }

    async def read_file(
        self, share_link: str, path: str, cursor: int = 0, *, preview: bool = False
    ) -> dict[str, Any]:
        row = await self.resolve(share_link)
        safe_path(path)
        entry = next(
            (
                item
                for item in row.manifest["files"]
                if item["path"] == path
                and (
                    item["scope"] == "project"
                    if not preview
                    else path.startswith("public/theme/") or path == "portfolio.json"
                )
            ),
            None,
        )
        if entry is None:
            raise DeliveryError(
                "FILE_NOT_FOUND", "This file is not in the handoff manifest.", status_code=404
            )
        if isinstance(cursor, bool) or cursor < 0 or cursor > entry["bytes"]:
            raise DeliveryError("INVALID_CURSOR", "The file cursor is invalid.")
        reference = ArtifactReference.model_validate(entry["reference"])
        try:
            data = await self.store.get_range(
                reference, cursor, self.settings.react_delivery.chunk_bytes
            )
        except ArtifactStorageError:
            raise DeliveryError(
                "ARTIFACT_UNAVAILABLE",
                "The project file is temporarily unavailable. Retry this chunk.",
                retryable=True,
                status_code=503,
            ) from None
        # Recheck after network I/O: revocation/expiry can race a slow read.
        await self.resolve(share_link)
        return {
            "path": path,
            "offset": cursor,
            "bytes": len(data),
            "encoding": "base64",
            "data": base64.b64encode(data).decode(),
            "chunk_sha256": sha256(data),
            "sha256": entry["sha256"],
            "next_cursor": cursor + len(data) if cursor + len(data) < entry["bytes"] else None,
        }
