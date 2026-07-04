"""
Base declarativa do SQLAlchemy 2.x e mixins reutilizáveis por `models`.

Nenhuma lógica de negócio deve viver aqui — apenas a infraestrutura de
mapeamento ORM (estilo `Mapped` / `mapped_column`) compartilhada entre
todas as entidades do domínio.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Retorna o horário atual em UTC, timezone-aware.

    Usado como `default`/`onupdate` em vez de `datetime.utcnow()` (que é
    naive e está deprecado), garantindo que todos os timestamps
    persistidos sejam consistentes e comparáveis entre si. Exportado
    (sem underscore) para que `models` que não usam `TimestampMixin`
    completo — como `RefreshToken` e `Session`, que só precisam de
    `created_at` — possam reutilizar o mesmo default.
    """
    return datetime.now(UTC)


# Alias privado mantido por compatibilidade interna deste módulo.
_utcnow = utcnow


class Base(DeclarativeBase):
    """
    Declarative base compartilhada por todos os `models` do serviço.

    Todas as entidades SQLAlchemy (Seção 5 da especificação) devem herdar
    desta classe, direta ou indiretamente via os mixins abaixo.
    """

    pass


class UUIDPrimaryKeyMixin:
    """Adiciona uma PK do tipo UUID, gerada no lado da aplicação."""

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )


class TimestampMixin:
    """Adiciona `created_at` / `updated_at` com gerenciamento automático."""

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
    """Adiciona exclusão lógica via `deleted_at` (nunca fazer DELETE físico de User)."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
