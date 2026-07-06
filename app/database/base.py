"""
Base declarativa do SQLAlchemy e mixins reutilizáveis para os models.

Responsável apenas pelo mapeamento ORM (estilo Mapped/mapped_column).
Nenhuma regra de negócio deve ficar aqui dentro.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """
    Retorna o horário atual em UTC com timezone (aware).

    Substitui o `datetime.utcnow()` (que foi depreciado e era naive).
    Fica exportado publicamente para que qualquer modelo que precise
    de datas (como `RefreshToken` ou `Session`) use o mesmo padrão.
    """

    return datetime.now(UTC)


# Mantido apenas para compatibilidade interna do módulo.
_utcnow = utcnow


class Base(DeclarativeBase):
    """
    Classe base (Declarative Base) herdada por todos os modelos.
    Todas as entidades do banco de dados devem estender esta classe.
    """

    pass


class UUIDPrimaryKeyMixin:
    """Cria uma chave primária (PK) do tipo UUID gerada pelo app."""

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )


class TimestampMixin:
    """Cria os campos `created_at` e `updated_at` com atualização automática."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )


class SoftDeleteMixin:
    """Cria exclusão lógica via `deleted_at` para evitar o DELETE físico."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
