"""Schemas para o gerenciamento de permissões."""

from __future__ import annotations

import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

_PERMISSION_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$")


class PermissionBase(BaseModel):
    """Campos base compartilhados pelas permissões do sistema."""

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
        Valida se o código segue o padrão `recurso:acao`.

        Isso é apenas uma checagem de formato da API (camada schemas),
        não uma regra de negócio. Validar se o código já existe ou se
        pode ser criado é responsabilidade do `permission_service`.
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
    """
    Payload de criação de uma nova permissão.
    Classe só herda por enquanto, mas pode ser estendida no futuro
    se houver campos adicionais.
    """

    pass


class PermissionUpdate(BaseModel):
    """Campos para atualização parcial (tudo opcional)."""

    description: str | None = Field(default=None, max_length=500)


class PermissionRead(PermissionBase):
    """Dados da permissão expostos publicamente pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


class AssignPermissionRequest(BaseModel):
    """Dados necessários para associar uma permissão a um perfil (role)."""

    permission_id: uuid.UUID
