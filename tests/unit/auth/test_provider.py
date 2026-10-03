from __future__ import annotations

from uuid import UUID

import httpx
import pytest

from oryxenai.auth.errors import (
    AuthInvalidError,
    AuthProviderUnavailableError,
    AuthRateLimitedError,
)
from oryxenai.auth.provider import SupabaseAuthProvider

SUBJECT = UUID("11111111-1111-4111-8111-111111111111")


def _provider(
    body: object, status_code: int = 200
) -> tuple[SupabaseAuthProvider, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status_code, json=body)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return SupabaseAuthProvider(
        supabase_url="https://project.supabase.co",
        publishable_key="sb_publishable_test",
        timeout_seconds=1,
        client=client,
    ), requests


@pytest.mark.asyncio
async def test_provider_requires_confirmed_google_identity_and_returns_presentation_metadata() -> (
    None
):
    provider, requests = _provider(
        {
            "id": str(SUBJECT),
            "email": "Person@Example.com",
            "email_confirmed_at": "2026-08-23T00:00:00Z",
            "app_metadata": {"provider": "google"},
            "user_metadata": {
                "full_name": "Presentation Name",
                "role": "admin",
                "avatar_url": "https://example.com/avatar.png",
            },
        }
    )
    try:
        identity = await provider.get_user("caller-token", SUBJECT)
    finally:
        await provider.aclose()

    assert identity.subject == SUBJECT
    assert identity.email == "person@example.com"
    assert identity.display_name == "Presentation Name"
    assert identity.avatar_url == "https://example.com/avatar.png"
    assert requests[0].headers["authorization"] == "Bearer caller-token"
    assert requests[0].headers["apikey"] == "sb_publishable_test"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {
            "id": str(SUBJECT),
            "email": "person@example.com",
            "email_confirmed_at": "2026-08-23T00:00:00Z",
            "app_metadata": {"provider": "email"},
        },
        {
            "id": str(SUBJECT),
            "email": "person@example.com",
            "app_metadata": {"provider": "google"},
        },
        {
            "id": str(UUID("22222222-2222-4222-8222-222222222222")),
            "email": "person@example.com",
            "email_confirmed_at": "2026-08-23T00:00:00Z",
            "app_metadata": {"provider": "google"},
        },
    ],
)
async def test_provider_rejects_unconfirmed_non_google_or_mismatched_id(body: object) -> None:
    provider, _ = _provider(body)
    try:
        with pytest.raises(AuthInvalidError):
            await provider.get_user("caller-token", SUBJECT)
    finally:
        await provider.aclose()


@pytest.mark.asyncio
async def test_provider_retries_one_server_error_then_returns_identity() -> None:
    calls = 0
    body = {
        "id": str(SUBJECT),
        "email": "person@example.com",
        "email_confirmed_at": "2026-08-23T00:00:00Z",
        "app_metadata": {"provider": "google"},
    }

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503) if calls == 1 else httpx.Response(200, json=body)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseAuthProvider(
        supabase_url="https://project.supabase.co",
        publishable_key="sb_publishable_test",
        timeout_seconds=1,
        client=client,
    )
    try:
        identity = await provider.get_user("caller-token", SUBJECT)
    finally:
        await provider.aclose()
        await client.aclose()

    assert identity.subject == SUBJECT
    assert calls == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [(401, AuthInvalidError), (403, AuthInvalidError), (429, AuthRateLimitedError)],
)
async def test_provider_does_not_retry_auth_rejection_or_rate_limit(
    status_code: int,
    error_type: type[Exception],
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status_code)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseAuthProvider(
        supabase_url="https://project.supabase.co",
        publishable_key="sb_publishable_test",
        timeout_seconds=1,
        client=client,
    )
    try:
        with pytest.raises(error_type):
            await provider.get_user("caller-token", SUBJECT)
    finally:
        await provider.aclose()
        await client.aclose()

    assert calls == 1


@pytest.mark.asyncio
async def test_provider_maps_two_failed_server_attempts_to_unavailable() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SupabaseAuthProvider(
        supabase_url="https://project.supabase.co",
        publishable_key="sb_publishable_test",
        timeout_seconds=1,
        client=client,
    )
    try:
        with pytest.raises(AuthProviderUnavailableError):
            await provider.get_user("caller-token", SUBJECT)
    finally:
        await provider.aclose()
        await client.aclose()

    assert calls == 2
