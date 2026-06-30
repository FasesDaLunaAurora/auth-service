"""
Base declarativa do SQLAlchemy 2.x e mixins comuns às entidades.

Decisão de implementação: criamos mixins (`UUIDPrimaryKeyMixin`,
`TimestampMixin`) não exigidos explicitamente pela especificação, mas
necessários para evitar duplicação, já que todas as entidades da Seção 5
compartilham PK em UUID e, na maioria dos casos, `created_at`/`updated_at`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    """Retorna o instante atual em UTC, usado como default de timestamps."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """
    Base declarativa única de todos os modelos ORM.

    Todas as classes em `app/models/*` devem herdar desta `Base`, garantindo
    que `Base.metadata` (usado pelo Alembic em `alembic/env.py`) conheça
    todas as tabelas do schema.
    """

    pass


class UUIDPrimaryKeyMixin:
    """Mixin que adiciona uma PK `id` do tipo UUID, gerada no servidor de aplicação."""

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """Mixin que adiciona `created_at` e `updated_at` com timezone, em UTC."""

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
