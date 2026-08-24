"""Redaction and bounded cursor helpers for administrator projections."""

from __future__ import annotations

import base64
import binascii
from datetime import datetime
from uuid import UUID

from oryxenai.api.errors import ValidationError


def mask_email(email: str) -> str:
    local, separator, domain = email.partition("@")
    if not separator or not local or not domain:
        return "***"
    return f"{local[0]}***@{domain}"


def encode_cursor(created_at: datetime, identifier: UUID) -> str:
    raw = f"{created_at.isoformat()}|{identifier}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def decode_cursor(value: str | None) -> tuple[datetime, UUID] | None:
    if not value:
        return None
    if len(value) > 256:
        raise ValidationError("The pagination cursor is invalid.")
    try:
        padded = value + "=" * (-len(value) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        timestamp, identifier = raw.split("|", 1)
        parsed = datetime.fromisoformat(timestamp)
        return parsed, UUID(identifier)
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise ValidationError("The pagination cursor is invalid.") from exc


def bounded_limit(value: int = 25) -> int:
    if value < 1 or value > 100:
        raise ValidationError("The page size must be between 1 and 100.")
    return value
