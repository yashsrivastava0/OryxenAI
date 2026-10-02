"""Short-lived signed preview grants.

An iframe cannot send a Bearer token, so the preview is addressed by a signed,
expiring grant that the owner-authorized API mints. The grant is stateless (an
HMAC over the session, version and expiry), carries no user identity, and stops
working after its TTL or when the signing key changes. It is only an *address*:
what it can read is limited to one ready version of one session.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from uuid import UUID

_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class PreviewGrant:
    session_id: UUID
    version_id: UUID
    expires_at: int


class GrantError(Exception):
    """A grant is malformed, forged or expired."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class PreviewGrantSigner:
    """Mints and verifies grants with one symmetric key."""

    def __init__(self, secret: bytes | str) -> None:
        key = secret.encode("utf-8") if isinstance(secret, str) else secret
        if len(key) < 16:
            raise ValueError("The preview grant secret must be at least 16 bytes.")
        self._key = key

    @classmethod
    def random(cls) -> PreviewGrantSigner:
        """A per-process key: grants die with the process and are simply re-minted."""
        return cls(secrets.token_bytes(32))

    def _sign(self, body: str) -> str:
        return _b64(hmac.new(self._key, body.encode("ascii"), hashlib.sha256).digest())

    def mint(self, session_id: UUID, version_id: UUID, ttl_seconds: int) -> tuple[str, int]:
        expires_at = int(time.time()) + max(1, int(ttl_seconds))
        payload = {"s": str(session_id), "v": str(version_id), "e": expires_at}
        body = _VERSION + "." + _b64(json.dumps(payload, separators=(",", ":")).encode("ascii"))
        return f"{body}.{self._sign(body)}", expires_at

    def verify(self, token: str, *, now: float | None = None) -> PreviewGrant:
        parts = token.split(".")
        if len(parts) != 3 or parts[0] != _VERSION:
            raise GrantError("malformed")
        body = f"{parts[0]}.{parts[1]}"
        if not hmac.compare_digest(self._sign(body), parts[2]):
            raise GrantError("invalid_signature")
        try:
            payload = json.loads(_unb64(parts[1]))
            grant = PreviewGrant(
                session_id=UUID(str(payload["s"])),
                version_id=UUID(str(payload["v"])),
                expires_at=int(payload["e"]),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise GrantError("malformed") from exc
        if (time.time() if now is None else now) >= grant.expires_at:
            raise GrantError("expired")
        return grant
