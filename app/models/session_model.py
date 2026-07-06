"""
Modelo de Sessão de Usuário.

Representa o login ativo de um usuário em um dispositivo específico
(não confundir com a sessão do banco de dados). É a tabela usada para
listar e derrubar acessos ativos.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin, utcnow

if TYPE_CHECKING:
    from app.models.user_model import User


class Session(UUIDPrimaryKeyMixin, Base):
    """
    Sessão ativa de um usuário em um dispositivo.

    O campo `last_active_at` é atualizado ao validar o token para registrar
    o histórico de uso, evitando overhead de gravação no banco a cada requisição.
    """

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_info: Mapped[str | None] = mapped_column(String(500), default=None, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)  # suporta IPv6
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="sessions")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Session id={self.id} user_id={self.user_id} revoked={self.revoked}>"
