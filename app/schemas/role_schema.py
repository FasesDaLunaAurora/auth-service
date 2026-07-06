"""
Schemas de entrada e saída para as rotas de `Role` (`/api/v1/roles`).
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.permission_schema import PermissionRead


class RoleBase(BaseModel):
    """Campos compartilhados entre criação e leitura de uma role."""

    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class RoleCreate(RoleBase):
    """Payload de criação de uma nova role."""

    pass


class RoleUpdate(BaseModel):
    """Campos opcionais para atualização parcial de uma role."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class RoleRead(RoleBase):
    """
    Dados públicos de uma role e suas permissões associadas.

    O campo `permissions` sempre vem na resposta. Se o cliente só precisar
    do nome ou da descrição, basta ignorar essa lista. Assim evitamos criar
    um schema `RoleSummary` sem necessidade.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    permissions: list[PermissionRead] = Field(default_factory=list)


class AssignRoleRequest(BaseModel):
    """Payload para atribuir uma role existente a um usuário."""

    role_id: uuid.UUID
