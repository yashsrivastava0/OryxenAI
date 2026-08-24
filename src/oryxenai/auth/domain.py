"""Small, provider-neutral authentication domain types and normalizers."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class AuthRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class AccountStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETION_PENDING = "deletion_pending"
    DELETED = "deleted"


RESERVED_USERNAMES = frozenset(
    {
        "admin",
        "api",
        "app",
        "auth",
        "health",
        "preview",
        "settings",
        "static",
        "support",
        "system",
    }
)
_USERNAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{1,28})[a-z0-9]$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthInputError(ValueError):
    """A safe configuration or onboarding input error."""


def normalize_email(value: str) -> str:
    """Return a normalized email without attempting provider-side validation."""
    normalized = value.strip().lower()
    if not normalized or not _EMAIL_RE.fullmatch(normalized):
        raise AuthInputError("A verified email address is required.")
    return normalized


def normalize_email_list(raw: str | Iterable[str]) -> tuple[str, ...]:
    """Normalize a comma/semicolon/whitespace-separated email collection."""
    values = re.split(r"[,;\s]+", raw) if isinstance(raw, str) else [str(item) for item in raw]
    entries = [item.strip().lower() for item in values if item.strip()]
    normalized: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        email = normalize_email(entry)
        if email in seen:
            raise AuthInputError("The authentication email configuration contains duplicates.")
        seen.add(email)
        normalized.append(email)
    return tuple(normalized)


def normalize_username(value: str) -> str:
    """Normalize and validate the one-time application username claim."""
    if not isinstance(value, str):
        raise AuthInputError("Username must be text.")
    candidate = value.strip().lower()
    if not 3 <= len(candidate) <= 30:
        raise AuthInputError("Username must be between 3 and 30 characters.")
    if _EMAIL_RE.fullmatch(candidate) or "@" in candidate:
        raise AuthInputError("Username cannot resemble an email address.")
    if not candidate.isascii() or not _USERNAME_RE.fullmatch(candidate):
        raise AuthInputError(
            "Username must use lowercase letters, numbers, underscores, or hyphens "
            "and start and end with a letter or number."
        )
    if candidate in RESERVED_USERNAMES:
        raise AuthInputError("That username is reserved.")
    return candidate


@dataclass(frozen=True, slots=True)
class ProviderIdentity:
    """Verified top-level identity returned by Supabase Auth."""

    subject: UUID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None


@dataclass(frozen=True, slots=True)
class EntitlementProjection:
    """Safe, additive portfolio-capability projection for ``/me``.

    These are capabilities, not authority.  The server recomputes and
    enforces them from the entitlement row for every mutating request.
    """

    policy: str
    portfolio_session_id: UUID | None
    generation_run_id: UUID | None
    successful_run_id: UUID | None
    consumed_at: datetime | None
    can_create_portfolio: bool
    can_start_generation: bool
    can_retry_generation: bool
    can_regenerate: bool
    read_only: bool
    revision: int


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """The minimum local identity projection needed by Phase 1 routes."""

    id: UUID
    supabase_user_id: UUID
    username: str | None
    role: AuthRole
    status: AccountStatus
    entitlement: EntitlementProjection | None = None

    @property
    def onboarding_required(self) -> bool:
        return self.username is None

    @property
    def admin_available(self) -> bool:
        return self.role is AuthRole.ADMIN and self.status is AccountStatus.ACTIVE
