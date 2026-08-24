from __future__ import annotations

import json
from uuid import uuid4

import httpx
import pytest

from oryxenai.api.errors import ValidationError
from oryxenai.auth.admin.masking import bounded_limit, decode_cursor, encode_cursor, mask_email
from oryxenai.auth.admin.provider import AdminProviderError, SupabaseAdminProvider
from oryxenai.auth.admin.repository import validate_safe_details


@pytest.mark.asyncio
async def test_supabase_admin_provider_uses_server_headers_and_safe_payloads() -> None:
    subject = uuid4()
    calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(204, request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseAdminProvider(
        supabase_url="https://project.supabase.co",
        secret_key="server-secret",  # noqa: S106 - deterministic unit-test credential.
        client=client,
    )
    await provider.suspend_user(subject)
    await provider.restore_user(subject)
    await provider.delete_user(subject)
    await client.aclose()

    assert calls[0].url.path == f"/auth/v1/admin/users/{subject}"
    assert calls[0].headers["apikey"] == "server-secret"
    assert calls[0].headers["authorization"] == "Bearer server-secret"
    assert json.loads(calls[0].content) == {"ban_duration": "876000h"}
    assert json.loads(calls[1].content) == {"ban_duration": "none"}
    assert calls[2].method == "DELETE"


@pytest.mark.asyncio
async def test_supabase_admin_provider_maps_rate_limit_and_timeout_without_body_leakage() -> None:
    subject = uuid4()

    async def rate_limited(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, content=b"provider body contains a secret")

    rate_client = httpx.AsyncClient(transport=httpx.MockTransport(rate_limited))
    provider = SupabaseAdminProvider(
        supabase_url="https://project.supabase.co",
        secret_key="server-secret",  # noqa: S106 - deterministic unit-test credential.
        client=rate_client,
    )
    with pytest.raises(AdminProviderError) as rate_error:
        await provider.suspend_user(subject)
    await rate_client.aclose()
    assert rate_error.value.code == "AUTH_ADMIN_PROVIDER_RATE_LIMITED"
    assert "provider body" not in str(rate_error.value)

    async def timed_out(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("provider timeout", request=request)

    timeout_client = httpx.AsyncClient(transport=httpx.MockTransport(timed_out))
    provider = SupabaseAdminProvider(
        supabase_url="https://project.supabase.co",
        secret_key="server-secret",  # noqa: S106 - deterministic unit-test credential.
        client=timeout_client,
    )
    with pytest.raises(AdminProviderError) as timeout_error:
        await provider.delete_user(subject)
    await timeout_client.aclose()
    assert timeout_error.value.code == "AUTH_ADMIN_PROVIDER_UNAVAILABLE"
    assert timeout_error.value.retryable is True


def test_admin_projection_helpers_are_bounded_and_opaque() -> None:
    identifier = uuid4()
    from datetime import UTC, datetime

    timestamp = datetime.now(UTC)
    cursor = encode_cursor(timestamp, identifier)
    decoded = decode_cursor(cursor)
    assert decoded == (timestamp, identifier)
    assert mask_email("person@example.com") == "p***@example.com"
    assert mask_email("not-an-email") == "***"
    assert bounded_limit(100) == 100
    with pytest.raises(ValidationError):
        bounded_limit(101)
    with pytest.raises(ValidationError):
        decode_cursor("not-a-cursor")


def test_admin_safe_details_reject_private_or_unbounded_fields() -> None:
    assert validate_safe_details({"role": "admin", "accepted": True}) == {
        "role": "admin",
        "accepted": True,
    }
    with pytest.raises(ValueError):
        validate_safe_details({"email": "person@example.com"})
    with pytest.raises(ValueError):
        validate_safe_details({"session_id": "C:\\generated\\portfolio"})
