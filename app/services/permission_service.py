"""
Regras de negócio para o gerenciamento de permissões (`/api/v1/permissions`).
"""

from __future__ import annotations

import uuid

from app.exceptions.base_exception import ResourceNotFoundError, ValidationConflictError
from app.models.permission_model import Permission
from app.repositories.permission_repository import PermissionRepository
from app.schemas.permission_schema import PermissionCreate, PermissionUpdate


class PermissionService:
    def __init__(self, permission_repository: PermissionRepository) -> None:
        self._permissions = permission_repository

    async def get_by_id_or_raise(self, permission_id: uuid.UUID) -> Permission:
        permission = await self._permissions.get_by_id(permission_id)
        if permission is None:
            raise ResourceNotFoundError("Permissão")
        return permission

    async def create_permission(self, payload: PermissionCreate) -> Permission:
        if await self._permissions.exists_by_code(payload.code):
            raise ValidationConflictError(f"Já existe uma permissão com o código '{payload.code}'.")
        permission = Permission(code=payload.code, description=payload.description)
        await self._permissions.create(permission)
        return permission

    async def update_permission(
        self, permission_id: uuid.UUID, payload: PermissionUpdate
    ) -> Permission:
        permission = await self.get_by_id_or_raise(permission_id)
        if payload.description is not None:
            permission.description = payload.description
        await self._permissions.update(permission)
        return permission

    async def delete_permission(self, permission_id: uuid.UUID) -> None:
        permission = await self.get_by_id_or_raise(permission_id)
        await self._permissions.delete(permission)

    async def list_permissions(self, *, page: int, page_size: int) -> tuple[list[Permission], int]:
        return await self._permissions.list_all(page=page, page_size=page_size)
