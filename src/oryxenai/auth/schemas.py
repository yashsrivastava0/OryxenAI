"""Public, deliberately minimal auth API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from oryxenai.auth.domain import CurrentUser


class MeResponse(BaseModel):
    id: str
    username: str | None
    role: str
    status: str
    onboarding_required: bool
    admin_available: bool

    @classmethod
    def from_current_user(cls, user: CurrentUser) -> MeResponse:
        return cls(
            id=str(user.id),
            username=user.username,
            role=user.role.value,
            status=user.status.value,
            onboarding_required=user.onboarding_required,
            admin_available=user.admin_available,
        )


class UsernameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str


def safe_me_dict(user: CurrentUser) -> dict[str, Any]:
    """Make the response boundary obvious to callers and tests."""
    return MeResponse.from_current_user(user).model_dump()
