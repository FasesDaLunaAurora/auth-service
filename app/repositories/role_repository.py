"""
Repositório de `Role`.

Assim como `UserRepository`, contém apenas operações de persistência —
a decisão de, por exemplo, impedir a exclusão de uma role em uso por
usuários ativos é do `role_service.py` (Etapa 6), não deste módulo.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission_model import Permission
from app.models.role_model import Role


class RoleRepository:
    """Acesso a dados da entidade `Role`, isolado de regras de negócio."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, role_id: uuid.UUID) -> Role | None:
        stmt = select(Role).where(Role.id == role_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name.strip())
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_name(self, name: str) -> bool:
        stmt = select(func.count()).select_from(Role).where(Role.name == name.strip())
        result = await self._db.execute(stmt)
        return (result.scalar_one() or 0) > 0

    async def create(self, role: Role) -> Role:
        self._db.add(role)
        await self._db.flush()
        # Garante que `.permissions` esteja carregado (vazio, para uma
        # role recém-criada) antes de devolver o objeto — sem isso,
        # serializar a resposta com `RoleRead.model_validate(role)`
        # (que inclui `permissions`) na camada de API pode disparar o
        # mesmo `MissingGreenlet` já visto em `assign_permission`.
        await self._db.refresh(role, attribute_names=["permissions"])
        return role

    async def update(self, role: Role) -> Role:
        await self._db.flush()
        return role

    async def delete(self, role: Role) -> None:
        """
        Exclusão física.

        Diferente de `User`, a especificação (Seção 5) não define
        exclusão lógica para `Role` — optei por `DELETE` físico real,
        já que roles não carregam histórico de auditoria individual (o
        histórico de quem teve qual permissão fica nos logs de
        auditoria, não na tabela `roles`). Decisão registrada no
        changelog.
        """
        await self._db.delete(role)
        await self._db.flush()

    async def list_all(self, *, page: int, page_size: int) -> tuple[list[Role], int]:
        count_result = await self._db.execute(select(func.count()).select_from(Role))
        total = count_result.scalar_one()

        stmt = (
            select(Role)
            .order_by(Role.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    # Nota: `role.permissions` é acessada por `assign_permission` e
    # `remove_permission` logo abaixo. Sem um `refresh()` explícito
    # antes desse acesso, uma `Role` cuja coleção não tenha sido
    # populada pela consulta que a originou (ex: uma role recém-criada
    # e apenas `flush()`ada, ou dependendo da versão do SQLAlchemy)
    # pode disparar uma tentativa de lazy-load síncrona ao acessar
    # `.permissions` — o que falha com `MissingGreenlet` sobre um
    # engine assíncrono, mesmo com `lazy="selectin"` configurado no
    # model (Etapa 2). `session.refresh()` é assíncrono e seguro aqui.
    async def assign_permission(self, role: Role, permission: Permission) -> bool:
        """
        Adiciona uma permissão à coleção de permissões da role, se ainda
        não presente. Retorna `True` se a atribuição foi de fato nova,
        `False` se a permissão já estava atribuída — assim, chamadores
        (services, scripts) nunca precisam acessar `role.permissions`
        diretamente para saber se algo mudou.
        """
        await self._db.refresh(role, attribute_names=["permissions"])
        if permission not in role.permissions:
            role.permissions.append(permission)
            await self._db.flush()
            return True
        return False

    async def remove_permission(self, role: Role, permission: Permission) -> bool:
        """Remove uma permissão da role, se presente. Ver `assign_permission`."""
        await self._db.refresh(role, attribute_names=["permissions"])
        if permission in role.permissions:
            role.permissions.remove(permission)
            await self._db.flush()
            return True
        return False