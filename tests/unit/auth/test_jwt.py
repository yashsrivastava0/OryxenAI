from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any
from uuid import UUID

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

from oryxenai.auth.errors import (
    AuthInvalidError,
    AuthProviderUnavailableError,
    AuthRateLimitedError,
    AuthRequiredError,
)
from oryxenai.auth.jwt import SupabaseJwtVerifier, extract_bearer_token
from oryxenai.core.settings import AuthConfig

SUPABASE_URL = "https://project.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"
SUBJECT = UUID("11111111-1111-4111-8111-111111111111")


def _private_pem(key: Any) -> bytes:
    return key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())


RSA_PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
EC_PRIVATE = ec.generate_private_key(ec.SECP256R1())
RSA_PRIVATE_OTHER = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _jwk(key: Any, *, kid: str, algorithm: str) -> dict[str, Any]:
    public = key.public_key()
    algorithm_api = (
        jwt.algorithms.RSAAlgorithm if algorithm == "RS256" else jwt.algorithms.ECAlgorithm
    )
    value = json.loads(algorithm_api.to_jwk(public))
    value.update({"kid": kid, "alg": algorithm, "use": "sig", "key_ops": ["verify"]})
    return value


def _claims(**overrides: Any) -> dict[str, Any]:
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "aud": "authenticated",
        "exp": now + 3600,
        "iat": now,
        "nbf": now - 1,
        "sub": str(SUBJECT),
        "role": "authenticated",
    }
    claims.update(overrides)
    return claims


def _token(key: Any, *, algorithm: str = "RS256", kid: str = "key-1", **claims: Any) -> str:
    return jwt.encode(
        _claims(**claims),
        _private_pem(key) if algorithm == "RS256" else key,
        algorithm=algorithm,
        headers={"kid": kid},
    )


def _verifier(
    keys: list[dict[str, Any]],
    handler: Callable[[httpx.Request], httpx.Response] | None = None,
) -> tuple[SupabaseJwtVerifier, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def default_handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"keys": keys})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler or default_handler))
    return SupabaseJwtVerifier(
        supabase_url=SUPABASE_URL, config=AuthConfig(), client=client
    ), requests


def test_bearer_extraction_is_strict_and_bounded() -> None:
    jwt_text = "a.b.c"
    assert extract_bearer_token([f"Bearer {jwt_text}"]) == jwt_text
    with pytest.raises(AuthRequiredError):
        extract_bearer_token([])
    with pytest.raises(AuthInvalidError):
        extract_bearer_token([f"Bearer {jwt_text}", f"Bearer {jwt_text}"])
    with pytest.raises(AuthInvalidError):
        extract_bearer_token(["Basic a.b.c"])
    with pytest.raises(AuthInvalidError):
        extract_bearer_token([f"Bearer {jwt_text}"], max_bytes=3)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("algorithm", "key"),
    [("RS256", RSA_PRIVATE), ("ES256", EC_PRIVATE)],
)
async def test_valid_asymmetric_tokens_return_only_the_subject(algorithm: str, key: Any) -> None:
    verifier, _ = _verifier([_jwk(key, kid="key-1", algorithm=algorithm)])
    try:
        result = await verifier.verify(_token(key, algorithm=algorithm))
    finally:
        await verifier.aclose()
    assert result.subject == SUBJECT


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": int(time.time()) - 60},
        {"nbf": int(time.time()) + 3600},
        {"iss": "https://other.supabase.co/auth/v1"},
        {"aud": "public"},
        {"role": "anon"},
        {"sub": "not-a-uuid"},
        {"sub": None},
    ],
)
async def test_registered_claim_failures_are_rejected(overrides: dict[str, Any]) -> None:
    verifier, _ = _verifier([_jwk(RSA_PRIVATE, kid="key-1", algorithm="RS256")])
    try:
        with pytest.raises(AuthInvalidError):
            await verifier.verify(_token(RSA_PRIVATE, **overrides))
    finally:
        await verifier.aclose()


@pytest.mark.asyncio
async def test_invalid_signature_wrong_algorithm_and_unknown_key_are_rejected() -> None:
    verifier, _ = _verifier([_jwk(RSA_PRIVATE, kid="key-1", algorithm="RS256")])
    try:
        with pytest.raises(AuthInvalidError):
            await verifier.verify(_token(RSA_PRIVATE_OTHER))
        with pytest.raises(AuthInvalidError):
            await verifier.verify(
                jwt.encode(
                    _claims(),
                    "test-secret-that-is-at-least-thirty-two-bytes-long",
                    algorithm="HS256",
                    headers={"kid": "key-1"},
                )
            )
        with pytest.raises(AuthInvalidError):
            await verifier.verify(_token(RSA_PRIVATE, kid="missing"))
    finally:
        await verifier.aclose()


@pytest.mark.asyncio
async def test_jwks_cache_and_unknown_kid_rotation_refresh() -> None:
    responses = [
        {"keys": [_jwk(RSA_PRIVATE, kid="key-1", algorithm="RS256")]},
        {
            "keys": [
                _jwk(RSA_PRIVATE, kid="key-1", algorithm="RS256"),
                _jwk(EC_PRIVATE, kid="key-2", algorithm="ES256"),
            ]
        },
    ]
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=responses[min(len(requests) - 1, 1)])

    verifier, _ = _verifier([], handler)
    try:
        assert (await verifier.verify(_token(RSA_PRIVATE))).subject == SUBJECT
        assert (await verifier.verify(_token(RSA_PRIVATE))).subject == SUBJECT
        assert (
            await verifier.verify(_token(EC_PRIVATE, algorithm="ES256", kid="key-2"))
        ).subject == SUBJECT
    finally:
        await verifier.aclose()
    assert len(requests) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [429, 503])
async def test_jwks_rate_limit_and_outage_are_safe(status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status)

    verifier, _ = _verifier([], handler)
    try:
        expected = AuthRateLimitedError if status == 429 else AuthProviderUnavailableError
        with pytest.raises(expected):
            await verifier.verify(_token(RSA_PRIVATE))
    finally:
        await verifier.aclose()


@pytest.mark.asyncio
async def test_jwks_timeout_is_bounded_and_does_not_expose_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    verifier, _ = _verifier([], handler)
    try:
        with pytest.raises(AuthProviderUnavailableError):
            await verifier.verify(_token(RSA_PRIVATE))
    finally:
        await verifier.aclose()
