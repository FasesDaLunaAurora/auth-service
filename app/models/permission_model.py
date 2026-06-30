"""
Modelo de dados da entidade `Permission`.

Implementa todos os campos da Seção 5. O campo `code` segue a convenção
`resource:action` (ex: `user:create`, `user:delete`) definida nos exemplos
da especificação e no `DefaultPermission` de `core/constants.py`.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin


class Permission(UUIDPrimaryKeyMixin, Base):
    """
    Entidade de permissão granular no modelo RBAC.

    Cada `Permission` representa uma capacidade atômica (ex: `user:delete`)
    que pode ser associada a um ou mais `Role`. O acesso efetivo de um
    `User` é a união das permissões de todos os seus roles.
    """

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Código único no formato resource:action (ex: user:create)",
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # --- Relacionamentos ---
    roles: Mapped[list[Role]] = relationship(  # type: ignore[name-defined]
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Permission id={self.id} code={self.code!r}>"


# Resolvendo importação circular no final do módulo.
from app.models.role_model import Role  # noqa: E402, F401
