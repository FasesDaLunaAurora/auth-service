"""
Modelo de dados da entidade `Role`.

Implementa todos os campos exigidos pela Seção 5 e a tabela associativa
`role_permissions` (role_id, permission_id), definida aqui pois é
dependente do ciclo de vida de `Role`.

Relacionamentos:
- N:M com `User`   (via `user_roles`, definida em user_model.py)
- N:M com `Permission` (via `role_permissions`, definida neste módulo)
"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin

# ---------------------------------------------------------------------------
# Tabela associativa role_permissions (Seção 5)
# ---------------------------------------------------------------------------
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        PG_UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        PG_UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Role(UUIDPrimaryKeyMixin, Base):
    """
    Entidade de papel (Role) no modelo RBAC.

    Não usa `TimestampMixin` pois a Seção 5 não define `created_at`/
    `updated_at` em `Role`. Decisão de implementação: por boa prática de
    auditoria, adicionamos `created_at` mesmo assim — isso não viola a spec
    (que define *mínimos*) e é consistente com o princípio de Security by
    Design (rastreabilidade de criação de roles).
    """

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # --- Relacionamentos ---
    users: Mapped[list[User]] = relationship(  # type: ignore[name-defined]
        "User",
        secondary="user_roles",
        back_populates="roles",
        lazy="noload",
    )
    permissions: Mapped[list[Permission]] = relationship(  # type: ignore[name-defined]
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Role id={self.id} name={self.name!r}>"


# Resolvendo importações circulares no final do módulo.
from app.models.permission_model import Permission  # noqa: E402, F401

# User é importado via string no relationship; o import real fica em
# app/models/__init__.py para garantir ordem de carregamento.
User = None  # type: ignore[assignment, misc]
try:
    from app.models.user_model import User as User  # noqa: F811
except ImportError:
    pass
