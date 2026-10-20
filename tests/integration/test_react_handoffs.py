"""Real PostgreSQL claims, immutable promotion, revocation and cleanup."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from pydantic import SecretStr
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from oryxenai.auth.authorization import PortfolioAccess
from oryxenai.auth.domain import AccountStatus, AuthRole, CurrentUser
from oryxenai.auth.models import AppUser, PortfolioEntitlement
from oryxenai.auth.worker_fence import AuthorizationFenceError
from oryxenai.core.settings import get_settings
from oryxenai.db.models.background_job import BackgroundJob
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.models.react_handoff import ReactHandoff
from oryxenai.db.models.site_version import PortfolioSiteVersion
from oryxenai.db.repositories.site_versions import SiteVersionRepository
from oryxenai.delivery.cleanup import sweep
from oryxenai.delivery.contracts import DeliveryError, sha256
from oryxenai.delivery.service import DeliveryRuntime
from oryxenai.jobs.handlers.react_delivery import prepare
from oryxenai.jobs.repository import JobRepository
from oryxenai.storage.artifacts import ArtifactStorageError, MemoryArtifactStore
from oryxenai.themes import get_theme
from tests.unit.themes.atlas_fixtures import designer

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest_asyncio.fixture
async def db_session(test_engine):
    async with async_sessionmaker(test_engine, expire_on_commit=False)() as db:
        yield db
        await db.rollback()


async def fixture(db, engine, *, store=None):
    settings = get_settings().model_copy(deep=True)
    settings.handoff_signing_secret = SecretStr("test-only-stable-signing-secret-000000000000")
    settings.react_delivery.enabled = True
    settings.react_delivery.storage.provider = "memory"
    settings.react_delivery.storage.require_lifecycle = False
    owner_id, subject_id, session_id = uuid4(), uuid4(), uuid4()
    owner = AppUser(
        id=owner_id,
        supabase_user_id=subject_id,
        primary_email="delivery@example.com",
        username="delivery-owner",
        role="user",
        status="active",
        onboarding_completed_at=datetime.now(UTC),
    )
    db.add(owner)
    await db.flush()
    portfolio = PortfolioSession(
        id=session_id,
        owner_user_id=owner_id,
        legacy_quarantined=False,
        session_mode="owned",
        status="active",
    )
    db.add(portfolio)
    await db.flush()
    db.add(PortfolioEntitlement(user_id=owner_id, portfolio_session_id=session_id, revision=1))
    theme = get_theme("cobalt-atlas/v2")
    source = PortfolioSiteVersion(
        portfolio_session_id=session_id,
        seq=1,
        status="ready",
        content_snapshot=designer(),
        theme_id=theme.theme_id,
        theme_sha256=theme.css_sha256,
        index_html="<verified>fixture</verified>",
        index_sha256=sha256(b"<verified>fixture</verified>"),
    )
    db.add(source)
    await db.commit()
    actor = CurrentUser(
        id=owner_id,
        supabase_user_id=subject_id,
        username="delivery-owner",
        role=AuthRole.USER,
        status=AccountStatus.ACTIVE,
    )
    runtime = DeliveryRuntime(
        settings, async_sessionmaker(engine, expire_on_commit=False), store or MemoryArtifactStore()
    )
    return runtime, PortfolioAccess(actor, portfolio), source


async def start(db, runtime, access, source):
    result = await runtime.create(db, access, source.id)
    await db.commit()
    jobs = await JobRepository(db).claim_batch(
        "delivery-test", 120, batch_size=4, model_lane_concurrency=2
    )
    await db.commit()
    row = await db.get(ReactHandoff, UUID(result["id"]))
    job = next(job for job in jobs if job.id == row.job_id)
    return result, {
        **job.payload,
        "job_id": str(job.id),
        "attempt": job.attempt,
        "lease_token": job.lease_token,
    }


async def test_duplicate_ready_reuse_expiry_and_post_read_revocation(db_session, test_engine):
    runtime, access, source = await fixture(db_session, test_engine)
    initial, payload = await start(db_session, runtime, access, source)
    assert (await runtime.create(db_session, access, source.id))["id"] == initial["id"]
    await db_session.commit()
    assert (await prepare(runtime, payload))["model_calls"] == 0
    db_session.expunge_all()
    row = await db_session.get(ReactHandoff, UUID(initial["id"]))
    status = runtime.status(row)
    again = await runtime.create(db_session, access, source.id)
    assert again["id"] == initial["id"] and again["expires_at"] == status["expires_at"]
    await db_session.commit()
    link = status["share_link"]
    manifest = await runtime.project(link)
    assert manifest["receipt"]["model_calls"] == 0
    assert all("reference" not in entry for entry in manifest["files"])
    assert (await runtime.read_file(link, "portfolio.json"))["offset"] == 0
    with pytest.raises(DeliveryError) as exc:
        await runtime.read_file(link, "../.env")
    assert exc.value.code == "FILE_NOT_FOUND"
    row.status = "revoked"
    await db_session.commit()
    with pytest.raises(DeliveryError) as exc:
        await runtime.read_file(link, "portfolio.json")
    assert exc.value.code == "REVOKED"
    await sweep(runtime)
    await db_session.refresh(row)
    assert row.cleaned_at and not runtime.store._objects


async def test_replacement_failure_preserves_ready_then_promotes_atomically(
    db_session, test_engine
):
    runtime, access, source = await fixture(db_session, test_engine)
    initial, payload = await start(db_session, runtime, access, source)
    await prepare(runtime, payload)
    await JobRepository(db_session).mark_succeeded(UUID(payload["job_id"]), {})
    await db_session.commit()
    second = PortfolioSiteVersion(
        portfolio_session_id=access.session.id,
        seq=2,
        status="ready",
        content_snapshot=designer(),
        theme_id=source.theme_id,
        theme_sha256=source.theme_sha256,
        index_html="new",
        index_sha256=sha256(b"new"),
    )
    db_session.add(second)
    await db_session.commit()
    replacement, second_payload = await start(db_session, runtime, access, second)
    original_put = runtime.store.put_verified

    async def outage(**kwargs):
        raise ArtifactStorageError("OUTAGE", "Temporary storage outage")

    runtime.store.put_verified = outage
    with pytest.raises(ArtifactStorageError):
        await prepare(runtime, second_payload)
    async with runtime.sessionmaker() as db:
        first_row = await db.get(ReactHandoff, UUID(initial["id"]))
        assert first_row.status == "ready"
    runtime.store.put_verified = original_put
    await prepare(runtime, second_payload)
    db_session.expunge_all()
    assert (await db_session.get(ReactHandoff, UUID(initial["id"]))).status == "revoked"
    assert (await db_session.get(ReactHandoff, UUID(replacement["id"]))).status == "ready"


async def test_lost_lease_cannot_publish_partial_upload(db_session, test_engine):
    runtime, access, source = await fixture(db_session, test_engine)
    initial, payload = await start(db_session, runtime, access, source)
    original_put = runtime.store.put_verified
    changed = False

    async def supersede(**kwargs):
        nonlocal changed
        result = await original_put(**kwargs)
        if not changed:
            changed = True
            async with runtime.sessionmaker() as db:
                job = await db.get(BackgroundJob, UUID(payload["job_id"]))
                job.lease_token = str(uuid4())
                job.attempt += 1
                await db.commit()
        return result

    runtime.store.put_verified = supersede
    with pytest.raises(AuthorizationFenceError):
        await prepare(runtime, payload)
    await db_session.rollback()
    row = await db_session.get(ReactHandoff, UUID(initial["id"]))
    assert row.status == "validating" and row.ready_at is None and not row.manifest


async def test_source_pinning_restrictions_and_cascade_preserve_cleanup(db_session, test_engine):
    runtime, access, source = await fixture(db_session, test_engine)
    initial, payload = await start(db_session, runtime, access, source)
    await prepare(runtime, payload)
    for sequence in (2, 3):
        db_session.add(
            PortfolioSiteVersion(
                portfolio_session_id=access.session.id,
                seq=sequence,
                status="ready",
                content_snapshot=designer(),
                theme_id=source.theme_id,
                theme_sha256=source.theme_sha256,
                index_html="new",
                index_sha256=sha256(b"new"),
            )
        )
    await db_session.commit()
    await SiteVersionRepository(db_session).prune_versions(
        access.session.id, keep=0, active_id=None
    )
    assert await db_session.get(PortfolioSiteVersion, source.id) is not None
    await SiteVersionRepository(db_session).restrict_versions(access.session.id, [source.id])
    await db_session.commit()
    db_session.expunge_all()
    row = await db_session.get(ReactHandoff, UUID(initial["id"]))
    assert row.status == "revoked"
    await db_session.execute(
        delete(BackgroundJob).where(BackgroundJob.portfolio_session_id == access.session.id)
    )
    await db_session.execute(
        delete(PortfolioEntitlement).where(PortfolioEntitlement.user_id == access.actor.id)
    )
    await db_session.execute(
        delete(PortfolioSession).where(PortfolioSession.id == access.session.id)
    )
    await db_session.execute(delete(AppUser).where(AppUser.id == access.actor.id))
    await db_session.commit()
    await db_session.refresh(row)
    assert (
        row.owner_user_id is None
        and row.portfolio_session_id is None
        and row.source_version_id is None
    )
    assert row.artifact_prefix
    await sweep(runtime)
    await db_session.refresh(row)
    assert row.cleaned_at and not runtime.store._objects


@pytest.mark.parametrize("job_status", [None, "cancelled", "succeeded"])
async def test_cleanup_finishes_orphaned_preparations(db_session, test_engine, job_status):
    runtime, access, source = await fixture(db_session, test_engine)
    result = await runtime.create(db_session, access, source.id)
    await db_session.commit()
    row = await db_session.get(ReactHandoff, UUID(result["id"]))
    if job_status:
        job = await db_session.get(BackgroundJob, row.job_id)
        job.status = job_status
    else:
        await db_session.execute(delete(BackgroundJob).where(BackgroundJob.id == row.job_id))
    await db_session.commit()
    await sweep(runtime)
    await db_session.refresh(row)
    assert row.status == "failed" and row.cleaned_at
    row.cleaned_at = datetime.now(UTC) - timedelta(days=8)
    await db_session.commit()
    await sweep(runtime)
    db_session.expunge_all()
    assert await db_session.get(ReactHandoff, row.id) is None


async def test_redeployment_refuses_to_replace_a_live_viewer(db_session, test_engine):
    runtime, access, source = await fixture(db_session, test_engine)
    initial, payload = await start(db_session, runtime, access, source)
    await prepare(runtime, payload)
    await runtime.validate_compatibility()
    db_session.expunge_all()
    row = await db_session.get(ReactHandoff, UUID(initial["id"]))
    row.viewer_version = "older-immutable-viewer"
    await db_session.commit()
    with pytest.raises(DeliveryError) as exc:
        await runtime.validate_compatibility()
    assert exc.value.code == "VIEWER_COMPATIBILITY_REQUIRED"
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()
    await runtime.validate_compatibility()


async def test_expiry_denies_immediately_without_waiting_for_cleanup(db_session, test_engine):
    runtime, access, source = await fixture(db_session, test_engine)
    initial, payload = await start(db_session, runtime, access, source)
    await prepare(runtime, payload)
    db_session.expunge_all()
    row = await db_session.get(ReactHandoff, UUID(initial["id"]))
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    expired_link = (
        runtime.settings.auth.primary_origin
        + "/share/"
        + runtime.signer.token(row.id, row.expires_at)
    )
    await db_session.commit()
    with pytest.raises(DeliveryError) as exc:
        await runtime.project(expired_link)
    assert exc.value.code == "EXPIRED"
    await sweep(runtime)
    await db_session.refresh(row)
    assert row.status == "expired" and row.cleaned_at


async def test_queue_admits_only_one_delivery_across_workers(db_session, test_engine):
    runtime, access, source = await fixture(db_session, test_engine)
    first = await runtime.create(db_session, access, source.id)
    await db_session.commit()
    job = await db_session.get(
        BackgroundJob, (await db_session.get(ReactHandoff, UUID(first["id"]))).job_id
    )
    await JobRepository(db_session).enqueue(
        "react_delivery.prepare",
        {"handoff_id": str(uuid4()), "portfolio_session_id": str(access.session.id)},
        owner_user_id=access.actor.id,
        actor_user_id=access.actor.id,
        portfolio_session_id=access.session.id,
        authorization_context_version=1,
        execution_lane="react-delivery",
    )
    await db_session.commit()
    claimed = await JobRepository(db_session).claim_batch(
        "worker-a", 120, batch_size=8, model_lane_concurrency=2
    )
    await db_session.commit()
    async with runtime.sessionmaker() as other:
        claimed_b = await JobRepository(other).claim_batch(
            "worker-b", 120, batch_size=8, model_lane_concurrency=2
        )
        await other.commit()
    assert len(claimed) == 1 and not claimed_b
    assert job.execution_lane == "react-delivery"
