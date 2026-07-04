"""
Rotas de permissões (`/api/v1/permissions`, Seção 6) — CRUD completo.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.db_dependency import PermissionServiceDep
from app.api.dependencies.permission_dependency import require_permission
from app.core.constants import PermissionCode
from app.schemas.permission_schema import PermissionCreate, PermissionRead, PermissionUpdate

router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.post(
    "",
    response_model=PermissionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(PermissionCode.PERMISSION_CREATE))],
    summary="Cria uma nova permissão",
)
async def create_permission(
    payload: PermissionCreate, permission_service: PermissionServiceDep
) -> PermissionRead:
    permission = await permission_service.create_permission(payload)
    return PermissionRead.model_validate(permission)


@router.get(
    "",
    response_model=list[PermissionRead],
    dependencies=[Depends(require_permission(PermissionCode.PERMISSION_LIST))],
    summary="Lista permissões (paginado)",
)
async def list_permissions(
    permission_service: PermissionServiceDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> list[PermissionRead]:
    permissions, _total = await permission_service.list_permissions(page=page, page_size=page_size)
    return [PermissionRead.model_validate(permission) for permission in permissions]


@router.patch(
    "/{permission_id}",
    response_model=PermissionRead,
    dependencies=[Depends(require_permission(PermissionCode.PERMISSION_UPDATE))],
    summary="Atualiza a descrição de uma permissão",
)
async def update_permission(
    permission_id: uuid.UUID,
    payload: PermissionUpdate,
    permission_service: PermissionServiceDep,
) -> PermissionRead:
    permission = await permission_service.update_permission(permission_id, payload)
    return PermissionRead.model_validate(permission)


@router.delete(
    "/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(PermissionCode.PERMISSION_DELETE))],
    summary="Exclui uma permissão",
)
async def delete_permission(
    permission_id: uuid.UUID, permission_service: PermissionServiceDep
) -> None:
    await permission_service.delete_permission(permission_id)
