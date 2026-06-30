"""
Schema base compartilhado por todos os schemas Pydantic do projeto.

Centraliza configurações comuns (ex: `from_attributes=True` para
serialização a partir de modelos ORM) e utilitários de resposta
padronizados exigidos pela Seção 6 (envelope de erro e paginação).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class AppBaseModel(BaseModel):
    """
    Base de todos os schemas de entrada e saída.

    `populate_by_name=True` permite usar tanto o alias quanto o nome
    real do campo ao construir instâncias, facilitando testes.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class OrmBaseModel(AppBaseModel):
    """
    Base para schemas de *resposta* que são construídos a partir
    de instâncias ORM (via `model_validate(orm_obj)`).

    `from_attributes=True` habilita o modo de leitura de atributos
    de objetos ORM, substituindo o antigo `orm_mode = True` do Pydantic v1.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


# ---------------------------------------------------------------------------
# Envelope de erro padronizado (Seção 6)
# ---------------------------------------------------------------------------

class ErrorDetail(AppBaseModel):
    """Detalhe interno de um erro (campo `details` do envelope)."""

    field: str | None = None
    message: str | None = None


class ErrorBody(AppBaseModel):
    """Corpo do objeto `error` no envelope de resposta."""

    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(AppBaseModel):
    """
    Envelope de erro padronizado exigido pela Seção 6:

    {
        "error": {
            "code": "INVALID_CREDENTIALS",
            "message": "E-mail ou senha incorretos.",
            "details": null
        }
    }
    """

    error: ErrorBody


# ---------------------------------------------------------------------------
# Resposta paginada genérica
# ---------------------------------------------------------------------------

class PaginationMeta(AppBaseModel):
    """Metadados de paginação incluídos em listagens."""

    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedResponse(AppBaseModel, Generic[T]):
    """
    Wrapper genérico para endpoints de listagem paginada.

    Uso: `PaginatedResponse[UserResponse]`
    """

    items: list[T]
    pagination: PaginationMeta


# ---------------------------------------------------------------------------
# Schemas de campos reutilizáveis
# ---------------------------------------------------------------------------

class UUIDResponse(OrmBaseModel):
    """Schema mínimo que retorna apenas o `id` de um recurso criado."""

    id: uuid.UUID


class TimestampSchema(OrmBaseModel):
    """Mixin de timestamps para schemas de resposta."""

    created_at: datetime
    updated_at: datetime
