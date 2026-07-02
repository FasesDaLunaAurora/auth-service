"""
Contratos de entrada/saída para `Permission` (`/api/v1/permissions`).
"""

from __future__ import annotations

import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

_PERMISSION_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$")


class PermissionBase(BaseModel):
    """Campos compartilhados entre criação e leitura de uma permissão."""

    code: str = Field(
        ...,
        min_length=3,
        max_length=150,
        description="Formato obrigatório: 'recurso:acao', ex: 'user:create'.",
    )
    description: str | None = Field(default=None, max_length=500)

    @field_validator("code")
    @classmethod
    def _validate_code_format(cls, value: str) -> str:
        """
        Garante que o código siga a convenção `recurso:acao`.

        Esta é validação de *formato* de input (responsabilidade da
        camada `schemas`), não uma regra de negócio — decidir se um
        código específico pode ou não ser criado (ex: duplicidade)
        continua em `permission_service`.
        """
        normalized = value.strip().lower()
        if not _PERMISSION_CODE_PATTERN.match(normalized):
            raise ValueError(
                "O código de permissão deve seguir o formato 'recurso:acao' "
                "(ex: 'user:create'), usando apenas letras minúsculas, "
                "números e underscore."
            )
        return normalized


class PermissionCreate(PermissionBase):
    """Payload de criação de uma nova permissão."""

    pass


class PermissionUpdate(BaseModel):
    """Payload de atualização parcial (todos os campos opcionais)."""

    description: str | None = Field(default=None, max_length=500)


class PermissionRead(PermissionBase):
    """Representação pública de uma permissão retornada pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


class AssignPermissionRequest(BaseModel):
    """Payload para atribuir uma permissão existente a uma role."""

    permission_id: uuid.UUID
