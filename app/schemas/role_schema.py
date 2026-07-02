"""
Contratos de entrada/saída para `Role` (`/api/v1/roles`).
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
    """Payload de atualização parcial de uma role (todos os campos opcionais)."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class RoleRead(RoleBase):
    """
    Representação pública de uma role, incluindo suas permissões.

    O campo `permissions` é sempre retornado — clientes que só precisam
    do nome/descrição podem simplesmente ignorá-lo, evitando a
    necessidade de um schema `RoleSummary` adicional não previsto na
    especificação.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    permissions: list[PermissionRead] = Field(default_factory=list)


class AssignRoleRequest(BaseModel):
    """Payload para atribuir uma role existente a um usuário."""

    role_id: uuid.UUID
