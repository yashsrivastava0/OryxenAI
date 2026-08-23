from __future__ import annotations

from uuid import UUID

import httpx
import pytest

from oryxenai.auth.errors import AuthInvalidError
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
