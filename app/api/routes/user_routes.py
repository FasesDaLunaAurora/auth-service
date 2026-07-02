"""
Rotas de usuários (`/api/v1/users`, Seção 6).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.auth_dependency import CurrentUser
from app.api.dependencies.db_dependency import RoleServiceDep, UserServiceDep
from app.api.dependencies.permission_dependency import require_permission
from app.core.constants import PermissionCode
from app.schemas.role_schema import AssignRoleRequest, RoleRead
from app.schemas.user_schema import (
    ChangePasswordRequest,
    UserAdminUpdate,
    UserListResponse,
    UserRead,
    UserUpdateMe,
)

router = APIRouter(prefix="/users", tags=["Users"])


# --- Perfil próprio (qualquer usuário autenticado, sem permissão RBAC extra) ---


@router.get("/me", response_model=UserRead, summary="Retorna o usuário autenticado")
async def get_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead, summary="Atualiza o perfil próprio")
async def update_me(
    payload: UserUpdateMe, current_user: CurrentUser, user_service: UserServiceDep
) -> UserRead:
    user = await user_service.update_me(current_user, payload)
    return UserRead.model_validate(user)


@router.patch(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Altera a própria senha",
)
async def change_my_password(
    payload: ChangePasswordRequest, current_user: CurrentUser, user_service: UserServiceDep
) -> None:
    await user_service.change_password(current_user, payload)


# --- Administração de usuários (cada rota declara sua própria permissão RBAC) ---


@router.get(
    "",
    response_model=UserListResponse,
    dependencies=[Depends(require_permission(PermissionCode.USER_LIST))],
    summary="Lista usuários (paginado)",
)
async def list_users(
    user_service: UserServiceDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=255),
) -> UserListResponse:
    items, total = await user_service.list_users(page=page, page_size=page_size, search=search)
    return UserListResponse(
        items=[UserRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_permission(PermissionCode.USER_READ))],
    summary="Detalhe de um usuário",
)
async def get_user(user_id: uuid.UUID, user_service: UserServiceDep) -> UserRead:
    user = await user_service.get_by_id_or_raise(user_id)
    return UserRead.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_permission(PermissionCode.USER_UPDATE))],
    summary="Atualiza um usuário",
)
async def admin_update_user(
    user_id: uuid.UUID, payload: UserAdminUpdate, user_service: UserServiceDep
) -> UserRead:
    user = await user_service.admin_update(user_id, payload)
    return UserRead.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(PermissionCode.USER_DELETE))],
    summary="Exclusão lógica de um usuário",
)
async def delete_user(
    user_id: uuid.UUID, current_user: CurrentUser, user_service: UserServiceDep
) -> None:
    await user_service.soft_delete(user_id, requesting_user_id=current_user.id)


@router.post(
    "/{user_id}/activate",
    response_model=UserRead,
    dependencies=[Depends(require_permission(PermissionCode.USER_UPDATE))],
    summary="Ativa a conta de um usuário",
)
async def activate_user(user_id: uuid.UUID, user_service: UserServiceDep) -> UserRead:
    user = await user_service.activate(user_id)
    return UserRead.model_validate(user)


@router.post(
    "/{user_id}/deactivate",
    response_model=UserRead,
    dependencies=[Depends(require_permission(PermissionCode.USER_UPDATE))],
    summary="Desativa a conta de um usuário",
)
async def deactivate_user(
    user_id: uuid.UUID, current_user: CurrentUser, user_service: UserServiceDep
) -> UserRead:
    user = await user_service.deactivate(user_id, requesting_user_id=current_user.id)
    return UserRead.model_validate(user)


# --- Atribuição de roles a um usuário (RBAC) ---
#
# Hospedadas aqui (em vez de `role_routes.py`) porque o path começa em
# `/users/{id}/...` (Seção 6 não fixa este contrato — ver nota em
# `audit_middleware.py`, Etapa 7) — mantém a convenção REST de que o
# path reflete o recurso "pai" da URL.


@router.post(
    "/{user_id}/roles",
    response_model=RoleRead,
    dependencies=[Depends(require_permission(PermissionCode.ROLE_ASSIGN))],
    summary="Atribui uma role a um usuário",
)
async def assign_role_to_user(
    user_id: uuid.UUID, payload: AssignRoleRequest, role_service: RoleServiceDep
) -> RoleRead:
    await role_service.assign_role_to_user(user_id, payload.role_id)
    role = await role_service.get_by_id_or_raise(payload.role_id)
    return RoleRead.model_validate(role)


@router.delete(
    "/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(PermissionCode.ROLE_ASSIGN))],
    summary="Remove uma role de um usuário",
)
async def revoke_role_from_user(
    user_id: uuid.UUID, role_id: uuid.UUID, role_service: RoleServiceDep
) -> None:
    await role_service.revoke_role_from_user(user_id, role_id)
