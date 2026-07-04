"""
Entidade `Permission`.

Cada permissão é um código atômico e granular (ex: `user:create`,
`role:assign`), usado pela camada `api/dependencies/permission_dependency.py`
(Etapa 8) para autorização baseada em RBAC.
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
    Permissão granular do sistema (ex.: `user:create`, `session:revoke`).

    O campo `code` segue a convenção `recurso:acao`, usada de forma
    consistente em `app/core/constants.py::PermissionCode` e nos
    decorators de autorização das rotas (Etapa 8).
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
        return f"<Permission id={self.id} code={self.code!r}>"
