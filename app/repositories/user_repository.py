"""
Repositório de Usuários.

Centraliza as operações de consulta e persistência da tabela de usuários.

As validações de negócio, como determinar o momento exato de bloquear
ou desbloquear um acesso, ficam sob responsabilidade da camada de serviços.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role_model import Role
from app.models.user_model import User


class UserRepository:
    """Acesso a dados de usuários, isolado das regras de negócio."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, user_id: uuid.UUID, *, include_deleted: bool = False) -> User | None:
        """Busca um usuário por ID, desconsiderando contas removidas."""

        stmt = select(User).where(User.id == user_id)
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, *, include_deleted: bool = False) -> User | None:
        """
        Busca um usuário pelo e-mail.
        Ajusta o texto para letras minúsculas por segurança, garantindo a
        localização correta do registro mesmo se o valor enviado vier sem tratamento.
        """

        stmt = select(User).where(User.email == email.strip().lower())
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_email(self, email: str) -> bool:
        """Verifica se um e-mail já existe sem carregar todos os dados."""

        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.email == email.strip().lower(), User.deleted_at.is_(None))
        )
        result = await self._db.execute(stmt)
        return (result.scalar_one() or 0) > 0

    async def create(self, user: User) -> User:
        """Salva o usuário no banco e atualiza o ID gerado sem encerrar a transação."""
        self._db.add(user)
        await self._db.flush()
        # Carrega a lista de papéis (roles) para evitar erros de relacionamento
        # ao transformar o usuário em formato de resposta da API (JSON).

        await self._db.refresh(user, attribute_names=["roles"])
        return user

    async def update(self, user: User) -> User:
        """
        Sincroniza as alterações do usuário com o banco de dados.
        Força a atualização dos dados editados para garantir que as novas
        informações fiquem prontas para uso imediato.
        """

        await self._db.flush()
        return user

    async def soft_delete(self, user: User, *, deleted_at: datetime) -> None:
        """Aplica exclusão lógica, mantendo o registro no banco para histórico."""

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
        Lista usuários paginados com filtros opcionais de busca.
        Retorna a lista e o total de registros encontrados, deixando a
        formatação da resposta final por conta da camada superior.
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
        """Salva ou remove o bloqueio temporário por excesso de tentativas."""

        user.locked_until = locked_until
        await self._db.flush()

    async def increment_failed_attempts(self, user: User) -> int:
        """Soma mais uma tentativa ao contador de logins incorretos."""

        user.failed_login_attempts += 1
        await self._db.flush()
        return user.failed_login_attempts

    async def reset_failed_attempts(self, user: User) -> None:
        """Zera as tentativas de login incorretos após um acesso bem-sucedido."""

        user.failed_login_attempts = 0
        await self._db.flush()

    # Sincroniza os dados para carregar os papéis (roles) com segurança,
    # evitando erros de carregamento assíncrono ao acessar o relacionamento.

    async def assign_role(self, user: User, role: Role) -> bool:
        """
        Vincula um papel (role) ao usuário, caso ainda não possua.
        Retorna se a atribuição foi nova ou se o usuário já tinha o papel.
        """

        await self._db.refresh(user, attribute_names=["roles"])
        if role not in user.roles:
            user.roles.append(role)
            await self._db.flush()
            return True
        return False

    async def remove_role(self, user: User, role: Role) -> bool:
        """
        Remove um papel (role) do usuário, caso esteja associado.
        Retorna se a remoção foi feita ou se ele já não tinha o papel.
        """

        await self._db.refresh(user, attribute_names=["roles"])
        if role in user.roles:
            user.roles.remove(role)
            await self._db.flush()
            return True
        return False
