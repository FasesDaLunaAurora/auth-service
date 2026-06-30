"""
Schemas de Permission (Seção 6 — /api/v1/permissions).

Cobre o CRUD completo de permissions. O campo `code` segue a convenção
`resource:action` (ex: `user:create`, `role:delete`) definida em
`core/constants.py` (`DefaultPermission`).
"""

from __future__ import annotations

import re
import uuid

from pydantic import Field, field_validator

from app.schemas.base_schema import AppBaseModel, OrmBaseModel, PaginatedResponse

_CODE_RE = re.compile(r"^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class PermissionResponse(OrmBaseModel):
    """Representação pública completa de uma Permission."""

    id: uuid.UUID
    code: str
    description: str | None


PermissionListResponse = PaginatedResponse[PermissionResponse]


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreatePermissionRequest(AppBaseModel):
    """Criação de nova Permission — POST /permissions."""

    code: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Código no formato 'resource:action' (ex: 'user:create').",
    )
    description: str | None = Field(default=None, max_length=500)

    @field_validator("code")
    @classmethod
    def _validate_code_format(cls, value: str) -> str:
        if not _CODE_RE.match(value):
            raise ValueError(
                "O código da permissão deve seguir o formato 'resource:action' "
                "usando apenas letras minúsculas, números e underscores "
                "(ex: 'user:create', 'report:export')."
            )
        return value


class UpdatePermissionRequest(AppBaseModel):
    """Atualização parcial de Permission — PATCH /permissions/{id}."""

    description: str | None = Field(default=None, max_length=500)

    # Decisão de implementação: o `code` de uma permission não é atualizável
    # após a criação. Mudar o code quebraria silenciosamente qualquer role
    # que dependa dele, já que as referências são por UUID (não por code).
    # A correção de um code errado deve ser feita excluindo e recriando
    # a permission.
