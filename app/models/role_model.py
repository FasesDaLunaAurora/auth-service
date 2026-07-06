"""
Modelo de Role e tabelas de relacionamento (N:N) do RBAC.

As tabelas associativas (`user_roles` e `role_permissions`) usam o padrão
`Table` do Core por conterem apenas FKs, dispensando um modelo ORM próprio.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.permission_model import Permission
    from app.models.user_model import User

# --- Tabela associativa: usuário <-> roles ---
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# --- Tabela associativa: role <-> permissions ---
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Role(UUIDPrimaryKeyMixin, Base):
    """
    Papel (Role) do usuário que agrupa permissões do sistema.
    O modelo segue um padrão RBAC simples, sem hierarquia ou herança entre os papéis.
    """

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), default=None, nullable=True)

    users: Mapped[list[User]] = relationship(
        secondary=user_roles,
        back_populates="roles",
        lazy="selectin",
    )
    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Role id={self.id} name={self.name!r}>"
