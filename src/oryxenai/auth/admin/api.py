"""Administrator console API; every route is server-authorized."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from oryxenai.agents.code_generator.service import CodeGeneratorService
from oryxenai.api.dependencies import (
    get_admin_service,
    get_code_generator_service,
    require_admin,
)
from oryxenai.auth.admin.schemas import (
    AdminActionRequest,
    AdminOperationResponse,
    AdminPage,
)
from oryxenai.auth.admin.service import AdminService
from oryxenai.auth.domain import CurrentUser

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", ""))


def _key(request: Request) -> str:
    return request.headers.get("Idempotency-Key", "")


def _operation_response(operation: Any) -> AdminOperationResponse:
    return AdminOperationResponse(
        id=operation.id,
        action=operation.action,
        target_type=operation.target_type,
        target_id=operation.target_id,
        status=operation.status,
        step=operation.step,
        attempt_count=operation.attempt_count,
        last_error_code=operation.last_error_code,
        created_at=operation.created_at,
        updated_at=operation.updated_at,
        completed_at=operation.completed_at,
        safe_state=operation.safe_state,
    )


@router.get("/summary")
async def summary(service: AdminService = Depends(get_admin_service)) -> dict[str, Any]:
    return await service.summary()


@router.get("/users", response_model=AdminPage)
async def users(
    limit: int = 25,
    cursor: str | None = None,
    service: AdminService = Depends(get_admin_service),
) -> AdminPage:
    return AdminPage(**await service.users(limit=limit, cursor=cursor))


@router.get("/users/{user_id}")
async def user(user_id: UUID, service: AdminService = Depends(get_admin_service)) -> dict[str, Any]:
    return await service.user(user_id)


@router.get("/deleted-identities", response_model=AdminPage)
async def deleted_identities(
    limit: int = 25,
    cursor: str | None = None,
    service: AdminService = Depends(get_admin_service),
) -> AdminPage:
    return AdminPage(**await service.deleted_identities(limit=limit, cursor=cursor))


@router.get("/projects", response_model=AdminPage)
async def projects(
    limit: int = 25,
    cursor: str | None = None,
    service: AdminService = Depends(get_admin_service),
) -> AdminPage:
    return AdminPage(**await service.projects(limit=limit, cursor=cursor, legacy=False))


@router.get("/projects/{session_id}")
async def project(
    session_id: UUID, service: AdminService = Depends(get_admin_service)
) -> dict[str, Any]:
    return await service.project(session_id)


@router.get("/legacy-projects", response_model=AdminPage)
async def legacy_projects(
    limit: int = 25,
    cursor: str | None = None,
    service: AdminService = Depends(get_admin_service),
) -> AdminPage:
    return AdminPage(**await service.projects(limit=limit, cursor=cursor, legacy=True))


@router.get("/audit-events", response_model=AdminPage)
async def audit_events(
    limit: int = 25,
    cursor: str | None = None,
    service: AdminService = Depends(get_admin_service),
) -> AdminPage:
    return AdminPage(**await service.audit_events(limit=limit, cursor=cursor))


@router.get("/operations/{operation_id}", response_model=AdminOperationResponse)
async def operation(
    operation_id: UUID, service: AdminService = Depends(get_admin_service)
) -> AdminOperationResponse:
    return _operation_response(await service.operation(operation_id))


@router.post(
    "/users/{user_id}/suspend",
    response_model=AdminOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def suspend_user(
    user_id: UUID,
    body: AdminActionRequest,
    request: Request,
    current: CurrentUser = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
) -> AdminOperationResponse:
    return _operation_response(
        await service.suspend_user(
            actor_id=current.id,
            target_id=user_id,
            confirmation=body.confirmation,
            username=body.username,
            reason=body.reason,
            idempotency_key=_key(request),
            request_id=_request_id(request),
        )
    )


@router.post(
    "/users/{user_id}/restore",
    response_model=AdminOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def restore_user(
    user_id: UUID,
    body: AdminActionRequest,
    request: Request,
    current: CurrentUser = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
) -> AdminOperationResponse:
    return _operation_response(
        await service.restore_user(
            actor_id=current.id,
            target_id=user_id,
            confirmation=body.confirmation,
            username=body.username,
            reason=body.reason,
            idempotency_key=_key(request),
            request_id=_request_id(request),
        )
    )


@router.post(
    "/users/{user_id}/delete",
    response_model=AdminOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def delete_user(
    user_id: UUID,
    body: AdminActionRequest,
    request: Request,
    current: CurrentUser = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
) -> AdminOperationResponse:
    return _operation_response(
        await service.delete_user(
            actor_id=current.id,
            target_id=user_id,
            confirmation=body.confirmation,
            username=body.username,
            reason=body.reason,
            idempotency_key=_key(request),
            request_id=_request_id(request),
        )
    )


@router.post(
    "/users/{user_id}/entitlement/reset",
    response_model=AdminOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reset_entitlement(
    user_id: UUID,
    body: AdminActionRequest,
    request: Request,
    current: CurrentUser = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
) -> AdminOperationResponse:
    return _operation_response(
        await service.reset_entitlement(
            actor_id=current.id,
            target_id=user_id,
            confirmation=body.confirmation,
            username=body.username,
            reason=body.reason,
            idempotency_key=_key(request),
            request_id=_request_id(request),
        )
    )


@router.post(
    "/users/{user_id}/promote",
    response_model=AdminOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def promote_user(
    user_id: UUID,
    body: AdminActionRequest,
    request: Request,
    current: CurrentUser = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
) -> AdminOperationResponse:
    return _operation_response(
        await service.promote_user(
            actor_id=current.id,
            target_id=user_id,
            confirmation=body.confirmation,
            username=body.username,
            reason=body.reason,
            idempotency_key=_key(request),
            request_id=_request_id(request),
        )
    )


@router.post(
    "/users/{user_id}/demote",
    response_model=AdminOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def demote_user(
    user_id: UUID,
    body: AdminActionRequest,
    request: Request,
    current: CurrentUser = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
) -> AdminOperationResponse:
    return _operation_response(
        await service.demote_user(
            actor_id=current.id,
            target_id=user_id,
            confirmation=body.confirmation,
            username=body.username,
            reason=body.reason,
            idempotency_key=_key(request),
            request_id=_request_id(request),
        )
    )


@router.post(
    "/deleted-identities/{tombstone_id}/readmit",
    response_model=AdminOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def readmit_identity(
    tombstone_id: UUID,
    body: AdminActionRequest,
    request: Request,
    current: CurrentUser = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
) -> AdminOperationResponse:
    return _operation_response(
        await service.readmit_identity(
            actor_id=current.id,
            target_id=tombstone_id,
            confirmation=body.confirmation,
            reason=body.reason,
            idempotency_key=_key(request),
            request_id=_request_id(request),
        )
    )


@router.post(
    "/projects/{session_id}/delete",
    response_model=AdminOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def delete_project(
    session_id: UUID,
    body: AdminActionRequest,
    request: Request,
    current: CurrentUser = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
) -> AdminOperationResponse:
    return _operation_response(
        await service.delete_project(
            actor_id=current.id,
            session_id=session_id,
            confirmation=body.confirmation,
            reason=body.reason,
            idempotency_key=_key(request),
            request_id=_request_id(request),
        )
    )


@router.post(
    "/legacy-projects/{session_id}/delete",
    response_model=AdminOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def delete_legacy_project(
    session_id: UUID,
    body: AdminActionRequest,
    request: Request,
    current: CurrentUser = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
) -> AdminOperationResponse:
    return _operation_response(
        await service.delete_project(
            actor_id=current.id,
            session_id=session_id,
            confirmation=body.confirmation,
            reason=body.reason,
            idempotency_key=_key(request),
            request_id=_request_id(request),
            legacy=True,
        )
    )


@router.post(
    "/operations/{operation_id}/resume",
    response_model=AdminOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def resume_operation(
    operation_id: UUID,
    request: Request,
    current: CurrentUser = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
) -> AdminOperationResponse:
    return _operation_response(
        await service.resume_operation(
            actor_id=current.id,
            operation_id=operation_id,
            idempotency_key=_key(request),
            request_id=_request_id(request),
        )
    )


@router.post(
    "/projects/{session_id}/code-generator/retry",
    response_model=AdminOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_code_generator(
    session_id: UUID,
    body: AdminActionRequest,
    request: Request,
    current: CurrentUser = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
    code_generator: CodeGeneratorService = Depends(get_code_generator_service),
) -> AdminOperationResponse:
    return _operation_response(
        await service.code_generator_command(
            actor_id=current.id,
            session_id=session_id,
            confirmation=body.confirmation,
            reason=body.reason,
            idempotency_key=_key(request),
            request_id=_request_id(request),
            action="code_generator_retry",
            callback=lambda: code_generator.retry(session_id, idempotency_key=_key(request)),
        )
    )


@router.post(
    "/projects/{session_id}/code-generator/regenerate",
    response_model=AdminOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def regenerate_code_generator(
    session_id: UUID,
    body: AdminActionRequest,
    request: Request,
    current: CurrentUser = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
    code_generator: CodeGeneratorService = Depends(get_code_generator_service),
) -> AdminOperationResponse:
    return _operation_response(
        await service.code_generator_command(
            actor_id=current.id,
            session_id=session_id,
            confirmation=body.confirmation,
            reason=body.reason,
            idempotency_key=_key(request),
            request_id=_request_id(request),
            action="code_generator_regenerate",
            callback=lambda: code_generator.regenerate(session_id, idempotency_key=_key(request)),
        )
    )
