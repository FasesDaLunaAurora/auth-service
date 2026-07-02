"""
Repositório de `Permission`.

Contém apenas operações de persistência sobre a entidade `Permission`.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission_model import Permission


class PermissionRepository:
    """Acesso a dados da entidade `Permission`, isolado de regras de negócio."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, permission_id: uuid.UUID) -> Permission | None:
        stmt = select(Permission).where(Permission.id == permission_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Permission | None:
        stmt = select(Permission).where(Permission.code == code.strip().lower())
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_codes(self, codes: list[str]) -> list[Permission]:
        """Busca múltiplas permissões por código de uma vez (usado em seeds/testes)."""
        normalized = [c.strip().lower() for c in codes]
        stmt = select(Permission).where(Permission.code.in_(normalized))
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def exists_by_code(self, code: str) -> bool:
        stmt = select(func.count()).select_from(Permission).where(
            Permission.code == code.strip().lower()
        )
        result = await self._db.execute(stmt)
        return (result.scalar_one() or 0) > 0

    async def create(self, permission: Permission) -> Permission:
        self._db.add(permission)
        await self._db.flush()
        return permission

    async def update(self, permission: Permission) -> Permission:
        await self._db.flush()
        return permission

    async def delete(self, permission: Permission) -> None:
        """
        Exclusão física.

        Mesma decisão aplicada a `Role`: a especificação não define
        exclusão lógica para `Permission` na Seção 5.
        """
        await self._db.delete(permission)
        await self._db.flush()

    async def list_all(self, *, page: int, page_size: int) -> tuple[list[Permission], int]:
        count_result = await self._db.execute(select(func.count()).select_from(Permission))
        total = count_result.scalar_one()

        stmt = (
            select(Permission)
            .order_by(Permission.code.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total
