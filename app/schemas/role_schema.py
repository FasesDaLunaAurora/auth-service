"""
Schemas de Role (Seção 6 — /api/v1/roles).

Cobre CRUD completo de roles e os endpoints de:
  - atribuição/remoção de roles a um usuário
  - atribuição/remoção de permissions a uma role
"""

from __future__ import annotations

import uuid

from pydantic import Field

from app.schemas.base_schema import AppBaseModel, OrmBaseModel, PaginatedResponse


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class PermissionMinimalResponse(OrmBaseModel):
    """Representação mínima de Permission, embutida em respostas de Role."""

    id: uuid.UUID
    code: str
    description: str | None


class RoleResponse(OrmBaseModel):
    """Representação pública completa de um Role."""

    id: uuid.UUID
    name: str
    description: str | None
    permissions: list[PermissionMinimalResponse] = []


RoleListResponse = PaginatedResponse[RoleResponse]


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateRoleRequest(AppBaseModel):
    """Criação de novo Role — POST /roles."""

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9_\-]+$",
        description="Nome do role em lowercase snake_case (ex: 'admin', 'support_agent').",
    )
    description: str | None = Field(default=None, max_length=500)


class UpdateRoleRequest(AppBaseModel):
    """Atualização parcial de Role — PATCH /roles/{id}."""

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9_\-]+$",
    )
    description: str | None = Field(default=None, max_length=500)


# ---------------------------------------------------------------------------
# Atribuição de roles a usuários
# ---------------------------------------------------------------------------

class AssignRoleRequest(AppBaseModel):
    """
    Atribui um ou mais roles a um usuário — POST /users/{id}/roles.

    Decisão de implementação: aceitar uma lista de `role_ids` em vez de
    um único ID por request reduz a quantidade de chamadas HTTP necessárias
    para configurar um usuário com múltiplos roles.
    """

    role_ids: list[uuid.UUID] = Field(..., min_length=1)


class RevokeRoleRequest(AppBaseModel):
    """Remove um ou mais roles de um usuário — DELETE /users/{id}/roles."""

    role_ids: list[uuid.UUID] = Field(..., min_length=1)


class RoleAssignmentResponse(AppBaseModel):
    """Confirmação de atribuição/remoção de roles."""

    message: str
    user_id: uuid.UUID
    affected_roles: list[uuid.UUID]


# ---------------------------------------------------------------------------
# Atribuição de permissions a roles
# ---------------------------------------------------------------------------

class AssignPermissionToRoleRequest(AppBaseModel):
    """Atribui uma ou mais permissions a um role — POST /roles/{id}/permissions."""

    permission_ids: list[uuid.UUID] = Field(..., min_length=1)


class RevokePermissionFromRoleRequest(AppBaseModel):
    """Remove uma ou mais permissions de um role — DELETE /roles/{id}/permissions."""

    permission_ids: list[uuid.UUID] = Field(..., min_length=1)


class PermissionAssignmentResponse(AppBaseModel):
    """Confirmação de atribuição/remoção de permissions em um role."""

    message: str
    role_id: uuid.UUID
    affected_permissions: list[uuid.UUID]
