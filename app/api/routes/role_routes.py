"""
Rotas de roles (`/api/v1/roles`, Seção 6) — CRUD completo + atribuição
de permissões a uma role.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.db_dependency import RoleServiceDep
from app.api.dependencies.permission_dependency import require_permission
from app.core.constants import PermissionCode
from app.schemas.permission_schema import AssignPermissionRequest
from app.schemas.role_schema import RoleCreate, RoleRead, RoleUpdate

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.post(
    "",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(PermissionCode.ROLE_CREATE))],
    summary="Cria uma nova role",
)
async def create_role(payload: RoleCreate, role_service: RoleServiceDep) -> RoleRead:
    role = await role_service.create_role(payload)
    return RoleRead.model_validate(role)


@router.get(
    "",
    response_model=list[RoleRead],
    dependencies=[Depends(require_permission(PermissionCode.ROLE_LIST))],
    summary="Lista roles (paginado)",
)
async def list_roles(
    role_service: RoleServiceDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> list[RoleRead]:
    roles, _total = await role_service.list_roles(page=page, page_size=page_size)
    return [RoleRead.model_validate(role) for role in roles]


@router.get(
    "/{role_id}",
    response_model=RoleRead,
    dependencies=[Depends(require_permission(PermissionCode.ROLE_READ))],
    summary="Detalhe de uma role",
)
async def get_role(role_id: uuid.UUID, role_service: RoleServiceDep) -> RoleRead:
    role = await role_service.get_by_id_or_raise(role_id)
    return RoleRead.model_validate(role)


@router.patch(
    "/{role_id}",
    response_model=RoleRead,
    dependencies=[Depends(require_permission(PermissionCode.ROLE_UPDATE))],
    summary="Atualiza uma role",
)
async def update_role(
    role_id: uuid.UUID, payload: RoleUpdate, role_service: RoleServiceDep
) -> RoleRead:
    role = await role_service.update_role(role_id, payload)
    return RoleRead.model_validate(role)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(PermissionCode.ROLE_DELETE))],
    summary="Exclui uma role",
)
async def delete_role(role_id: uuid.UUID, role_service: RoleServiceDep) -> None:
    await role_service.delete_role(role_id)


# --- Atribuição de permissões a uma role (ver nota de path em `audit_middleware.py`) ---


@router.post(
    "/{role_id}/permissions",
    response_model=RoleRead,
    dependencies=[Depends(require_permission(PermissionCode.PERMISSION_ASSIGN))],
    summary="Atribui uma permissão a uma role",
)
async def assign_permission_to_role(
    role_id: uuid.UUID, payload: AssignPermissionRequest, role_service: RoleServiceDep
) -> RoleRead:
    role = await role_service.assign_permission(role_id, payload.permission_id)
    return RoleRead.model_validate(role)


@router.delete(
    "/{role_id}/permissions/{permission_id}",
    response_model=RoleRead,
    dependencies=[Depends(require_permission(PermissionCode.PERMISSION_ASSIGN))],
    summary="Remove uma permissão de uma role",
)
async def revoke_permission_from_role(
    role_id: uuid.UUID, permission_id: uuid.UUID, role_service: RoleServiceDep
) -> RoleRead:
    role = await role_service.revoke_permission(role_id, permission_id)
    return RoleRead.model_validate(role)
