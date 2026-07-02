"""
Repositório de `RefreshToken`.

Nota de decisão: o cronograma da Etapa 4 lista explicitamente apenas
`user_repository.py`, `role_repository.py` e `permission_repository.py`
— mas a árvore de pastas da Seção 4 exige também
`refresh_token_repository.py` e `session_repository.py`, e o fluxo de
rotação de tokens (Seção 7) e o `session_service` (Etapa 6) dependem
diretamente deles. Gerei os dois agora para não bloquear as etapas
seguintes; se preferir, posso tratá-los como pertencentes formalmente à
Etapa 6 em vez da 4 — o conteúdo é o mesmo.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token_model import RefreshToken


class RefreshTokenRepository:
    """Acesso a dados da entidade `RefreshToken`, isolado de regras de negócio."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, refresh_token: RefreshToken) -> RefreshToken:
        self._db.add(refresh_token)
        await self._db.flush()
        return refresh_token

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """
        Busca um refresh token pelo hash armazenado.

        Quem calcula o hash a partir do token em texto puro recebido na
        requisição é `app/security/jwt_handler.py` (Etapa 5) — este
        repositório nunca vê o valor original do token.
        """
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, refresh_token: RefreshToken) -> None:
        """Revoga um único refresh token (usado na rotação normal, Seção 7)."""
        refresh_token.revoked = True
        await self._db.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """
        Revoga, em massa, todos os refresh tokens de um usuário.

        Usado tanto por `POST /auth/logout-all` quanto pela proteção
        contra *token replay* (Seção 7): reuso de um refresh token já
        revogado deve disparar a revogação de todas as sessões do
        usuário. A decisão de *quando* chamar este método é do
        `auth_service`; aqui só a mecânica de persistência.
        """
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        await self._db.execute(stmt)
        await self._db.flush()

    async def delete_expired(self, *, older_than: datetime) -> None:
        """
        Remove fisicamente refresh tokens expirados há mais de `older_than`.

        Operação de manutenção/limpeza (chamada por um script agendado,
        `scripts/`, fora do ciclo de requisição HTTP) — não afeta a
        lógica de autenticação em tempo real.
        """
        stmt = delete(RefreshToken).where(RefreshToken.expires_at < older_than)
        await self._db.execute(stmt)
        await self._db.flush()
