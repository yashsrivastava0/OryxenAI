from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryxenai.auth.admin.provider import AdminProviderError
from oryxenai.auth.models import AppUser, DeletedIdentityTombstone
from oryxenai.main import create_app
from tests.conftest import install_test_identity, override_test_identity

pytestmark = pytest.mark.integration


class _FakeAdminProvider:
    def __init__(self, *, fail_delete_once: bool = False) -> None:
        self.fail_delete_once = fail_delete_once
        self.deleted: list[str] = []

    async def suspend_user(self, subject) -> None:
        return None

    async def restore_user(self, subject) -> None:
        return None

    async def delete_user(self, subject) -> None:
        if self.fail_delete_once:
            self.fail_delete_once = False
            raise AdminProviderError("AUTH_ADMIN_PROVIDER_UNAVAILABLE", retryable=True)
        self.deleted.append(str(subject))


async def _admin_client(test_engine):
    app = create_app()
    app.state.sessionmaker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    admin = await install_test_identity(app, test_engine, role="admin")
    provider = _FakeAdminProvider()
    app.state.auth_admin_provider = provider
    return app, admin, provider


@pytest.mark.asyncio
async def test_admin_inventory_is_admin_only_and_masks_identity_data(test_engine) -> None:
    app, _admin, _provider = await _admin_client(test_engine)
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/admin/summary")
        assert response.status_code == 200
        assert response.json()["users"]["active"] == 1

        users = await client.get("/api/v1/admin/users")
        assert users.status_code == 200
        payload = users.json()
        assert payload["items"][0]["masked_email"] == "t***@example.com"
        assert "test-admin@example.com" not in users.text
        assert "supabase_user_id" not in users.text

    normal_app = create_app()
    normal_app.state.sessionmaker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    override_test_identity(normal_app, role="user")
    async with httpx.AsyncClient(
        transport=ASGITransport(app=normal_app), base_url="http://test"
    ) as client:
        denied = await client.get("/api/v1/admin/summary")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "ADMIN_REQUIRED"


@pytest.mark.asyncio
async def test_failed_user_delete_is_resumable_and_audited(test_engine) -> None:
    app, admin, _provider = await _admin_client(test_engine)
    provider = _FakeAdminProvider(fail_delete_once=True)
    app.state.auth_admin_provider = provider
    target_id = uuid4()
    subject = uuid4()
    async with async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)() as db:
        db.add(
            AppUser(
                id=target_id,
                supabase_user_id=subject,
                primary_email="target@example.com",
                username="target-user",
                role="user",
                status="active",
                onboarding_completed_at=datetime.now(UTC),
            )
        )
        await db.commit()

    path = f"/api/v1/admin/users/{target_id}/delete"
    headers = {"Idempotency-Key": "delete-target-001", "Content-Type": "application/json"}
    body = {"confirmation": str(target_id), "username": "target-user"}
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        first = await client.post(path, headers=headers, json=body)
        assert first.status_code == 503
        assert first.json()["error"]["code"] == "AUTH_ADMIN_PROVIDER_UNAVAILABLE"
        operations = await client.get("/api/v1/admin/operations")
        assert operations.status_code == 200
        pending = operations.json()["items"]
        assert len(pending) == 1
        assert pending[0]["status"] == "retryable_failure"
        assert pending[0]["resumable"] is True
        assert "idempotency_key" not in operations.text
        assert "request_fingerprint" not in operations.text
        resumed = await client.post(
            f"/api/v1/admin/operations/{pending[0]['id']}/resume",
            headers={"Idempotency-Key": "resume-delete-target-001"},
        )
        assert resumed.status_code == 202
        assert resumed.json()["status"] == "completed"
        second = await client.post(path, headers=headers, json=body)
        assert second.status_code == 202
        operation = second.json()
        assert operation["status"] == "completed"
        assert operation["safe_state"]["local_status"] == "deleted"

    async with async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)() as db:
        target = await db.get(AppUser, target_id)
        tombstone = (
            await db.execute(
                select(DeletedIdentityTombstone).where(
                    DeletedIdentityTombstone.former_app_user_id == target_id
                )
            )
        ).scalar_one()
        assert target is not None and target.status == "deleted"
        assert tombstone.supabase_user_id == subject
        assert str(subject) not in first.text
    assert provider.deleted == [str(subject)]
    assert admin.id != target_id
