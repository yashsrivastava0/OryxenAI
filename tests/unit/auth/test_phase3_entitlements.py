from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from oryxenai.agents.shared.providers.errors import (
    MODEL_PROVIDER_CREDIT_EXHAUSTED,
    MODEL_PROVIDER_CREDIT_MESSAGE,
    ProviderCreditError,
    stable_provider_failure,
)
from oryxenai.auth.authorization import DurableAuthorizationContext, durable_snapshot
from oryxenai.auth.domain import (
    AccountStatus,
    AuthRole,
    CurrentUser,
    EntitlementProjection,
)
from oryxenai.auth.entitlements import admin_entitlement_projection
from oryxenai.auth.schemas import MeResponse
from oryxenai.auth.worker_fence import AuthorizationFenceError, WorkerAuthorizationFence


def _user(
    *, role: AuthRole = AuthRole.USER, entitlement: EntitlementProjection | None = None
) -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        supabase_user_id=uuid4(),
        username="phase-three-user",
        role=role,
        status=AccountStatus.ACTIVE,
        entitlement=entitlement,
    )


def test_admin_projection_is_explicitly_unlimited_and_safe() -> None:
    projection = admin_entitlement_projection()

    assert projection.policy == "unlimited_admin"
    assert projection.can_create_portfolio is True
    assert projection.can_start_generation is True
    assert projection.can_retry_generation is True
    assert projection.can_regenerate is True
    assert projection.read_only is False
    assert projection.portfolio_session_id is None


def test_me_projection_contains_only_safe_entitlement_fields() -> None:
    session_id = uuid4()
    run_id = uuid4()
    projection = EntitlementProjection(
        policy="single_portfolio",
        portfolio_session_id=session_id,
        generation_run_id=run_id,
        successful_run_id=None,
        consumed_at=None,
        can_create_portfolio=False,
        can_start_generation=False,
        can_retry_generation=True,
        can_regenerate=False,
        read_only=False,
        revision=2,
    )

    payload = MeResponse.from_current_user(_user(entitlement=projection)).model_dump()

    assert payload["portfolio_session_id"] == str(session_id)
    assert payload["generation_run_id"] == str(run_id)
    assert payload["can_retry_generation"] is True
    assert "email" not in payload
    assert "access_token" not in payload
    assert "allowlist" not in payload
    assert "supabase_user_id" not in payload


def test_durable_snapshot_carries_local_bindings_only() -> None:
    context = DurableAuthorizationContext(
        portfolio_session_id=uuid4(),
        owner_user_id=uuid4(),
        actor_user_id=uuid4(),
        entitlement_revision=4,
    )

    snapshot = durable_snapshot(context)

    assert snapshot["authorization_context_version"] == 1
    assert snapshot["entitlement_revision"] == 4
    assert set(snapshot) == {
        "portfolio_session_id",
        "owner_user_id",
        "actor_user_id",
        "authorization_context_version",
        "entitlement_revision",
    }

    with pytest.raises(ValueError, match="local identity bindings"):
        DurableAuthorizationContext(None, None, None).validate()
    with pytest.raises(ValueError, match="negative"):
        DurableAuthorizationContext(uuid4(), uuid4(), uuid4(), entitlement_revision=-1).validate()


def test_provider_credit_failure_is_stable_and_redacted() -> None:
    code, message = stable_provider_failure(
        ProviderCreditError("provider body contains secret billing details")
    )

    assert code == MODEL_PROVIDER_CREDIT_EXHAUSTED
    assert message == MODEL_PROVIDER_CREDIT_MESSAGE
    assert "secret" not in message

    unknown_code, unknown_message = stable_provider_failure(
        {"code": "PROVIDER_UNKNOWN_ERROR", "message": "raw provider body with a secret"}
    )
    assert unknown_code == "PROVIDER_UNKNOWN_ERROR"
    assert unknown_message == "The model operation failed safely."
    assert "secret" not in unknown_message


class _Result:
    def __init__(self, value: object) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object:
        return self.value


class _EntitlementSession:
    def __init__(self, entitlement: object) -> None:
        self.entitlement = entitlement

    async def execute(self, _statement: object) -> _Result:
        return _Result(self.entitlement)


@pytest.mark.asyncio
async def test_success_reconciliation_accepts_only_the_post_success_revision() -> None:
    user_id = uuid4()
    session_id = uuid4()
    run_id = uuid4()
    entitlement = SimpleNamespace(
        user_id=user_id,
        portfolio_session_id=session_id,
        generation_run_id=run_id,
        successful_run_id=run_id,
        revision=8,
    )
    fence = WorkerAuthorizationFence(_EntitlementSession(entitlement))  # type: ignore[arg-type]

    await fence._validate_entitlement(user_id, session_id, run_id, 7, allow_success=True)

    with pytest.raises(AuthorizationFenceError):
        await fence._validate_entitlement(user_id, session_id, run_id, 6, allow_success=True)


@pytest.mark.asyncio
async def test_worker_probe_fence_checks_claimed_attempt_without_database_access() -> None:
    fence = WorkerAuthorizationFence(object())  # type: ignore[arg-type]
    lease = "lease-3"
    job = SimpleNamespace(
        status="running",
        attempt=3,
        lease_token=lease,
        job_kind="system.worker_probe",
    )

    await fence.validate_job(job, expected_attempt=3, expected_lease_token=lease)

    with pytest.raises(AuthorizationFenceError):
        await fence.validate_job(job, expected_attempt=2, expected_lease_token=lease)
