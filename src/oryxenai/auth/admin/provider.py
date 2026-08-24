"""Narrow server-only Supabase Auth administrator client.

The publishable browser key is intentionally not accepted here.  This client
is created only in the FastAPI process and never serializes provider bodies.
"""

from __future__ import annotations

import re
from typing import Protocol
from uuid import UUID

import httpx


class AdminProviderError(Exception):
    """Safe provider failure classification without response-body leakage."""

    def __init__(self, code: str, *, retryable: bool = False) -> None:
        self.code = code
        self.retryable = retryable
        super().__init__(code)


class AdminIdentityProvider(Protocol):
    async def suspend_user(self, subject: UUID) -> None: ...

    async def restore_user(self, subject: UUID) -> None: ...

    async def delete_user(self, subject: UUID) -> None: ...


class SupabaseAdminProvider:
    """Bounded calls to Supabase's server-only Auth admin endpoints."""

    def __init__(
        self,
        *,
        supabase_url: str,
        secret_key: str,
        timeout_seconds: float = 5.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = supabase_url.rstrip("/")
        self._headers = {
            "apikey": secret_key,
            "Content-Type": "application/json",
        }
        # Supabase's modern ``sb_secret_...`` keys are opaque API keys and
        # must not be presented as bearer JWTs.  Legacy service-role JWTs
        # still require the Authorization header during the migration
        # window, so keep support without misclassifying arbitrary secrets.
        if _looks_like_legacy_jwt(secret_key):
            self._headers["Authorization"] = f"Bearer {secret_key}"
        self._owned_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(
                timeout_seconds,
                connect=min(timeout_seconds, 3.0),
                read=timeout_seconds,
                write=timeout_seconds,
                pool=min(timeout_seconds, 3.0),
            )
        )

    async def suspend_user(self, subject: UUID) -> None:
        await self._patch(subject, {"ban_duration": "876000h"})

    async def restore_user(self, subject: UUID) -> None:
        await self._patch(subject, {"ban_duration": "none"})

    async def delete_user(self, subject: UUID) -> None:
        try:
            response = await self._client.delete(
                f"{self._base_url}/auth/v1/admin/users/{subject}",
                headers=self._headers,
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise AdminProviderError("AUTH_ADMIN_PROVIDER_UNAVAILABLE", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise AdminProviderError("AUTH_ADMIN_PROVIDER_UNAVAILABLE", retryable=True) from exc
        if response.status_code in {200, 204, 404}:
            return
        self._raise_for_status(response)

    async def _patch(self, subject: UUID, payload: dict[str, str]) -> None:
        try:
            response = await self._client.put(
                f"{self._base_url}/auth/v1/admin/users/{subject}",
                headers=self._headers,
                json=payload,
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise AdminProviderError("AUTH_ADMIN_PROVIDER_UNAVAILABLE", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise AdminProviderError("AUTH_ADMIN_PROVIDER_UNAVAILABLE", retryable=True) from exc
        if 200 <= response.status_code < 300:
            return
        self._raise_for_status(response)

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code == 429:
            raise AdminProviderError("AUTH_ADMIN_PROVIDER_RATE_LIMITED", retryable=True)
        if response.status_code >= 500:
            raise AdminProviderError("AUTH_ADMIN_PROVIDER_UNAVAILABLE", retryable=True)
        if response.status_code in {401, 403}:
            raise AdminProviderError("AUTH_ADMIN_PROVIDER_CONFIG_INVALID")
        raise AdminProviderError("AUTH_ADMIN_PROVIDER_REQUEST_REJECTED")

    async def aclose(self) -> None:
        if self._owned_client:
            await self._client.aclose()


def _looks_like_legacy_jwt(value: str) -> bool:
    """Recognize only the compact three-segment JWT form used by legacy keys."""
    parts = value.split(".")
    return len(parts) == 3 and all(re.fullmatch(r"[A-Za-z0-9_-]+", part) for part in parts)
