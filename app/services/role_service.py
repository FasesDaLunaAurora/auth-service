"""
Regras de negócio de Roles e RBAC (controle de acesso baseado em perfis).
"""

from __future__ import annotations

import uuid

from app.exceptions.base_exception import ResourceNotFoundError, ValidationConflictError
from app.models.role_model import Role
from app.models.user_model import User
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.role_schema import RoleCreate, RoleUpdate


class RoleService:
    def __init__(
        self,
        role_repository: RoleRepository,
        permission_repository: PermissionRepository,
        user_repository: UserRepository,
    ) -> None:
        self._roles = role_repository
        self._permissions = permission_repository
        self._users = user_repository

    async def get_by_id_or_raise(self, role_id: uuid.UUID) -> Role:
        role = await self._roles.get_by_id(role_id)
        if role is None:
            raise ResourceNotFoundError("Role")
        return role

    async def create_role(self, payload: RoleCreate) -> Role:
        if await self._roles.exists_by_name(payload.name):
            raise ValidationConflictError(f"Já existe uma role com o nome '{payload.name}'.")
        role = Role(name=payload.name, description=payload.description)
        await self._roles.create(role)
        return role

    async def update_role(self, role_id: uuid.UUID, payload: RoleUpdate) -> Role:
        role = await self.get_by_id_or_raise(role_id)
        if payload.name is not None and payload.name != role.name:
            if await self._roles.exists_by_name(payload.name):
                raise ValidationConflictError(f"Já existe uma role com o nome '{payload.name}'.")
            role.name = payload.name
        if payload.description is not None:
            role.description = payload.description
        await self._roles.update(role)
        return role

    async def delete_role(self, role_id: uuid.UUID) -> None:
        role = await self.get_by_id_or_raise(role_id)
        await self._roles.delete(role)

    async def list_roles(self, *, page: int, page_size: int) -> tuple[list[Role], int]:
        return await self._roles.list_all(page=page, page_size=page_size)

    async def assign_permission(self, role_id: uuid.UUID, permission_id: uuid.UUID) -> Role:
        """Atribui uma permissão a uma role (`role:assign`)."""
        role = await self.get_by_id_or_raise(role_id)
        permission = await self._permissions.get_by_id(permission_id)
        if permission is None:
            raise ResourceNotFoundError("Permissão")
        await self._roles.assign_permission(role, permission)
        return role

    async def revoke_permission(self, role_id: uuid.UUID, permission_id: uuid.UUID) -> Role:
        """Remove uma permissão de uma role (`role:assign`)."""
        role = await self.get_by_id_or_raise(role_id)
        permission = await self._permissions.get_by_id(permission_id)
        if permission is None:
            raise ResourceNotFoundError("Permissão")
        await self._roles.remove_permission(role, permission)
        return role

    async def assign_role_to_user(self, user_id: uuid.UUID, role_id: uuid.UUID) -> User:
        """Atribui uma role a um usuário (`role:assign`)."""
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise ResourceNotFoundError("Usuário")
        role = await self.get_by_id_or_raise(role_id)
        await self._users.assign_role(user, role)
        return user

    async def revoke_role_from_user(self, user_id: uuid.UUID, role_id: uuid.UUID) -> User:
        """Remove uma role de um usuário (`role:assign`)."""
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise ResourceNotFoundError("Usuário")
        role = await self.get_by_id_or_raise(role_id)
        await self._users.remove_role(user, role)
        return user

    @staticmethod
    def user_has_permission(user: User, permission_code: str) -> bool:
        """
        Verifica se o usuário tem uma permissão (direta ou por meio de seus perfis).

        Superusuários (`is_superuser=True`) têm acesso livre e sempre passam por
        essa checagem. Usado no sistema de dependências de permissão da API.
        """

        if user.is_superuser:
            return True
        return any(
            permission.code == permission_code
            for role in user.roles
            for permission in role.permissions
        )
