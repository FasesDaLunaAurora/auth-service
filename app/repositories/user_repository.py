"""
Repositório de `User`.

Regra de camada (Seção 3): este módulo contém apenas
`SELECT`/`INSERT`/`UPDATE`/`DELETE` via SQLAlchemy. Nenhuma decisão de
negócio vive aqui — por exemplo, este repositório sabe *como* persistir
um bloqueio de conta (`set_lock`), mas não decide *quando* bloquear
(isso é responsabilidade de `app/services/auth_service.py`, Etapa 6).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role_model import Role
from app.models.user_model import User


class UserRepository:
    """Acesso a dados da entidade `User`, isolado de regras de negócio."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, user_id: uuid.UUID, *, include_deleted: bool = False) -> User | None:
        """Busca um usuário por ID. Por padrão, ignora usuários com exclusão lógica."""
        stmt = select(User).where(User.id == user_id)
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, *, include_deleted: bool = False) -> User | None:
        """
        Busca um usuário pelo e-mail (já normalizado em minúsculas pelo
        `@validates` do model — aqui apenas normalizamos defensivamente
        de novo, para o caso de o chamador passar um valor não tratado).
        """
        stmt = select(User).where(User.email == email.strip().lower())
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_email(self, email: str) -> bool:
        """Verifica existência por e-mail sem carregar a entidade completa."""
        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.email == email.strip().lower(), User.deleted_at.is_(None))
        )
        result = await self._db.execute(stmt)
        return (result.scalar_one() or 0) > 0

    async def create(self, user: User) -> User:
        """Persiste um novo usuário e sincroniza o ID gerado (`flush`, sem `commit`)."""
        self._db.add(user)
        await self._db.flush()
        # Mesma proteção aplicada em `RoleRepository.create()`: garante
        # que `.roles` esteja carregado (vazio) antes de o objeto ser
        # devolvido, prevenindo `MissingGreenlet` caso algum chamador
        # futuro serialize `UserRead` (que inclui `roles`) logo após a
        # criação, sem passar por uma consulta real antes.
        await self._db.refresh(user, attribute_names=["roles"])
        return user

    async def update(self, user: User) -> User:
        """
        Marca o objeto (já anexado à sessão) como sujo e sincroniza.

        Como `user` normalmente já foi carregado da própria sessão
        (`get_by_id`), esta operação em geral é redundante com o
        autoflush do SQLAlchemy — mantida explícita para deixar o
        contrato do repositório claro para quem lê a camada de serviço.
        """
        await self._db.flush()
        return user

    async def soft_delete(self, user: User, *, deleted_at: datetime) -> None:
        """Aplica exclusão lógica, preservando o registro para auditoria/integridade."""
        user.deleted_at = deleted_at
        await self._db.flush()

    async def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        """
        Lista usuários paginados, com filtro opcional por e-mail ou nome.

        Retorna `(items, total)` para que o Service monte o envelope de
        paginação (`UserListResponse`) sem o Repository precisar
        conhecer o formato de resposta HTTP.
        """
        base_stmt = select(User).where(User.deleted_at.is_(None))
        count_stmt = select(func.count()).select_from(User).where(User.deleted_at.is_(None))

        if search:
            pattern = f"%{search.strip().lower()}%"
            filter_clause = or_(
                func.lower(User.email).like(pattern),
                func.lower(User.full_name).like(pattern),
            )
            base_stmt = base_stmt.where(filter_clause)
            count_stmt = count_stmt.where(filter_clause)

        total_result = await self._db.execute(count_stmt)
        total = total_result.scalar_one()

        paginated_stmt = (
            base_stmt.order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._db.execute(paginated_stmt)
        items = list(result.scalars().all())
        return items, total

    async def set_lock(self, user: User, *, locked_until: datetime | None) -> None:
        """Persiste (ou limpa, se `None`) o bloqueio temporário de força bruta."""
        user.locked_until = locked_until
        await self._db.flush()

    async def increment_failed_attempts(self, user: User) -> int:
        """Incrementa e persiste o contador de tentativas de login falhas."""
        user.failed_login_attempts += 1
        await self._db.flush()
        return user.failed_login_attempts

    async def reset_failed_attempts(self, user: User) -> None:
        """Zera o contador de tentativas falhas (chamado após login bem-sucedido)."""
        user.failed_login_attempts = 0
        await self._db.flush()

    # Ver nota de decisão equivalente em
    # `RoleRepository.assign_permission` sobre por que o `refresh()`
    # explícito abaixo é necessário para evitar `MissingGreenlet`.
    async def assign_role(self, user: User, role: Role) -> bool:
        """Adiciona uma role ao usuário, se ainda não presente. Retorna se foi nova."""
        await self._db.refresh(user, attribute_names=["roles"])
        if role not in user.roles:
            user.roles.append(role)
            await self._db.flush()
            return True
        return False

    async def remove_role(self, user: User, role: Role) -> bool:
        """Remove uma role da coleção de roles do usuário, se presente. Retorna se foi removida."""
        await self._db.refresh(user, attribute_names=["roles"])
        if role in user.roles:
            user.roles.remove(role)
            await self._db.flush()
            return True
        return False
