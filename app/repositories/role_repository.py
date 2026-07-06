"""
Repositório de Roles (Papéis).
Gerencia exclusivamente a persistência e as consultas da tabela de papéis.
Validações de negócio, como impedir a exclusão de regras em uso, ficam nos services.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission_model import Permission
from app.models.role_model import Role


class RoleRepository:
    """Acesso a dados de papéis (roles), isolado das regras de negócio."""

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
        # Garante o carregamento do relacionamento de permissões para evitar
        # erros de carregamento assíncrono (MissingGreenlet) na serialização da API.

        await self._db.refresh(role, attribute_names=["permissions"])
        return role

    async def update(self, role: Role) -> Role:
        await self._db.flush()
        return role

    async def delete(self, role: Role) -> None:
        """
        Remove a role fisicamente do banco de dados.
        Seguindo a modelagem do sistema, papéis não utilizam exclusão lógica,
        já que o histórico de alterações fica registrado diretamente nos logs.
        """

        await self._db.delete(role)
        await self._db.flush()

    async def list_all(self, *, page: int, page_size: int) -> tuple[list[Role], int]:
        count_result = await self._db.execute(select(func.count()).select_from(Role))
        total = count_result.scalar_one()

        stmt = (
            select(Role).order_by(Role.name.asc()).offset((page - 1) * page_size).limit(page_size)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    # Atualiza os dados para carregar o relacionamento com segurança,
    # evitando quebras ao tentar acessar a lista de permissões.

    async def assign_permission(self, role: Role, permission: Permission) -> bool:
        """
        Vincula uma permissão ao papel (role), caso ainda não exista.

        Retorna `True` se for uma nova atribuição ou `False` se a permissão
        já estava associada, poupando validações manuais antes de salvar.
        """

        await self._db.refresh(role, attribute_names=["permissions"])
        if permission not in role.permissions:
            role.permissions.append(permission)
            await self._db.flush()
            return True
        return False

    async def remove_permission(self, role: Role, permission: Permission) -> bool:
        """Remove uma permissão da role, caso esteja associada, igual a `assign_permission`."""
        await self._db.refresh(role, attribute_names=["permissions"])
        if permission in role.permissions:
            role.permissions.remove(permission)
            await self._db.flush()
            return True
        return False
