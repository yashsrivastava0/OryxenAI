"""Phase 1 current-user and username onboarding routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from oryxenai.api.dependencies import get_auth_service, get_bearer_token, get_current_user
from oryxenai.auth.domain import CurrentUser
from oryxenai.auth.schemas import MeResponse, UsernameRequest
from oryxenai.auth.service import AuthService

router = APIRouter(prefix="/me", tags=["auth"])


@router.get("", response_model=MeResponse)
async def get_me(user: CurrentUser = Depends(get_current_user)) -> MeResponse:
    return MeResponse.from_current_user(user)


@router.put("/username", response_model=MeResponse)
async def claim_username(
    body: UsernameRequest,
    token: str = Depends(get_bearer_token),
    service: AuthService = Depends(get_auth_service),
) -> MeResponse:
    user = await service.claim_username(token, body.username)
    return MeResponse.from_current_user(user)
