"""Bounded Supabase Auth identity resolution for first-login admission."""

from __future__ import annotations

import logging
from typing import Any, Protocol
from uuid import UUID

import httpx

from oryxenai.auth.domain import ProviderIdentity, normalize_email
from oryxenai.auth.errors import (
    AuthInvalidError,
    AuthProviderUnavailableError,
    AuthRateLimitedError,
)
from oryxenai.auth.http import AuthHttpClient

logger = logging.getLogger(__name__)


class ProviderIdentityClient(Protocol):
    async def get_user(self, token: str, expected_subject: UUID) -> ProviderIdentity: ...


class SupabaseAuthProvider:
    """Call only the Supabase Auth user endpoint; never persist provider tokens."""

    def __init__(
        self,
        *,
        supabase_url: str,
        publishable_key: str,
        timeout_seconds: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._url = supabase_url.rstrip("/")
        self._publishable_key = publishable_key
        self._http = AuthHttpClient(
            timeout=httpx.Timeout(timeout_seconds),
            client=client,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def get_user(self, token: str, expected_subject: UUID) -> ProviderIdentity:
        if not self._url or not self._publishable_key:
            raise AuthProviderUnavailableError()
        try:
            response = await self._http.get(
                f"{self._url}/auth/v1/user",
                headers={
                    "Accept": "application/json",
                    "apikey": self._publishable_key,
                    "Authorization": f"Bearer {token}",
                },
            )
        except httpx.RequestError as exc:
            logger.warning("Supabase identity lookup failed (%s)", type(exc).__name__)
            raise AuthProviderUnavailableError() from exc
        if response.status_code == 429:
            logger.warning("Supabase identity lookup returned HTTP 429")
            raise AuthRateLimitedError()
        if response.status_code in {401, 403}:
            raise AuthInvalidError()
        if response.status_code >= 500:
            logger.warning("Supabase identity lookup returned HTTP %s", response.status_code)
            raise AuthProviderUnavailableError()
        if response.status_code != 200:
            logger.warning("Supabase identity lookup returned HTTP %s", response.status_code)
            raise AuthProviderUnavailableError()
        try:
            body: Any = response.json()
        except ValueError as exc:
            logger.warning(
                "Supabase identity response could not be parsed (%s)", type(exc).__name__
            )
            raise AuthProviderUnavailableError() from exc
        if not isinstance(body, dict):
            raise AuthProviderUnavailableError()

        provider_subject = body.get("id")
        email_value = body.get("email")
        confirmed_at = body.get("email_confirmed_at") or body.get("confirmed_at")
        app_metadata = body.get("app_metadata")
        provider_name = app_metadata.get("provider") if isinstance(app_metadata, dict) else None
        providers = app_metadata.get("providers") if isinstance(app_metadata, dict) else None
        google_identity = provider_name == "google" or (
            isinstance(providers, list) and "google" in providers
        )
        if (
            provider_subject != str(expected_subject)
            or not email_value
            or not confirmed_at
            or not google_identity
        ):
            raise AuthInvalidError()
        try:
            email = normalize_email(str(email_value))
        except ValueError as exc:
            raise AuthInvalidError() from exc

        # These values are presentation-only and are deliberately not used by
        # admission, role, status, ownership, or quota decisions.
        metadata = body.get("user_metadata")
        display_name: str | None = None
        avatar_url: str | None = None
        if isinstance(metadata, dict):
            for key in ("full_name", "name"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    display_name = value.strip()[:200]
                    break
            avatar = metadata.get("avatar_url")
            if isinstance(avatar, str) and avatar.startswith(("https://", "http://")):
                avatar_url = avatar[:2048]
        return ProviderIdentity(
            subject=expected_subject,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
        )
