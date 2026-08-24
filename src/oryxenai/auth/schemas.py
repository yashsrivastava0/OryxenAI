"""Public, deliberately minimal auth API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from oryxenai.auth.domain import CurrentUser


class MeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    username: str | None
    role: str
    status: str
    onboarding_required: bool
    admin_available: bool

    @classmethod
    def from_current_user(cls, user: CurrentUser) -> MeResponse:
        values: dict[str, Any] = {
            "id": str(user.id),
            "username": user.username,
            "role": user.role.value,
            "status": user.status.value,
            "onboarding_required": user.onboarding_required,
            "admin_available": user.admin_available,
        }
        if user.entitlement is not None:
            projection = user.entitlement
            values.update(
                policy=projection.policy,
                portfolio_session_id=(
                    str(projection.portfolio_session_id)
                    if projection.portfolio_session_id is not None
                    else None
                ),
                generation_run_id=(
                    str(projection.generation_run_id)
                    if projection.generation_run_id is not None
                    else None
                ),
                successful_run_id=(
                    str(projection.successful_run_id)
                    if projection.successful_run_id is not None
                    else None
                ),
                consumed_at=(
                    projection.consumed_at.isoformat()
                    if projection.consumed_at is not None
                    else None
                ),
                can_create_portfolio=projection.can_create_portfolio,
                can_start_generation=projection.can_start_generation,
                can_retry_generation=projection.can_retry_generation,
                can_regenerate=projection.can_regenerate,
                read_only=projection.read_only,
                revision=projection.revision,
            )
        return cls(**values)


class UsernameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str


def safe_me_dict(user: CurrentUser) -> dict[str, Any]:
    """Make the response boundary obvious to callers and tests."""
    return MeResponse.from_current_user(user).model_dump()
