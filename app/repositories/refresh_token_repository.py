"""
Repositório de Refresh Tokens.
Gerencia a persistência e as consultas das chaves de sessão e tokens de rotação.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token_model import RefreshToken


class RefreshTokenRepository:
    """Acesso a dados de refresh tokens, isolado das regras de negócio."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, refresh_token: RefreshToken) -> RefreshToken:
        self._db.add(refresh_token)
        await self._db.flush()
        return refresh_token

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """
        Busca um refresh token pelo hash cadastrado.

        A busca é feita usando apenas o hash. O valor original do token
        nunca chega a passar por este repositório.
        """

        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, refresh_token: RefreshToken) -> None:
        """Revoga um único refresh token durante o fluxo de rotação."""

        refresh_token.revoked = True
        await self._db.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """
        Revoga em massa todos os refresh tokens de um usuário.
        Utilizado no logout global ou na proteção contra ataques de reuso (Replay Attack).
        Este método executa apenas a atualização no banco de dados.
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
        Remove fisicamente do banco os refresh tokens expirados.
        Operação de limpeza para manutenção da base de dados, rodando em background
        ou scripts agendados fora das requisições HTTP da API.
        """

        stmt = delete(RefreshToken).where(RefreshToken.expires_at < older_than)
        await self._db.execute(stmt)
        await self._db.flush()
