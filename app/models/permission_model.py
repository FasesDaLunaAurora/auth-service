"""
Modelo de Permissão (RBAC).
Cada permissão é um código granular (ex: `user:create`, `role:assign`)
utilizado pelas dependências da API para controle de acesso.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin
from app.models.role_model import role_permissions

if TYPE_CHECKING:
    from app.models.role_model import Role


class Permission(UUIDPrimaryKeyMixin, Base):
    """
    Permissão granular do sistema (ex: `user:create`).

    O campo `code` segue o padrão `recurso:acao`, usado nas constantes
    do sistema e nos decorators de autorização das rotas.
    """

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), default=None, nullable=True)

    roles: Mapped[list[Role]] = relationship(
        secondary=role_permissions,
        back_populates="permissions",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover
        # "pragma: no cover" ignora cobertura de testes, use com cuidado,
        # esse método é só para debug, por isso está sendo desconsiderado.
        return f"<Permission id={self.id} code={self.code!r}>"
