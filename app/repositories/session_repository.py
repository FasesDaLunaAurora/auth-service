"""
Repositório de `Session` (sessão lógica de dispositivo/cliente).

Ver nota de decisão em `refresh_token_repository.py` sobre este arquivo
ter sido antecipado da Etapa 6 para a Etapa 4, por dependência estrutural.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session_model import Session


class SessionRepository:
    """Acesso a dados da entidade `Session`, isolado de regras de negócio."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, session: Session) -> Session:
        self._db.add(session)
        await self._db.flush()
        return session

    async def get_by_id(self, session_id: uuid.UUID) -> Session | None:
        stmt = select(Session).where(Session.id == session_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_for_user(self, user_id: uuid.UUID) -> list[Session]:
        """Lista sessões não revogadas de um usuário, usado por `GET /sessions`."""
        stmt = (
            select(Session)
            .where(Session.user_id == user_id, Session.revoked.is_(False))
            .order_by(Session.last_active_at.desc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def revoke(self, session: Session) -> None:
        """Revoga uma sessão específica (`DELETE /sessions/{id}`, ou logout de um dispositivo)."""
        session.revoked = True
        await self._db.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Revoga todas as sessões de um usuário (`POST /auth/logout-all`)."""
        stmt = (
            update(Session)
            .where(Session.user_id == user_id, Session.revoked.is_(False))
            .values(revoked=True)
        )
        await self._db.execute(stmt)
        await self._db.flush()

    async def touch_last_active(self, session: Session, *, timestamp: datetime) -> None:
        """
        Atualiza `last_active_at`.

        Chamado pela camada de serviço de forma esporádica (não a cada
        requisição autenticada) — a política de throttling dessa
        atualização é decidida em `session_service.py` (Etapa 6), não
        aqui.
        """
        session.last_active_at = timestamp
        await self._db.flush()
