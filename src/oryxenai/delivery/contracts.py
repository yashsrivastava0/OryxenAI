"""Small public delivery contract and purpose-separated capability signing."""

from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import UTC, datetime
from pathlib import PurePosixPath
from urllib.parse import urlsplit
from uuid import UUID

KIND = "react_delivery.prepare"
ADAPTER_REVISION = "1"
VIEWER_URI = "ui://oryxenai/react-portfolio-v1.html"


class DeliveryError(Exception):
    def __init__(
        self, code: str, message: str, *, retryable: bool = False, status_code: int = 409
    ) -> None:
        self.code, self.message, self.retryable, self.status_code = (
            code,
            message,
            retryable,
            status_code,
        )
        super().__init__(message)

    def envelope(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}


def safe_path(path: str) -> str:
    candidate = PurePosixPath(path)
    if (
        not path
        or len(path) > 240
        or "\\" in path
        or candidate.is_absolute()
        or any(
            part in {"", ".", ".."} or ":" in part or part.startswith(".")
            for part in path.split("/")
        )
    ):
        raise DeliveryError(
            "FILE_NOT_FOUND", "The requested project file does not exist.", status_code=404
        )
    return path


class ShareSigner:
    def __init__(self, secret: str) -> None:
        if len(secret.encode()) < 32:
            raise DeliveryError(
                "HANDOFF_NOT_CONFIGURED",
                "Sharing requires a stable signing secret of at least 32 bytes.",
                status_code=503,
            )
        self._secret = secret.encode()

    def token(self, identifier: UUID, expires_at: datetime) -> str:
        body = f"{identifier.hex}.{int(expires_at.timestamp())}"
        signature = (
            base64.urlsafe_b64encode(
                hmac.digest(self._secret, b"react-handoff/v1:" + body.encode(), "sha256")
            )
            .decode()
            .rstrip("=")
        )
        return f"{body}.{signature}"

    def parse(self, link: str) -> tuple[UUID, int]:
        try:
            token = urlsplit(link).path.rsplit("/", 1)[-1] if "/" in link else link
            raw_id, expiry, _ = token.split(".")
            identifier = UUID(hex=raw_id)
            timestamp = int(expiry)
            expected = self.token(identifier, datetime.fromtimestamp(timestamp, UTC))
            if not hmac.compare_digest(token, expected):
                raise ValueError
            return identifier, timestamp
        except (ValueError, OverflowError, OSError):
            raise DeliveryError(
                "INVALID_SHARE_LINK", "This share link is invalid.", status_code=404
            ) from None


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
