"""Asymmetric Supabase JWT verification with a bounded process-local JWKS cache."""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
import jwt

from oryxenai.auth.errors import (
    AuthInvalidError,
    AuthProviderUnavailableError,
    AuthRateLimitedError,
    AuthRequiredError,
)
from oryxenai.core.settings import AuthConfig

_JWT_RE = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")


def extract_bearer_token(values: Sequence[str], *, max_bytes: int = 8192) -> str:
    """Extract exactly one bounded JWT bearer value from header values."""
    if not values:
        raise AuthRequiredError()
    if len(values) != 1:
        raise AuthInvalidError()
    raw = values[0].strip()
    if not raw:
        raise AuthRequiredError()
    if len(raw.encode("utf-8")) > max_bytes:
        raise AuthInvalidError()
    if not raw.startswith("Bearer "):
        raise AuthInvalidError()
    token = raw[7:].strip()
    if not token or not _JWT_RE.fullmatch(token):
        raise AuthInvalidError()
    return token


@dataclass(frozen=True, slots=True)
class VerifiedToken:
    subject: UUID


class SupabaseJwtVerifier:
    """Verify Supabase access JWTs without trusting unverified claims."""

    def __init__(
        self,
        *,
        supabase_url: str,
        config: AuthConfig,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._supabase_url = supabase_url.rstrip("/")
        try:
            self._issuer = config.issuer_for(self._supabase_url)
        except ValueError:
            # Optional local/test startup may not have provider coordinates;
            # an actual verification request remains fail-closed with 503.
            self._issuer = ""
        self._jwks_url = f"{self._issuer}/.well-known/jwks.json"
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(config.http_timeout_seconds)
        )
        self._owns_client = client is None
        self._cache_lock = asyncio.Lock()
        self._keys: dict[str, dict[str, Any]] = {}
        self._fetched_at: float | None = None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def verify(self, token: str) -> VerifiedToken:
        """Verify header, key, signature, registered claims, and role."""
        if not self._issuer:
            raise AuthProviderUnavailableError()
        if len(token.encode("utf-8")) > self._config.max_token_bytes:
            raise AuthInvalidError()
        try:
            header: Mapping[str, Any] = jwt.get_unverified_header(token)
        except (TypeError, ValueError, jwt.InvalidTokenError) as exc:
            raise AuthInvalidError() from exc

        algorithm = header.get("alg")
        kid = header.get("kid")
        if (
            not isinstance(algorithm, str)
            or algorithm not in self._config.allowed_algorithms
            or algorithm in {"HS256", "HS384", "HS512"}
            or not isinstance(kid, str)
            or not kid
            or len(kid) > 256
        ):
            raise AuthInvalidError()

        jwk = await self._get_key(kid)
        if jwk is None:
            raise AuthInvalidError()
        if jwk.get("kid") != kid or jwk.get("alg") not in {None, algorithm}:
            raise AuthInvalidError()
        if jwk.get("kty") not in {"RSA", "EC", "OKP"}:
            raise AuthInvalidError()
        key_ops = jwk.get("key_ops")
        if key_ops and (not isinstance(key_ops, list) or "verify" not in key_ops):
            raise AuthInvalidError()
        if jwk.get("use") not in {None, "sig"}:
            raise AuthInvalidError()

        try:
            key = jwt.PyJWK.from_json(json.dumps(jwk)).key
            claims: dict[str, Any] = jwt.decode(
                token,
                key=key,
                algorithms=[algorithm],
                issuer=self._issuer,
                audience=self._config.audience,
                leeway=self._config.clock_skew_seconds,
                options={
                    "require": ["exp", "iss", "sub", "aud", "role"],
                    "verify_signature": True,
                },
            )
        except (jwt.InvalidTokenError, TypeError, ValueError, KeyError) as exc:
            raise AuthInvalidError() from exc

        if claims.get("aud") != self._config.audience:
            raise AuthInvalidError()
        if claims.get("role") != "authenticated":
            raise AuthInvalidError()
        subject = claims.get("sub")
        if not isinstance(subject, str):
            raise AuthInvalidError()
        try:
            return VerifiedToken(subject=UUID(subject))
        except ValueError as exc:
            raise AuthInvalidError() from exc

    async def _get_key(self, kid: str) -> dict[str, Any] | None:
        now = time.monotonic()
        if self._fetched_at is None or now - self._fetched_at > self._config.jwks_cache_ttl_seconds:
            await self._refresh()
        key = self._keys.get(kid)
        if key is not None:
            return key
        # Rotation is the one allowed cache miss refresh. A second miss is a
        # token error; a network failure remains provider-unavailable.
        await self._refresh(force=True)
        return self._keys.get(kid)

    async def _refresh(self, *, force: bool = False) -> None:
        async with self._cache_lock:
            now = time.monotonic()
            if (
                self._fetched_at is not None
                and now - self._fetched_at <= self._config.jwks_cache_ttl_seconds
                and not force
            ):
                return
            try:
                response = await self._client.get(
                    self._jwks_url,
                    headers={"Accept": "application/json"},
                )
            except httpx.TimeoutException as exc:
                raise AuthProviderUnavailableError() from exc
            except httpx.RequestError as exc:
                raise AuthProviderUnavailableError() from exc
            if response.status_code == 429:
                raise AuthRateLimitedError()
            if response.status_code >= 500:
                raise AuthProviderUnavailableError()
            if response.status_code != 200:
                raise AuthProviderUnavailableError()
            try:
                payload = response.json()
                raw_keys = payload["keys"]
                keys = {
                    item["kid"]: dict(item)
                    for item in raw_keys
                    if isinstance(item, dict)
                    and isinstance(item.get("kid"), str)
                    and item.get("kid")
                }
            except (ValueError, TypeError, KeyError) as exc:
                raise AuthProviderUnavailableError() from exc
            if not keys:
                raise AuthProviderUnavailableError()
            self._keys = keys
            self._fetched_at = time.monotonic()
